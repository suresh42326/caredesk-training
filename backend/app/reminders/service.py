"""Send SMS reminders for appointments starting within the next 24 hours."""

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models import Appointment, PatientContact, Reminder
from app.reminders.provider import SmsProvider

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 3
BACKOFF_BASE_SECONDS = 1.0
WINDOW = timedelta(hours=24)
MAX_ERROR_LENGTH = 500


@dataclass
class RunSummary:
    sent: int = 0
    failed: int = 0
    skipped_opted_out: int = 0
    skipped_duplicate: int = 0


def build_message(starts_at: datetime) -> str:
    """Date and time only; the visit reason must never appear here."""
    return (
        f"Reminder: you have an appointment on {starts_at:%Y-%m-%d} at {starts_at:%H:%M}. "
        "Reply STOP to opt out."
    )


def _clean_error(error: str | None, phone: str) -> str:
    text = (error or "send failed").replace(phone, "[redacted]")
    return text[:MAX_ERROR_LENGTH]


def send_due_reminders(
    db: Session,
    provider: SmsProvider,
    now: datetime,
    sleep: Callable[[float], None] = time.sleep,
) -> RunSummary:
    summary = RunSummary()
    appointments = (
        db.query(Appointment)
        .filter(Appointment.starts_at > now, Appointment.starts_at <= now + WINDOW)
        .order_by(Appointment.starts_at, Appointment.id)
        .all()
    )
    for appt in appointments:
        existing = db.query(Reminder).filter(Reminder.appointment_id == appt.id).first()
        if existing is not None:
            summary.skipped_duplicate += 1
            continue

        contact = db.get(PatientContact, appt.patient_id)
        if contact is None or contact.opted_out or not contact.phone:
            summary.skipped_opted_out += 1 if contact is not None and contact.opted_out else 0
            continue

        body = build_message(appt.starts_at)
        attempts = 0
        error: str | None = None
        ok = False
        while attempts < MAX_ATTEMPTS:
            attempts += 1
            result = provider.send(contact.phone, body)
            if result.ok:
                ok = True
                break
            error = result.error
            if not result.transient:
                break
            if attempts < MAX_ATTEMPTS:
                sleep(BACKOFF_BASE_SECONDS * 2 ** (attempts - 1))

        if ok:
            db.add(Reminder(appointment_id=appt.id, status="sent", attempts=attempts, sent_at=now))
            summary.sent += 1
        else:
            db.add(
                Reminder(
                    appointment_id=appt.id,
                    status="failed",
                    attempts=attempts,
                    error=_clean_error(error, contact.phone),
                )
            )
            summary.failed += 1
        db.commit()
        logger.info("reminder for appointment %s: %s", appt.id, "sent" if ok else "failed")
    return summary
