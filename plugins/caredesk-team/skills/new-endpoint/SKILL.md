---
name: new-endpoint
description: Scaffold a new CareDesk REST endpoint test-first - failing tests, schema, route, registration, green tests. Invoke explicitly with /new-endpoint <resource> <action>.
argument-hint: "<resource> <action>"
disable-model-invocation: true
allowed-tools: Read Grep Glob Edit Write Bash(uv run pytest *) Bash(uv run ruff *) Bash(git diff *)
---

# Add a CareDesk endpoint: $ARGUMENTS

Working tree right now:
!`git status --short`

Follow these steps in order. Stop and ask if the request is ambiguous.

1. **Learn the pattern.** Read `backend/app/routes/appointments.py`, `backend/app/schemas.py` and
   `backend/tests/test_reschedule.py`. Match their style.
2. **Tests first.** Create `backend/tests/test_<resource>.py`. Cover success, validation failure and
   not-found. Assert the status code AND the response body; for rejected writes also re-fetch and assert
   that nothing changed. Run the tests and show that they fail for the right reason.
3. **Implement.** Add request/response schemas to `schemas.py`, the route under `backend/app/routes/`,
   and register the router in `main.py`. Raise `AppError` for domain errors.
4. **Verify.** Run `cd backend && uv run pytest -q` and `uv run ruff check .`. Fix failures; never weaken a test.
5. **Report.** List files changed, tests added, and any assumption you made.
