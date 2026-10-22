from datetime import datetime

from app.models import Appointment


def test_SPEC002_AC1_appointment_stores_cancellation_details(db):
    appt = Appointment(patient_id=1, starts_at=datetime(2030, 1, 20, 9, 0), duration_min=30, reason="Check-up")
    db.add(appt)
    db.commit()
    assert (appt.cancelled_at, appt.cancel_reason, appt.cancelled_late) == (None, None, False)

    appt.cancelled_at = datetime(2030, 1, 15, 9, 0)
    appt.cancel_reason = "Patient is travelling"
    db.commit()
    db.refresh(appt)
    assert appt.cancel_reason == "Patient is travelling"
