# Design: SPEC002 Cancel an appointment with a reason

Spec: specs/cancel-appointment/spec.md (must be Approved before implementation starts; currently Draft)

## What changes (architecture delta)
- New service module `backend/app/appointments/cancellation.py` with `cancel_appointment`, which holds all the rules
  (already cancelled, late or not, trimming the reason). The route stays thin.
- New route `PATCH /appointments/{appointment_id}/cancel` in `backend/app/routes/appointments.py`.
- `ReminderService.send_due_reminders` gains one filter: appointments with `cancelled_at` set are not selected.
- `AppointmentOut` gains three read-only fields so the cancelled state is visible in every response.

## Data model and migration
Three columns are added to `appointments` by one generated Alembic revision (expand only, nothing dropped or changed):

| Column | Type | Null | Default |
|---|---|---|---|
| `cancelled_at` | DateTime | yes | none (null means not cancelled) |
| `cancel_reason` | String(200) | yes | none |
| `cancelled_late` | Boolean | no | **server default false** (`server_default=sa.false()`) |

The server default lets the migration add a NOT NULL column to existing rows without a backfill and keeps old
writers working. `cancelled_at` is the single source of truth for "is cancelled"; there is no separate status column.
The revision is generated with `alembic revision --autogenerate` and reviewed by a human; it is never edited by hand.
A migration is a High-risk change. Contract step (if ever needed) is a later spec.

## API and breaking changes
- New: `PATCH /appointments/{appointment_id}/cancel`, body `{"reason": "..."}`. Success returns 200 and the appointment.
- Errors: 404 (unknown id, problem document via `AppError`), 409 (already cancelled, `AppError`), 422 (reason missing or
  too short or too long, FastAPI request validation from the schema).
- Additive change to `AppointmentOut`: `cancelled_at`, `cancel_reason`, `cancelled_late`. Existing clients that ignore
  unknown fields are unaffected. No breaking changes.

Decisions that fix the exact behaviour:
- Late means `starts_at - cancelled_at` is strictly less than 24 hours. Exactly 24 hours (86400 s) is NOT late.
  A cancellation after the start time is also less than 24 hours, so it is late.
- `cancelled_at` is the service `now`, taken from the same naive clock as `starts_at` (as in the reschedule route and
  the reminder service). The route passes `datetime.now()`; tests inject `now`.
- The reason is trimmed of surrounding whitespace before the 3 to 200 length check, and the trimmed text is stored.
- The check for "already cancelled" runs before the reason is applied, so the first cancellation is never overwritten.
- 404 is checked before 409; validation (422) happens before both because it is done by the request schema.

## Contracts between tasks
Tasks run in parallel and hand work to each other, so the names and signatures they share are fixed here. An agent
that wants to change one of them stops and asks a human.

```python
# backend/app/models.py   (task T-002-01)
class Appointment(Base):
    # existing columns unchanged, plus:
    cancelled_at: Mapped[datetime | None]        # DateTime, nullable, no default
    cancel_reason: Mapped[str | None]            # String(200), nullable
    cancelled_late: Mapped[bool]                 # Boolean, NOT NULL, default False, server_default false

# backend/app/schemas.py   (task T-002-02)
class CancelRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=200)

class AppointmentOut(AppointmentCreate):         # three new optional fields
    cancelled_at: datetime | None = None
    cancel_reason: str | None = None
    cancelled_late: bool = False

# backend/app/appointments/cancellation.py   (task T-002-02)
LATE_CANCEL_WINDOW = timedelta(hours=24)
def cancel_appointment(db: Session, appointment_id: int, reason: str, now: datetime) -> Appointment
# raises AppError(404, "Not Found", ...) when the id is unknown
# raises AppError(409, "Already Cancelled", ...) when cancelled_at is already set
# raises AppError(422, "Invalid Reason", ...) when the trimmed reason is not 3 to 200 characters

# backend/app/routes/appointments.py   (task T-002-02)
PATCH /appointments/{appointment_id}/cancel   body CancelRequest   returns AppointmentOut (200)

# backend/app/reminders/service.py   (task T-002-03)
# send_due_reminders signature is unchanged; it skips any Appointment whose cancelled_at is not None.
# Skipped cancelled appointments are not counted in any RunSummary field.
```

## Threat-model delta
- New data: a free-text cancellation reason. It may contain health information typed by staff. It is stored only in
  `appointments.cancel_reason`, is never sent over SMS (the reminder message body is unchanged), and is never written
  to logs or to error messages (the 409 and 404 details contain the appointment id only).
- Reason is length-limited to 200 characters and handled only through SQLAlchemy parameters (no string-built SQL).
- Abuse: any caller of the endpoint can cancel any appointment because authentication is out of scope for this spec.
  Mitigations in this release: cancellation is one-way and idempotent-safe (the second call returns 409 and cannot
  overwrite the first reason or time). Authentication for operator endpoints is a follow-up before real use.
- New trust boundary: none. No network calls, no new dependencies.

## Test plan
| AC | Test layer | Test name pattern |
|---|---|---|
| SPEC002/AC-1 | integration (API) | `test_SPEC002_AC1_*` |
| SPEC002/AC-2 | integration (API), including missing, 2-character and whitespace-only reasons, and a check that the row is unchanged | `test_SPEC002_AC2_*` |
| SPEC002/AC-3 | integration (API), second call returns 409 and the first reason and time are kept | `test_SPEC002_AC3_*` |
| SPEC002/AC-4 | unit (injected `now`), with boundary cases at 23:59:59, exactly 24:00:00 (not late) and after the start | `test_SPEC002_AC4_*` |
| SPEC002/AC-5 | unit (fake provider), cancelled appointment gets no send and no Reminder row | `test_SPEC002_AC5_*` |
| SPEC002/AC-6 | integration (API), status 404 and an `application/problem+json` body | `test_SPEC002_AC6_*` |

Boundary cases for AC-1 (reason of 3 and of 200 characters accepted) belong with the AC-1 tests.
Acceptance tests are written first and reviewed by a human before the implementation task starts.

## Rollout and rollback
No feature flag: the endpoint only acts when called. Rollback is to stop calling it and revert the application code;
the three columns are additive and nullable or defaulted, so they can stay. Appointments already cancelled stay
cancelled and, if the reminder change is reverted, would become eligible for reminders again, so revert T-002-03 only
together with a decision on those rows.

## Decisions (ADR candidates)
- `cancelled_at` as the cancellation marker (no status enum): one fact, one place, and the timestamp is needed anyway.
  Rejected: a `status` column, which would duplicate the timestamp and invite disagreement.
- `cancelled_late` is stored at cancellation time rather than computed on read: the later fee and reporting work needs
  the value as it was judged then, even if the appointment is rescheduled afterwards.
- Server default false on `cancelled_late`: safe for existing rows and for writers that do not know the column.
- Cancelled appointments are skipped by the reminder job with no new counter, so `RunSummary` and its API response do not change.
