"""Cancel an appointment with a reason; mark late cancellations so the clinic's fee policy can apply."""
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.errors import AppError
from app.models import Appointment

LATE_WINDOW = timedelta(hours=24)


def cancel_appointment(db: Session, appointment_id: int, reason: str, now: datetime) -> Appointment:
    appointment = db.get(Appointment, appointment_id)
    if appointment is None:
        raise AppError(404, "Not Found", f"Appointment {appointment_id} does not exist")
    if appointment.cancelled_at is not None:
        raise AppError(409, "Already Cancelled", f"Appointment {appointment_id} was already cancelled")
    appointment.cancelled_at = now
    appointment.cancel_reason = reason
    appointment.cancelled_late = appointment.starts_at - now < LATE_WINDOW
    db.commit()
    db.refresh(appointment)
    return appointment
