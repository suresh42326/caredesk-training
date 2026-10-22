from datetime import datetime, timedelta

import pytest

from app.main import app
from app.models import Appointment, PatientContact, Reminder
from app.reminders.provider import FakeSmsProvider, SendResult

PHONE = "+15550100123"
OTHER_PHONE = "+15550100456"
REASON = "chronic migraine follow-up"


@pytest.fixture()
def provider():
    return FakeSmsProvider(sent=[], queue=[], calls=0)


@pytest.fixture()
def use_provider(provider):
    """Override the provider dependency with the fake. The run endpoint is the only injection
    point, so the dependency is imported lazily: tests that never run the job do not need it.

    ASSUMPTION (design.md does not name it): the dependency is `get_sms_provider` in
    `app.routes.reminders`.
    """
    from app.routes.reminders import get_sms_provider

    app.dependency_overrides[get_sms_provider] = lambda: provider
    yield provider
    app.dependency_overrides.pop(get_sms_provider, None)


def add_appointment(db, patient_id=1, hours_ahead=2, reason=REASON):
    # POST /reminders/run uses the real clock, so "due" appointments are relative to now.
    starts_at = datetime.now() + timedelta(hours=hours_ahead)
    appt = Appointment(patient_id=patient_id, starts_at=starts_at, duration_min=30, reason=reason)
    db.add(appt)
    db.commit()
    return appt


def add_contact(db, patient_id=1, phone=PHONE, opted_out=False):
    db.add(PatientContact(patient_id=patient_id, phone=phone, opted_out=opted_out))
    db.commit()


def add_reminder(db, appointment_id, status, attempts, error=None):
    db.add(Reminder(appointment_id=appointment_id, status=status, attempts=attempts, error=error))
    db.commit()


def reminders_in_db(db):
    db.expire_all()
    return db.query(Reminder).all()


# ---- POST /reminders/run ----


def test_SPEC001_AC7_run_returns_summary_counts_and_sends_once(client, db, use_provider):
    appt = add_appointment(db)
    add_contact(db)

    resp = client.post("/reminders/run")

    assert resp.status_code == 200
    assert resp.json() == {
        "sent": 1,
        "failed": 0,
        "skipped_opted_out": 0,
        "skipped_duplicate": 0,
    }
    assert [to for to, _ in use_provider.sent] == [PHONE]
    rows = reminders_in_db(db)
    assert [(r.appointment_id, r.status, r.attempts) for r in rows] == [(appt.id, "sent", 1)]


def test_SPEC001_AC7_run_twice_reports_duplicate_and_sends_once(client, db, use_provider):
    add_appointment(db)
    add_contact(db)

    first = client.post("/reminders/run")
    second = client.post("/reminders/run")

    assert first.status_code == 200
    assert first.json()["sent"] == 1
    assert second.status_code == 200
    assert second.json() == {
        "sent": 0,
        "failed": 0,
        "skipped_opted_out": 0,
        "skipped_duplicate": 1,
    }
    assert use_provider.calls == 1
    assert len(reminders_in_db(db)) == 1


def test_SPEC001_AC7_run_counts_opted_out_patient_as_skipped(client, db, use_provider):
    add_appointment(db)
    add_contact(db, opted_out=True)

    resp = client.post("/reminders/run")

    assert resp.status_code == 200
    assert resp.json() == {
        "sent": 0,
        "failed": 0,
        "skipped_opted_out": 1,
        "skipped_duplicate": 0,
    }
    assert use_provider.calls == 0
    assert reminders_in_db(db) == []


def test_SPEC001_AC7_run_counts_permanent_failure(client, db, use_provider):
    appt = add_appointment(db)
    add_contact(db)
    use_provider.queue = [SendResult(ok=False, transient=False, error="invalid number")]

    resp = client.post("/reminders/run")

    assert resp.status_code == 200
    assert resp.json() == {
        "sent": 0,
        "failed": 1,
        "skipped_opted_out": 0,
        "skipped_duplicate": 0,
    }
    assert use_provider.calls == 1
    rows = reminders_in_db(db)
    assert [(r.appointment_id, r.status, r.attempts) for r in rows] == [(appt.id, "failed", 1)]


# ---- GET /appointments/{id}/reminders ----


def test_SPEC001_AC7_list_returns_status_and_attempts_of_a_sent_reminder(client, db):
    appt = add_appointment(db)
    add_reminder(db, appt.id, "sent", 1)

    resp = client.get(f"/appointments/{appt.id}/reminders")

    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["status"] == "sent"
    assert body[0]["attempts"] == 1


def test_SPEC001_AC7_list_returns_status_and_attempts_of_a_failed_reminder(client, db):
    appt = add_appointment(db)
    add_reminder(db, appt.id, "failed", 3, error="timeout")

    resp = client.get(f"/appointments/{appt.id}/reminders")

    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["status"] == "failed"
    assert body[0]["attempts"] == 3


def test_SPEC001_AC7_list_is_empty_when_appointment_has_no_reminder(client, db):
    appt = add_appointment(db)

    resp = client.get(f"/appointments/{appt.id}/reminders")

    assert resp.status_code == 200
    assert resp.json() == []


def test_SPEC001_AC7_list_only_returns_reminders_of_the_requested_appointment(client, db):
    first = add_appointment(db, patient_id=1)
    second = add_appointment(db, patient_id=2)
    add_reminder(db, first.id, "sent", 1)
    add_reminder(db, second.id, "failed", 1, error="invalid number")

    resp = client.get(f"/appointments/{second.id}/reminders")

    assert resp.status_code == 200
    assert [(r["status"], r["attempts"]) for r in resp.json()] == [("failed", 1)]


def test_SPEC001_AC7_list_missing_appointment_returns_404_problem_document(client, db):
    resp = client.get("/appointments/999/reminders")

    assert resp.status_code == 404
    assert resp.headers["content-type"].startswith("application/problem+json")
    body = resp.json()
    assert body["title"] == "Not Found"
    assert body["status"] == 404
    assert "999" in body["detail"]
    assert reminders_in_db(db) == []


def test_SPEC001_AC7_run_then_list_shows_sent_reminder(client, db, use_provider):
    appt = add_appointment(db)
    add_contact(db)

    run = client.post("/reminders/run")
    listed = client.get(f"/appointments/{appt.id}/reminders")

    assert run.status_code == 200
    assert listed.status_code == 200
    body = listed.json()
    assert [(r["status"], r["attempts"]) for r in body] == [("sent", 1)]


def test_SPEC001_AC7_run_then_list_shows_failed_reminder_without_phone(client, db, use_provider):
    appt = add_appointment(db)
    add_contact(db)
    use_provider.queue = [SendResult(ok=False, transient=False, error=f"rejected {PHONE}")]

    run = client.post("/reminders/run")
    listed = client.get(f"/appointments/{appt.id}/reminders")

    assert run.status_code == 200
    assert run.json()["failed"] == 1
    assert listed.status_code == 200
    body = listed.json()
    assert [(r["status"], r["attempts"]) for r in body] == [("failed", 1)]
    assert PHONE not in listed.text
    assert PHONE not in run.text


def test_SPEC001_AC7_run_then_list_shows_three_attempts_after_transient_failures(
    client, db, use_provider
):
    # NOTE: the run endpoint has no sleep injection point (the provider dependency is the only
    # one), so this test waits the real backoff (about 3 seconds) between the three attempts.
    appt = add_appointment(db)
    add_contact(db)
    use_provider.queue = [SendResult(ok=False, transient=True, error="timeout") for _ in range(5)]

    run = client.post("/reminders/run")
    listed = client.get(f"/appointments/{appt.id}/reminders")

    assert run.status_code == 200
    assert run.json()["failed"] == 1
    assert use_provider.calls == 3
    assert listed.status_code == 200
    body = listed.json()
    assert [(r["status"], r["attempts"]) for r in body] == [("failed", 3)]
    assert PHONE not in listed.text


# ---- PUT /patients/{id}/contact ----


def test_SPEC001_AC7_put_contact_creates_record_and_returns_it(client, db):
    resp = client.put("/patients/1/contact", json={"phone": PHONE, "opted_out": False})

    assert resp.status_code == 200
    body = resp.json()
    assert body["phone"] == PHONE
    assert body["opted_out"] is False
    db.expire_all()
    contact = db.get(PatientContact, 1)
    assert contact is not None
    assert (contact.phone, contact.opted_out) == (PHONE, False)


def test_SPEC001_AC7_put_contact_updates_existing_record_without_duplicating(client, db):
    add_contact(db, patient_id=1, phone=PHONE, opted_out=False)

    resp = client.put("/patients/1/contact", json={"phone": OTHER_PHONE, "opted_out": True})

    assert resp.status_code == 200
    body = resp.json()
    assert body["phone"] == OTHER_PHONE
    assert body["opted_out"] is True
    db.expire_all()
    contacts = db.query(PatientContact).all()
    assert len(contacts) == 1
    assert (contacts[0].patient_id, contacts[0].phone, contacts[0].opted_out) == (
        1,
        OTHER_PHONE,
        True,
    )


def test_SPEC001_AC7_put_contact_does_not_change_other_patients(client, db):
    add_contact(db, patient_id=2, phone=OTHER_PHONE, opted_out=False)

    resp = client.put("/patients/1/contact", json={"phone": PHONE, "opted_out": True})

    assert resp.status_code == 200
    db.expire_all()
    other = db.get(PatientContact, 2)
    assert other is not None
    assert (other.phone, other.opted_out) == (OTHER_PHONE, False)


def test_SPEC001_AC7_opted_out_via_put_contact_stops_the_run(client, db, use_provider):
    add_appointment(db)
    put = client.put("/patients/1/contact", json={"phone": PHONE, "opted_out": True})

    run = client.post("/reminders/run")

    assert put.status_code == 200
    assert run.status_code == 200
    assert run.json()["skipped_opted_out"] == 1
    assert run.json()["sent"] == 0
    assert use_provider.calls == 0
    assert reminders_in_db(db) == []
