from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.cancellation import cancel_appointment
from app.db import get_db
from app.routes.reminders import get_now
from app.schemas import AppointmentOut, CancelRequest

router = APIRouter(tags=["cancellation"])


@router.post("/appointments/{appointment_id}/cancel", response_model=AppointmentOut)
def cancel(
    appointment_id: int,
    body: CancelRequest,
    db: Session = Depends(get_db),
    now: datetime = Depends(get_now),
):
    return cancel_appointment(db, appointment_id, body.reason, now)
