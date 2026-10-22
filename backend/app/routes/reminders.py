from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.errors import AppError
from app.models import Appointment, PatientContact, Reminder
from app.reminders.provider import FakeSmsProvider, SmsProvider
from app.reminders.service import send_due_reminders
from app.schemas import PatientContactOut, PatientContactUpdate, ReminderOut, RunSummaryOut

router = APIRouter(tags=["reminders"])


def get_sms_provider() -> SmsProvider:
    # No real SMS provider in this release: the default is the in-memory fake.
    return FakeSmsProvider(sent=[], queue=[], calls=0)


@router.post("/reminders/run", response_model=RunSummaryOut)
def run_reminders(
    db: Session = Depends(get_db), provider: SmsProvider = Depends(get_sms_provider)
):
    return send_due_reminders(db, provider, datetime.now())


@router.get("/appointments/{appointment_id}/reminders", response_model=list[ReminderOut])
def list_appointment_reminders(appointment_id: int, db: Session = Depends(get_db)):
    if db.get(Appointment, appointment_id) is None:
        raise AppError(404, "Not Found", f"Appointment {appointment_id} does not exist")
    return (
        db.query(Reminder)
        .filter(Reminder.appointment_id == appointment_id)
        .order_by(Reminder.id)
        .all()
    )


@router.put("/patients/{patient_id}/contact", response_model=PatientContactOut)
def put_patient_contact(
    patient_id: int, body: PatientContactUpdate, db: Session = Depends(get_db)
):
    contact = db.get(PatientContact, patient_id)
    if contact is None:
        contact = PatientContact(patient_id=patient_id, phone=body.phone, opted_out=body.opted_out)
        db.add(contact)
    else:
        contact.phone = body.phone
        contact.opted_out = body.opted_out
    db.commit()
    db.refresh(contact)
    return contact
