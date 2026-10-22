# Brief: SMS appointment reminders

*Example output of the `analyst` persona. Yours will differ; what matters is the structure and the separation of facts from assumptions.*

## Problem
Patients miss appointments because nothing reminds them. Each no-show wastes clinician time and delays other patients.
Front-desk staff currently phone patients by hand, which does not scale.

## Users and stakeholders
- **Patients:** receive the reminder; some will not want text messages.
- **Front-desk operators:** need to know whether a reminder went out, to follow up by phone.
- **Clinic manager:** cares about the no-show rate and the cost of messages.
- **Privacy lead:** cares about consent and what appears in a message.

## Goals and success measure
- Reduce the no-show rate (assumed baseline 12%, target 8% within two months).
- Never contact a patient who has opted out.

## Constraints and facts found in the repo
- Fact: appointments have `patient_id`, `starts_at`, `duration_min` and a free-text `reason` (`backend/app/models.py`).
- Fact: there is no stored phone number or consent flag for patients today.
- Fact: the database schema is managed by generated Alembic revisions; revisions are never hand-edited.
- Fact: errors use the `AppError` / RFC 7807 pattern; tests use the `client` fixture and no database mocks.
- Fact: `seed/patients.csv` holds synthetic personal data and must not be read by agents.

## Assumptions
- A: One reminder per appointment, about a day before, is enough.
- A: Real SMS delivery is out of scope for the first release (a fake provider stands in).
- A: Patients' phone numbers will be loaded from the patient system by a separate process.

## Risks
- **Privacy:** the visit reason is health information; it must never appear in an SMS.
- **Consent:** texting an opted-out patient is a compliance incident.
- **Duplicates:** repeated runs or concurrent jobs could text a patient twice.
- **Provider outages:** retries could spam; giving up silently could hide failures.
- **Cost:** a bug could send many messages.

## Open questions
1. What exactly counts as "once" if an appointment is rescheduled?
2. What may the message contain?
3. What should happen when the provider is down for hours?
4. Where is opt-out stored, and who is the authority for it?
5. How do we test without sending real messages?
6. Do we need time-zone handling and quiet hours in the first release?
