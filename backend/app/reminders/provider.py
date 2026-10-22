"""SMS provider interface and an in-memory fake for development and tests."""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class SendResult:
    ok: bool
    transient: bool = False  # only meaningful when ok is False: True means "worth retrying"
    error: str | None = None


class SmsProvider(Protocol):
    def send(self, to: str, body: str) -> SendResult: ...


@dataclass
class FakeSmsProvider:
    """Records messages; script outcomes through `queue` (one consumed per call)."""

    sent: list[tuple[str, str]]  # (to, body) of every successful send
    queue: list[SendResult]  # empty means success
    calls: int  # number of send calls

    def send(self, to: str, body: str) -> SendResult:
        self.calls += 1
        result = self.queue.pop(0) if self.queue else SendResult(ok=True)
        if result.ok:
            self.sent.append((to, body))
        return result
