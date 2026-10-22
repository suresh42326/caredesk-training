---
paths:
  - "backend/tests/**/*.py"
---

# Test conventions (backend)

- Use pytest with the `client` fixture from `conftest.py`; no mocking of the database.
- One test file per route module; name tests `test_<behaviour>`.
- Assert the status code AND the response body of every response; for rejected writes, re-fetch and assert nothing changed.
- Use fixed future dates (2030-...) so tests never depend on the current date.
- A bug fix starts with a failing test that reproduces the bug.
