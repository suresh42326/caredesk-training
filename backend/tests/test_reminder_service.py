from datetime import datetime, timedelta

from app.models import Appointment, PatientContact, Reminder
from app.reminders.provider import FakeSmsProvider, SendResult
from app.reminders.service import RunSummary, send_due_reminders

NOW = datetime(2030, 1, 15, 9, 0)
PHONE = "+91-90000-00001"


def make_appointment(db, patient_id=1, starts_at=None, reason="Cardiology follow-up"):
    appt = Appointment(
        patient_id=patient_id, starts_at=starts_at or NOW + timedelta(hours=23), duration_min=30, reason=reason
    )
    db.add(appt)
    db.commit()
    return appt


def make_contact(db, patient_id=1, phone=PHONE, opted_out=False):
    db.add(PatientContact(patient_id=patient_id, phone=phone, opted_out=opted_out))
    db.commit()


def run(db, provider, sleeps=None):
    sleeps = sleeps if sleeps is not None else []
    return send_due_reminders(db, provider, NOW, sleep=sleeps.append)


def test_SPEC001_AC1_sends_one_reminder_for_an_appointment_within_24_hours(db):
    make_appointment(db)
    make_contact(db)
    provider = FakeSmsProvider()

    summary = run(db, provider)

    assert summary == RunSummary(sent=1)
    assert [to for to, _ in provider.sent] == [PHONE]
    reminder = db.query(Reminder).one()
    assert (reminder.status, reminder.attempts, reminder.sent_at) == ("sent", 1, NOW)


def test_SPEC001_AC1_ignores_appointments_outside_the_24_hour_window(db):
    make_appointment(db, patient_id=1, starts_at=NOW + timedelta(hours=25))
    make_appointment(db, patient_id=1, starts_at=NOW - timedelta(hours=1))
    make_contact(db)
    provider = FakeSmsProvider()

    assert run(db, provider) == RunSummary()
    assert provider.calls == 0
    assert db.query(Reminder).count() == 0


def test_SPEC001_AC1_includes_an_appointment_starting_exactly_24_hours_from_now(db):
    make_appointment(db, starts_at=NOW + timedelta(hours=24))
    make_contact(db)
    provider = FakeSmsProvider()

    assert run(db, provider) == RunSummary(sent=1)
    assert len(provider.sent) == 1
    assert db.query(Reminder).count() == 1


def test_SPEC001_AC1_excludes_an_appointment_starting_exactly_now(db):
    make_appointment(db, starts_at=NOW)
    make_contact(db)
    provider = FakeSmsProvider()

    assert run(db, provider) == RunSummary()
    assert provider.calls == 0
    assert db.query(Reminder).count() == 0


def test_SPEC001_AC2_does_not_text_an_opted_out_patient(db):
    make_appointment(db)
    make_contact(db, opted_out=True)
    provider = FakeSmsProvider()

    assert run(db, provider) == RunSummary(skipped_opted_out=1)
    assert provider.calls == 0
    assert db.query(Reminder).count() == 0


def test_SPEC001_AC2_does_not_text_a_patient_without_a_phone_number(db):
    make_appointment(db, patient_id=2)
    provider = FakeSmsProvider()

    assert run(db, provider) == RunSummary(skipped_opted_out=1)
    assert provider.calls == 0


def test_SPEC001_AC3_a_second_run_does_not_send_a_duplicate(db):
    make_appointment(db)
    make_contact(db)
    provider = FakeSmsProvider()

    first = run(db, provider)
    second = run(db, provider)

    assert first.sent == 1
    assert second == RunSummary(skipped_duplicate=1)
    assert len(provider.sent) == 1
    assert db.query(Reminder).count() == 1


def test_SPEC001_AC4_retries_transient_errors_with_exponential_backoff_then_succeeds(db):
    make_appointment(db)
    make_contact(db)
    transient = SendResult(ok=False, transient=True, error="503")
    provider = FakeSmsProvider(queue=[transient, transient, SendResult(ok=True)])
    sleeps: list[float] = []

    summary = run(db, provider, sleeps)

    assert summary.sent == 1
    assert provider.calls == 3
    assert sleeps == [1.0, 2.0]
    assert db.query(Reminder).one().attempts == 3


def test_SPEC001_AC4_records_failed_after_three_transient_errors(db):
    make_appointment(db)
    make_contact(db)
    transient = SendResult(ok=False, transient=True, error="503 Service Unavailable")
    provider = FakeSmsProvider(queue=[transient, transient, transient])
    sleeps: list[float] = []

    summary = run(db, provider, sleeps)

    assert summary == RunSummary(failed=1)
    assert provider.calls == 3
    assert sleeps == [1.0, 2.0]  # no pointless wait after the last attempt
    reminder = db.query(Reminder).one()
    assert (reminder.status, reminder.attempts, reminder.sent_at) == ("failed", 3, None)
    assert reminder.error == "503 Service Unavailable"


def test_SPEC001_AC5_records_failed_without_retrying_a_permanent_error(db):
    make_appointment(db)
    make_contact(db)
    provider = FakeSmsProvider(queue=[SendResult(ok=False, transient=False, error="invalid number")])
    sleeps: list[float] = []

    summary = run(db, provider, sleeps)

    assert summary == RunSummary(failed=1)
    assert provider.calls == 1
    assert sleeps == []
    reminder = db.query(Reminder).one()
    assert (reminder.status, reminder.attempts) == ("failed", 1)


def test_SPEC001_AC6_message_has_date_and_time_but_no_health_information(db):
    make_appointment(db, reason="Cardiology follow-up")
    make_contact(db)
    provider = FakeSmsProvider()

    run(db, provider)

    (_, body), = provider.sent
    assert "16 Jan 2030" in body and "08:00" in body
    assert "Cardiology" not in body and "follow-up" not in body


def test_SPEC001_AC6_failure_records_never_contain_the_phone_number(db):
    make_appointment(db)
    make_contact(db)
    provider = FakeSmsProvider(queue=[SendResult(ok=False, transient=False, error="rejected")])

    run(db, provider)

    assert PHONE not in (db.query(Reminder).one().error or "")


def test_SPEC001_AC4_backoff_doubles_with_every_retry(db, monkeypatch):
    # With 3 attempts, doubling (1s, 2s) and linear growth (1s, 2s) look identical; 4 attempts tell them apart.
    monkeypatch.setattr("app.reminders.service.MAX_ATTEMPTS", 4)
    make_appointment(db)
    make_contact(db)
    transient = SendResult(ok=False, transient=True, error="503")
    provider = FakeSmsProvider(queue=[transient, transient, transient, SendResult(ok=True)])
    sleeps: list[float] = []

    run(db, provider, sleeps)

    assert sleeps == [1.0, 2.0, 4.0]
