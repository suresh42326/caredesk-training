from datetime import datetime, timedelta

from app.models import Appointment, PatientContact
from app.reminders.provider import FakeSmsProvider
from app.reminders.service import RunSummary, send_due_reminders

NOW = datetime(2030, 1, 15, 9, 0)


def make_appointment(db, hours_ahead, cancelled=False):
    appt = Appointment(
        patient_id=1,
        starts_at=NOW + timedelta(hours=hours_ahead),
        duration_min=30,
        reason="Check-up",
        cancelled_at=NOW if cancelled else None,
        cancel_reason="Patient is travelling" if cancelled else None,
    )
    db.add(appt)
    db.commit()
    return appt


def test_SPEC002_AC5_a_cancelled_appointment_gets_no_reminder(db):
    make_appointment(db, 20, cancelled=True)
    db.add(PatientContact(patient_id=1, phone="+91-90000-00001"))
    db.commit()
    provider = FakeSmsProvider()

    summary = send_due_reminders(db, provider, NOW, sleep=lambda s: None)

    assert summary == RunSummary()
    assert provider.calls == 0


def test_SPEC002_AC5_other_appointments_are_still_reminded(db):
    make_appointment(db, 20, cancelled=True)
    make_appointment(db, 21)
    db.add(PatientContact(patient_id=1, phone="+91-90000-00001"))
    db.commit()
    provider = FakeSmsProvider()

    summary = send_due_reminders(db, provider, NOW, sleep=lambda s: None)

    assert summary == RunSummary(sent=1)
    assert provider.calls == 1
