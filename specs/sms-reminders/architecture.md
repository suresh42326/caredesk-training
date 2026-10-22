# Architecture: SMS appointment reminders

*Example output of the `architect` persona, written from the analyst brief.*

## Context
Add a reminder job that texts patients shortly before an appointment, with idempotency, opt-out, retries and an operator view.

## Constraints from the existing system
- FastAPI app with routes -> schemas -> models layering; errors via `AppError`.
- Schema changes are generated Alembic revisions in `backend/migrations/`; tooling lives in `backend/alembic/`.
- Tests run on in-memory SQLite with the `client` fixture; no network in tests.

## Components
- `SmsProvider` interface with a `FakeSmsProvider` (no network). A real provider can replace it later.
- `ReminderService.send_due_reminders(db, provider, now)`: selects appointments in the next 24 hours, skips opted-out and
  already-reminded ones, sends with bounded retries, records the outcome.
- Routes: run the job, list an appointment's reminders, set a patient's contact record.

## Data
- `patient_contacts(patient_id, phone, opted_out)`.
- `reminders(id, appointment_id UNIQUE, status, attempts, sent_at, error)`. The unique constraint is the duplicate guard.

## Interfaces
`POST /reminders/run`, `GET /appointments/{id}/reminders`, `PUT /patients/{id}/contact`. No existing endpoint changes.

## Risks and risk tier
- A migration is **High risk**; the service and API tasks are Medium; the provider interface is Low.
- Phone numbers are personal data: never log them or put them in error text.
- The message body must exclude the visit reason.

## Options considered
- Duplicate guard in code only: rejected, it races under concurrent runs. Chosen: database unique constraint.
- Re-sending failed reminders automatically: rejected, risks surprise messages after an outage.
- A background scheduler now: deferred; an endpoint is enough for the first release.

## Decisions to confirm
1. One reminder per appointment id, even if the appointment is rescheduled.
2. Failed reminders are not retried by later runs; operators follow up.
3. Time zones and quiet hours are a follow-up.
