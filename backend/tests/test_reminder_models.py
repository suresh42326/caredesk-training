from datetime import datetime

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

SENT_AT = datetime(2030, 1, 15, 9, 0)


def test_SPEC001_AC3_second_reminder_for_same_appointment_is_rejected(db):
    from app.models import Reminder

    db.add(Reminder(appointment_id=42, status="sent", attempts=1, sent_at=SENT_AT, error=None))
    db.commit()

    db.add(Reminder(appointment_id=42, status="failed", attempts=3, sent_at=None, error="boom"))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()

    rows = db.scalars(select(Reminder).where(Reminder.appointment_id == 42)).all()
    assert len(rows) == 1
    assert rows[0].status == "sent"
    assert rows[0].attempts == 1
    assert rows[0].sent_at == SENT_AT
    assert rows[0].error is None


def test_SPEC001_AC3_reminders_for_different_appointments_are_both_stored(db):
    from app.models import Reminder

    db.add(Reminder(appointment_id=1, status="sent", attempts=1, sent_at=SENT_AT, error=None))
    db.add(Reminder(appointment_id=2, status="failed", attempts=3, sent_at=None, error="boom"))
    db.commit()

    rows = db.scalars(select(Reminder).order_by(Reminder.appointment_id)).all()
    assert [(r.appointment_id, r.status) for r in rows] == [(1, "sent"), (2, "failed")]
