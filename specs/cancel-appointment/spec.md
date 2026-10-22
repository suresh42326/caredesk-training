# SPEC002: Cancel an appointment with a reason

Status: Approved  
Owner: Product owner (CareDesk)  
Risk tier: Medium (the migration task is High)

## Problem and outcome
Front-desk staff cannot record that an appointment was cancelled or why, so cancelled slots look booked and late cancellations cannot be told apart from early ones. Staff will cancel an appointment with a reason, and the system will remember when it was cancelled and whether it was late.  
**Success measure:** share of cancelled appointments that carry a reason and a cancellation time goes from 0% to 100%; zero reminders sent for cancelled appointments.

## User stories
- US-1: As a front-desk operator, I want to cancel an appointment and record why, so that the schedule and the history are accurate.
- US-2: As a front-desk operator, I want late cancellations to be marked, so that the clinic can follow up on them later.
- US-3: As a patient, I want no reminder for an appointment that was cancelled, so that I am not confused.

## Acceptance criteria (EARS, one behaviour each)

Definition of late: an appointment is late-cancelled when the time from the cancellation to its start is strictly
less than 24 hours (24 hours is 86400 seconds). Exactly 24 hours is not late.

| ID | Criterion | Test layer |
|---|---|---|
| SPEC002/AC-1 | When an operator cancels an appointment with a reason of 3 to 200 characters, the system shall mark it cancelled, store the reason and the cancellation time, and return the appointment. | integration |
| SPEC002/AC-2 | If the reason is missing or shorter than 3 characters, then the system shall reject the request with status 422 and leave the appointment unchanged. | integration |
| SPEC002/AC-3 | If an appointment is already cancelled, then the system shall reject a second cancellation with status 409 and keep the first cancellation unchanged. | integration |
| SPEC002/AC-4 | When an appointment is cancelled less than 24 hours before its start, the system shall mark the cancellation as late. | unit |
| SPEC002/AC-5 | While an appointment is cancelled, the reminder job shall send no reminder for it. | unit |
| SPEC002/AC-6 | If the appointment does not exist, then the system shall respond with status 404 and a problem document. | integration |

Every criterion is testable and maps to at least one automated test whose name contains the AC id
(for example `test_SPEC002_AC1_...`).

## Out of scope
- Charging the late-cancellation fee.
- Un-cancelling an appointment.
- Notifying the patient of the cancellation.
- Authentication and authorisation of operators.

## Open questions (filled by grilling)

| # | Question | Owner | Resolved answer |
|---|---|---|---|
| 1 | Is a cancellation exactly 24 hours before the start "late"? | Suresh Karri | No. Late means strictly less than 24 hours. Exactly 24 hours is not late, and a boundary test pins both sides. |
| 2 | Can a cancellation be undone? | Suresh Karri | No. Un-cancelling is out of scope; a cancelled appointment stays cancelled. |
| 3 | What happens to reminders already sent for this appointment? | Suresh Karri | Nothing is recalled. The reminder job simply sends no further reminder for a cancelled appointment (AC-5). |
| 4 | Is the reason free text, and may it be logged? | Suresh Karri | Free text, trimmed, 3 to 200 characters. It is never written to application logs; only the appointment row stores it. |
| 5 | Is a cancellation a delete or a status change? | Suresh Karri | A status change: set `cancelled_at`, `cancel_reason` and `cancelled_late`; never delete the row. |
| 6 | Which clock decides "now" and "late"? | Suresh Karri | The injected `get_now` clock used by the reminder job, so tests are deterministic; the same clock decides the 24-hour boundary. |

A spec is **Approved** only when every open question has a resolved answer.

## Approval
Product owner: ________  Tech lead: ________  Date: ________

- **Approval:** Tech lead: Suresh Karri  Date: 2026-10-22
