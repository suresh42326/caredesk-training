---
name: fastapi-conventions
description: CareDesk FastAPI backend conventions - layering, response models, status codes, AppError and RFC 7807 errors, validation, pagination. Use when writing or reviewing code under backend/app/ (routes, schemas, models, errors).
---

# FastAPI conventions for CareDesk

Apply these when you add or change backend code. The detailed rules, with reasons and examples, are in
[reference.md](reference.md) - read it when you need the exact rule, not by default.

## The short version
- Layering: routes -> schemas -> models. No SQL strings in routes.
- Every route has `response_model`; creation returns 201 + the resource; deletion returns 204.
- Sessions come from `Depends(get_db)`.
- Domain errors: `raise AppError(status, title, detail)` (RFC 7807 body).
- Validation lives in Pydantic `Field(...)` constraints in `schemas.py`.
- Register new routers in `main.py`. Add tests for every endpoint.
