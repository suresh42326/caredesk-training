from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AppointmentCreate(BaseModel):
    patient_id: int
    starts_at: datetime
    duration_min: int = 30
    reason: str = Field(min_length=3, max_length=200)


class RescheduleRequest(BaseModel):
    starts_at: datetime


class AppointmentOut(AppointmentCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int


class RunSummaryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    sent: int
    failed: int
    skipped_opted_out: int
    skipped_duplicate: int


class ReminderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    appointment_id: int
    status: str
    attempts: int
    sent_at: datetime | None = None
    error: str | None = None


class PatientContactUpdate(BaseModel):
    phone: str = Field(min_length=1, max_length=32)
    opted_out: bool = False


class PatientContactOut(PatientContactUpdate):
    model_config = ConfigDict(from_attributes=True)

    patient_id: int
