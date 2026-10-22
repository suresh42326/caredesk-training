from fastapi import Request
from fastapi.responses import JSONResponse


class AppError(Exception):
    """Domain error rendered as an RFC 7807 problem document."""

    def __init__(self, status: int, title: str, detail: str):
        self.status = status
        self.title = title
        self.detail = detail


async def app_error_handler(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, AppError)
    return JSONResponse(
        status_code=exc.status,
        media_type="application/problem+json",
        content={"title": exc.title, "status": exc.status, "detail": exc.detail},
    )
