from fastapi import FastAPI

from app.errors import AppError, app_error_handler
from app.routes import appointments, cancellation, reminders

# Tables are created by Alembic migrations (`uv run alembic upgrade head`), not at import time.

app = FastAPI(title="CareDesk")
app.add_exception_handler(AppError, app_error_handler)
app.include_router(appointments.router)
app.include_router(reminders.router)
app.include_router(cancellation.router)


@app.get("/health")
def health():
    return {"status": "ok"}
