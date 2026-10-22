import logging
from datetime import datetime

import pytest
from app.reminders.service import send_due_reminders

from app.models import Appointment, PatientContact, Reminder
from app.reminders.provider import FakeSmsProvider, SendResult

NOW = datetime(2030, 1, 1, 9, 0)
SOON = datetime(2030, 1, 2, 8, 30)  # 23.5 hours after NOW
LATER = datetime(2030, 1, 2, 9, 30)  # 24.5 hours after NOW
PHONE = "+15550100123"
REASON = "chronic migraine follow-up"


@pytest.fixture()
def provider():
    return FakeSmsProvider(sent=[], queue=[], calls=0)


@pytest.fixture()
def sleeps():
    return []


@pytest.fixture()
def fake_sleep(sleeps):
    return sleeps.append


def add_appointment(db, patient_id=1, starts_at=SOON, reason=REASON):
    appt = Appointment(patient_id=patient_id, starts_at=starts_at, duration_min=30, reason=reason)
    db.add(appt)
    db.commit()
    return appt


def add_contact(db, patient_id=1, phone=PHONE, opted_out=False):
    db.add(PatientContact(patient_id=patient_id, phone=phone, opted_out=opted_out))
    db.commit()


def reminders_of(db, appointment_id):
    db.expire_all()
    return db.query(Reminder).filter(Reminder.appointment_id == appointment_id).all()


def run(db, provider, fake_sleep):
    return send_due_reminders(db, provider, NOW, sleep=fake_sleep)


def test_SPEC001_AC1_appointment_within_24h_gets_one_sms_and_sent_reminder(
    db, provider, fake_sleep
):
    appt = add_appointment(db)
    add_contact(db)

    summary = run(db, provider, fake_sleep)

    assert (summary.sent, summary.failed) == (1, 0)
    assert (summary.skipped_opted_out, summary.skipped_duplicate) == (0, 0)
    assert len(provider.sent) == 1
    assert provider.sent[0][0] == PHONE
    rows = reminders_of(db, appt.id)
    assert len(rows) == 1
    assert rows[0].status == "sent"
    assert rows[0].attempts == 1
    assert rows[0].sent_at is not None


def test_SPEC001_AC1_appointment_beyond_24h_is_not_reminded(db, provider, fake_sleep):
    appt = add_appointment(db, starts_at=LATER)
    add_contact(db)

    summary = run(db, provider, fake_sleep)

    assert (summary.sent, summary.failed) == (0, 0)
    assert provider.calls == 0
    assert reminders_of(db, appt.id) == []


def test_SPEC001_AC2_opted_out_patient_gets_no_sms(db, provider, fake_sleep):
    appt = add_appointment(db)
    add_contact(db, opted_out=True)

    summary = run(db, provider, fake_sleep)

    assert summary.skipped_opted_out == 1
    assert (summary.sent, summary.failed, summary.skipped_duplicate) == (0, 0, 0)
    assert provider.calls == 0
    assert provider.sent == []
    assert reminders_of(db, appt.id) == []


def test_SPEC001_AC2_patient_without_contact_record_gets_no_sms(db, provider, fake_sleep):
    appt = add_appointment(db)

    summary = run(db, provider, fake_sleep)

    assert (summary.sent, summary.failed) == (0, 0)
    assert provider.calls == 0
    assert reminders_of(db, appt.id) == []


def test_SPEC001_AC2_patient_with_empty_phone_gets_no_sms(db, provider, fake_sleep):
    appt = add_appointment(db)
    add_contact(db, phone="")

    summary = run(db, provider, fake_sleep)

    assert (summary.sent, summary.failed) == (0, 0)
    assert provider.calls == 0
    assert reminders_of(db, appt.id) == []


def test_SPEC001_AC2_opted_out_patient_does_not_block_other_patients(db, provider, fake_sleep):
    add_appointment(db, patient_id=1)
    add_contact(db, patient_id=1, opted_out=True)
    other = add_appointment(db, patient_id=2)
    add_contact(db, patient_id=2, phone="+15550100456")

    summary = run(db, provider, fake_sleep)

    assert (summary.sent, summary.skipped_opted_out) == (1, 1)
    assert [to for to, _ in provider.sent] == ["+15550100456"]
    assert [r.status for r in reminders_of(db, other.id)] == ["sent"]


@pytest.mark.parametrize("status", ["sent", "failed"])
def test_SPEC001_AC3_existing_reminder_blocks_a_second_send(db, provider, fake_sleep, status):
    appt = add_appointment(db)
    add_contact(db)
    db.add(Reminder(appointment_id=appt.id, status=status, attempts=1))
    db.commit()

    summary = run(db, provider, fake_sleep)

    assert summary.skipped_duplicate == 1
    assert (summary.sent, summary.failed, summary.skipped_opted_out) == (0, 0, 0)
    assert provider.calls == 0
    rows = reminders_of(db, appt.id)
    assert len(rows) == 1
    assert rows[0].status == status
    assert rows[0].attempts == 1


def test_SPEC001_AC3_running_twice_sends_only_once(db, provider, fake_sleep):
    appt = add_appointment(db)
    add_contact(db)

    first = run(db, provider, fake_sleep)
    second = run(db, provider, fake_sleep)

    assert (first.sent, first.skipped_duplicate) == (1, 0)
    assert (second.sent, second.skipped_duplicate) == (0, 1)
    assert provider.calls == 1
    assert len(provider.sent) == 1
    assert len(reminders_of(db, appt.id)) == 1


def test_SPEC001_AC4_transient_errors_retry_three_times_then_fail(db, provider, fake_sleep, sleeps):
    appt = add_appointment(db)
    add_contact(db)
    provider.queue = [SendResult(ok=False, transient=True, error="timeout") for _ in range(5)]

    summary = run(db, provider, fake_sleep)

    assert (summary.sent, summary.failed) == (0, 1)
    assert provider.calls == 3
    assert provider.sent == []
    rows = reminders_of(db, appt.id)
    assert len(rows) == 1
    assert rows[0].status == "failed"
    assert rows[0].attempts == 3
    assert rows[0].sent_at is None
    assert rows[0].error


def test_SPEC001_AC4_backoff_delays_are_positive_and_increasing(db, provider, fake_sleep, sleeps):
    add_appointment(db)
    add_contact(db)
    provider.queue = [SendResult(ok=False, transient=True, error="timeout") for _ in range(3)]

    run(db, provider, fake_sleep)

    # Waits happen between attempts only: 3 attempts means 2 waits, none after the last.
    assert len(sleeps) == 2
    assert all(delay > 0 for delay in sleeps)
    assert sleeps[1] > sleeps[0]


def test_SPEC001_AC4_transient_error_then_success_records_sent_with_two_attempts(
    db, provider, fake_sleep, sleeps
):
    appt = add_appointment(db)
    add_contact(db)
    provider.queue = [SendResult(ok=False, transient=True, error="timeout")]

    summary = run(db, provider, fake_sleep)

    assert (summary.sent, summary.failed) == (1, 0)
    assert provider.calls == 2
    assert len(provider.sent) == 1
    assert len(sleeps) == 1
    rows = reminders_of(db, appt.id)
    assert len(rows) == 1
    assert rows[0].status == "sent"
    assert rows[0].attempts == 2


def test_SPEC001_AC5_permanent_error_fails_without_retry(db, provider, fake_sleep, sleeps):
    appt = add_appointment(db)
    add_contact(db)
    provider.queue = [SendResult(ok=False, transient=False, error="invalid number")]

    summary = run(db, provider, fake_sleep)

    assert (summary.sent, summary.failed) == (0, 1)
    assert provider.calls == 1
    assert provider.sent == []
    assert sleeps == []
    rows = reminders_of(db, appt.id)
    assert len(rows) == 1
    assert rows[0].status == "failed"
    assert rows[0].attempts == 1
    assert rows[0].error


def test_SPEC001_AC5_failed_reminder_is_not_resent_by_a_later_run(db, provider, fake_sleep):
    appt = add_appointment(db)
    add_contact(db)
    provider.queue = [SendResult(ok=False, transient=False, error="invalid number")]

    run(db, provider, fake_sleep)
    second = run(db, provider, fake_sleep)

    assert second.skipped_duplicate == 1
    assert provider.calls == 1
    assert [r.status for r in reminders_of(db, appt.id)] == ["failed"]


def test_SPEC001_AC6_message_contains_date_and_time(db, provider, fake_sleep):
    add_appointment(db)
    add_contact(db)

    run(db, provider, fake_sleep)

    body = provider.sent[0][1]
    date_forms = [
        "2030-01-02",
        "02/01/2030",
        "01/02/2030",
        "2 Jan 2030",
        "02 Jan 2030",
        "January 2, 2030",
        "2 January 2030",
        "02 January 2030",
    ]
    assert any(form in body for form in date_forms), body
    assert "08:30" in body or "8:30" in body, body


def test_SPEC001_AC6_message_does_not_contain_visit_reason(db, provider, fake_sleep):
    add_appointment(db, reason=REASON)
    add_contact(db)

    run(db, provider, fake_sleep)

    body = provider.sent[0][1].lower()
    assert REASON.lower() not in body
    assert "migraine" not in body


def test_SPEC001_AC6_message_does_not_contain_visit_reason_when_retried(db, provider, fake_sleep):
    add_appointment(db, reason=REASON)
    add_contact(db)
    provider.queue = [SendResult(ok=False, transient=True, error="timeout")]

    run(db, provider, fake_sleep)

    assert len(provider.sent) == 1
    assert "migraine" not in provider.sent[0][1].lower()


def test_SPEC001_AC1_phone_number_is_never_logged(db, provider, fake_sleep, caplog):
    add_appointment(db)
    add_contact(db)
    provider.queue = [SendResult(ok=False, transient=True, error="timeout")]

    with caplog.at_level(logging.DEBUG):
        run(db, provider, fake_sleep)

    assert PHONE not in caplog.text
