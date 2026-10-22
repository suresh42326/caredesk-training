from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, UniqueConstraint, false
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Appointment(Base):
    __tablename__ = "appointments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    patient_id: Mapped[int] = mapped_column(Integer, index=True)
    starts_at: Mapped[datetime] = mapped_column(DateTime)
    duration_min: Mapped[int] = mapped_column(Integer, default=30)
    reason: Mapped[str] = mapped_column(String(200))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    cancel_reason: Mapped[str | None] = mapped_column(String(200), nullable=True)
    cancelled_late: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())


class PatientContact(Base):
    """How to reach a patient by SMS, and whether they have opted out."""

    __tablename__ = "patient_contacts"

    patient_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    phone: Mapped[str] = mapped_column(String(32))
    opted_out: Mapped[bool] = mapped_column(Boolean, default=False)


class Reminder(Base):
    """One row per appointment that has been reminded (or failed). The unique constraint stops duplicates."""

    __tablename__ = "reminders"
    __table_args__ = (UniqueConstraint("appointment_id", name="uq_reminders_appointment_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    appointment_id: Mapped[int] = mapped_column(Integer, index=True)
    status: Mapped[str] = mapped_column(String(16))  # "sent" or "failed"
    attempts: Mapped[int] = mapped_column(Integer, default=1)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    error: Mapped[str | None] = mapped_column(String(200), nullable=True)
