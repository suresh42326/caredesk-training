# Design: SPEC001 SMS appointment reminders

Spec: specs/sms-reminders/spec.md (Approved)

## What changes (architecture delta)
- New package `backend/app/reminders/` with an `SmsProvider` interface, a `FakeSmsProvider` for development and tests,
  and a `ReminderService` that decides which reminders to send and records the outcome.
- New routes `backend/app/routes/reminders.py`: run the reminder job, list an appointment's reminders, update a
  patient's contact record.
- The provider is injected through a FastAPI dependency so tests (and later the real provider) can replace it.

## Data model and migration
Two new tables, added by one generated Alembic revision (expand only, nothing is dropped or changed):

| Table | Columns |
|---|---|
| `patient_contacts` | `patient_id` (primary key), `phone` (text), `opted_out` (boolean, default false) |
| `reminders` | `id`, `appointment_id` (indexed, **unique**), `status` (`sent` or `failed`), `attempts`, `sent_at` (nullable), `error` (nullable) |

The unique constraint on `appointment_id` is the duplicate guard behind AC-3. The revision is generated with
`alembic revision --autogenerate` and reviewed by a human; it is never edited by hand. A migration is a High-risk change.

## API and breaking changes
No existing endpoint changes. New: `POST /reminders/run` (runs the job, returns counts), `GET /appointments/{id}/reminders`,
`PUT /patients/{id}/contact`.

## Contracts between tasks
Tasks run in parallel and hand work to each other, so the names and signatures they share are fixed here. An agent
that wants to change one of them stops and asks a human.

```python
# backend/app/reminders/provider.py   (task T-001-02)
@dataclass(frozen=True)
class SendResult:
    ok: bool
    transient: bool = False      # only meaningful when ok is False: True means "worth retrying"
    error: str | None = None

class SmsProvider(Protocol):
    def send(self, to: str, body: str) -> SendResult: ...

@dataclass
class FakeSmsProvider:           # records messages; script outcomes through `queue`
    sent: list[tuple[str, str]]  # (to, body) of every successful send
    queue: list[SendResult]      # consumed one per send call; empty means success
    calls: int                   # number of send calls

# backend/app/models.py             (task T-001-01)
PatientContact(patient_id, phone, opted_out)
Reminder(id, appointment_id, status, attempts, sent_at, error)    # status is "sent" or "failed"

# backend/app/reminders/service.py  (task T-001-03)
def send_due_reminders(db, provider, now, sleep=time.sleep) -> RunSummary
RunSummary(sent, failed, skipped_opted_out, skipped_duplicate)
```

## Threat-model delta
- New personal data: phone numbers. They are stored only in `patient_contacts` and never written to logs or error messages.
- The message body is built from the appointment date and time only (AC-6). The visit reason is health information and
  must never be sent over SMS.
- Abuse: `POST /reminders/run` can send many messages. It is idempotent per appointment (AC-3) and, in this release,
  only talks to the fake provider. Authentication for operator endpoints is a follow-up before real delivery.

## Test plan
| AC | Test layer | Test name pattern |
|---|---|---|
| SPEC001/AC-1 | unit | `test_SPEC001_AC1_*` |
| SPEC001/AC-2 | unit | `test_SPEC001_AC2_*` |
| SPEC001/AC-3 | unit and model constraint | `test_SPEC001_AC3_*` |
| SPEC001/AC-4 | unit (fake provider, injected sleep) | `test_SPEC001_AC4_*` |
| SPEC001/AC-5 | unit | `test_SPEC001_AC5_*` |
| SPEC001/AC-6 | unit | `test_SPEC001_AC6_*` |
| SPEC001/AC-7 | integration (API) | `test_SPEC001_AC7_*` |

Acceptance tests are written first and reviewed by a human before the implementation task starts.

## Rollout and rollback
The job only runs when someone calls the endpoint, so there is nothing to switch off. Rollback is to stop calling the
endpoint; the tables are additive and can stay. No real SMS is sent in this release.

## Decisions (ADR candidates)
- Duplicate guard in the database (unique constraint) rather than only in code: survives concurrent runs.
- Failed reminders are not re-sent automatically: avoids surprise messages after an outage.
