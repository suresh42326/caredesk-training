# FastAPI conventions - detailed reference

## Layering
Routes call plain functions and the session; they never build SQL strings. Models never import from routes.
Business rules (for example the overlap check for rescheduling) live in plain functions that can be tested alone.

## Responses
- Every route declares `response_model`, plus `status_code` when it is not 200.
- Creation endpoints return 201 and the created resource. Deletion endpoints return 204 with no body.
- Lists are ordered deterministically. Pagination uses `limit` (default 20, maximum 100) and `offset`.
- Datetimes are timezone-naive UTC in the database and ISO 8601 strings in JSON.

## Errors
- Raise `AppError(status, title, detail)` for domain errors. Never return bare strings or dicts as errors.
- Error bodies follow RFC 7807: `title`, `status`, `detail`, served as `application/problem+json`.
- Never catch bare `Exception` in routes; let unexpected errors surface as 500.

## Validation
- Request schemas live in `schemas.py` and use Pydantic v2 `Field(...)` constraints.
- Path parameters are typed. Filter query parameters use `| None = None`.

## Style
- Keep route functions under 30 lines.
- Log with `logging`, never `print`.
- Register new route modules in `main.py` with `app.include_router`.
