# SPEC001: SMS appointment reminders

Status: Approved  
Owner: Product owner (CareDesk)  
Risk tier: Medium (High if it ever sends to real patients: the migration task is High)

## Problem and outcome
Patients miss appointments because nothing reminds them, which wastes clinician time. CareDesk will text each
patient once, shortly before their appointment, unless they have opted out.  
**Success measure:** no-show rate falls from 12% to 8% within two months of launch; zero messages sent to opted-out patients.

## User stories
- US-1: As a patient, I want a text reminder before my appointment, so that I do not forget it.
- US-2: As a patient, I want to opt out of texts, so that I control how the clinic contacts me.
- US-3: As a front-desk operator, I want to see whether a reminder was sent or failed, so that I can follow up by phone.

## Acceptance criteria (EARS, one behaviour each)

| ID | Criterion | Test layer |
|---|---|---|
| SPEC001/AC-1 | When an appointment starts within the next 24 hours and no reminder has been recorded for it, the system shall send one SMS reminder to the patient's phone number. | unit |
| SPEC001/AC-2 | While a patient is opted out or has no phone number, the system shall not send any SMS to that patient. | unit |
| SPEC001/AC-3 | If a reminder has already been recorded for an appointment, then the system shall not send another reminder for it. | unit |
| SPEC001/AC-4 | If the SMS provider returns a transient error, then the system shall retry with exponential backoff up to 3 attempts in total and then record the reminder as failed. | unit |
| SPEC001/AC-5 | If the SMS provider returns a permanent error, then the system shall record the reminder as failed without retrying. | unit |
| SPEC001/AC-6 | The reminder message shall contain the appointment date and time and shall not contain the visit reason or any other health information. | unit |
| SPEC001/AC-7 | When an operator requests the reminders of an appointment, the system shall return the status and number of attempts of each reminder. | integration |

Every criterion maps to at least one automated test whose name contains the AC id (for example `test_SPEC001_AC1_...`).

## Out of scope
- Real SMS delivery: Day 3 uses a fake provider behind an interface.
- Two-way replies (for example replying CANCEL), WhatsApp or email fallback, message translation.
- Automatic re-sending of reminders recorded as failed (operators follow up by phone).
- A scheduler process: the run is triggered by an endpoint; scheduling comes later.

## Open questions (filled by grilling)

| # | Question | Owner | Resolved answer |
|---|---|---|---|
| 1 | What counts as "once" when an appointment is rescheduled? | Product owner | One reminder per appointment id. A rescheduled appointment keeps its id, so no second reminder. Revisit if this causes confusion. |
| 2 | What may appear in the message body? | Tech lead | Date and time only, plus an opt-out hint. No visit reason, clinician or diagnosis (health information). Covered by AC-6. |
| 3 | What happens if the provider is down for hours? | Tech lead | Three attempts with backoff, then the reminder is recorded as failed. No automatic late send; operators follow up (AC-4). |
| 4 | Who is the authority for opt-out and where is it stored? | Product owner | The patient contact record holds the phone number and an opted-out flag; opted-out patients are never texted (AC-2). |
| 5 | How do we test without sending real SMS? | Tech lead | A fake provider records messages and can be told to fail transiently or permanently. No network in tests. |
| 6 | Can a failed reminder be retried later by another run? | Product owner | No. A recorded reminder blocks further sends (AC-3); a failed one is visible to operators (AC-7). |
| 7 | What about time zones and quiet hours? | Product owner | Out of scope for this release: the window is the next 24 hours from the run time. Recorded as a follow-up. |

## Approval
Product owner: Priya Nair  Tech lead: Arjun Mehta  Date: 2026-10-22
