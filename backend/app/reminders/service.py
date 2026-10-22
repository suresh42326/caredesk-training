"""Decide which appointments need a reminder, send it with retries, and record the outcome."""
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Appointment, PatientContact, Reminder
from app.reminders.provider import SmsProvider

WINDOW = timedelta(hours=24)
MAX_ATTEMPTS = 3
BASE_DELAY_SECONDS = 1.0


@dataclass
class RunSummary:
    sent: int = 0
    failed: int = 0
    skipped_opted_out: int = 0
    skipped_duplicate: int = 0


def build_message(appointment: Appointment) -> str:
    """Date and time only. The visit reason is health information and must never be sent by SMS."""
    when = appointment.starts_at
    return f"Reminder: your appointment is on {when:%d %b %Y} at {when:%H:%M}. Reply STOP to opt out."


def send_due_reminders(
    db: Session,
    provider: SmsProvider,
    now: datetime,
    sleep: Callable[[float], None] = time.sleep,
) -> RunSummary:
    summary = RunSummary()
    due = (
        db.query(Appointment)
        .filter(Appointment.starts_at > now, Appointment.starts_at <= now + WINDOW)
        .filter(Appointment.cancelled_at.is_(None))
        .order_by(Appointment.starts_at)
        .all()
    )
    for appointment in due:
        if db.query(Reminder).filter_by(appointment_id=appointment.id).first():
            summary.skipped_duplicate += 1
            continue
        contact = db.get(PatientContact, appointment.patient_id)
        if contact is None or contact.opted_out or not contact.phone:
            summary.skipped_opted_out += 1
            continue

        attempts = 0
        result = None
        while attempts < MAX_ATTEMPTS:
            attempts += 1
            result = provider.send(contact.phone, build_message(appointment))
            if result.ok or not result.transient:
                break
            if attempts < MAX_ATTEMPTS:
                sleep(BASE_DELAY_SECONDS * 2 ** (attempts - 1))

        assert result is not None
        reminder = Reminder(
            appointment_id=appointment.id,
            status="sent" if result.ok else "failed",
            attempts=attempts,
            sent_at=now if result.ok else None,
            error=None if result.ok else (result.error or "send failed")[:200],
        )
        db.add(reminder)
        try:
            db.commit()
        except IntegrityError:  # another run recorded it first
            db.rollback()
            summary.skipped_duplicate += 1
            continue
        if result.ok:
            summary.sent += 1
        else:
            summary.failed += 1
    return summary
