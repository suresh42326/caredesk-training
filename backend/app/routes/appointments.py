from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.errors import AppError
from app.models import Appointment
from app.schemas import AppointmentCreate, AppointmentOut, RescheduleRequest

router = APIRouter(prefix="/appointments", tags=["appointments"])


@router.post("", response_model=AppointmentOut, status_code=201)
def create_appointment(body: AppointmentCreate, db: Session = Depends(get_db)):
    appt = Appointment(**body.model_dump())
    db.add(appt)
    db.commit()
    db.refresh(appt)
    return appt


@router.get("/{appointment_id}", response_model=AppointmentOut)
def get_appointment(appointment_id: int, db: Session = Depends(get_db)):
    appt = db.get(Appointment, appointment_id)
    if appt is None:
        raise AppError(404, "Not Found", f"Appointment {appointment_id} does not exist")
    return appt


@router.patch("/{appointment_id}/reschedule", response_model=AppointmentOut)
def reschedule_appointment(
    appointment_id: int, body: RescheduleRequest, db: Session = Depends(get_db)
):
    appt = db.get(Appointment, appointment_id)
    if appt is None:
        raise AppError(404, "Not Found", f"Appointment {appointment_id} does not exist")
    if body.starts_at <= datetime.now():
        raise AppError(422, "Invalid Time", "Appointments cannot be moved into the past")

    new_end = body.starts_at + timedelta(minutes=appt.duration_min)
    others = (
        db.query(Appointment)
        .filter(Appointment.patient_id == appt.patient_id, Appointment.id != appt.id)
        .all()
    )
    for other in others:
        other_end = other.starts_at + timedelta(minutes=other.duration_min)
        if body.starts_at < other_end and other.starts_at < new_end:
            raise AppError(
                409,
                "Conflict",
                f"Patient already has appointment {other.id} at {other.starts_at.isoformat()}",
            )

    appt.starts_at = body.starts_at
    db.commit()
    db.refresh(appt)
    return appt


@router.get("", response_model=list[AppointmentOut])
def list_appointments(patient_id: int | None = None, db: Session = Depends(get_db)):
    query = db.query(Appointment)
    if patient_id is not None:
        query = query.filter(Appointment.patient_id == patient_id)
    return query.order_by(Appointment.starts_at).all()
