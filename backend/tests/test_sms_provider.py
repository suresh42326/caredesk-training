"""Acceptance tests for the SMS provider interface and FakeSmsProvider (T-001-02).

Contract: specs/sms-reminders/design.md, "Contracts between tasks". No database and no network.
"""

import dataclasses

import pytest

from app.reminders.provider import FakeSmsProvider, SendResult, SmsProvider


def make_provider(queue: list[SendResult] | None = None) -> FakeSmsProvider:
    return FakeSmsProvider(sent=[], queue=list(queue or []), calls=0)


# --- SendResult contract -------------------------------------------------------------------


def test_SPEC001_AC4_send_result_defaults_are_not_transient_and_no_error():
    result = SendResult(ok=True)
    assert result.ok is True
    assert result.transient is False
    assert result.error is None


def test_SPEC001_AC4_send_result_is_frozen():
    result = SendResult(ok=False, transient=True, error="timeout")
    with pytest.raises(dataclasses.FrozenInstanceError):
        result.ok = True


def test_SPEC001_AC4_fake_provider_satisfies_sms_provider_interface():
    provider: SmsProvider = make_provider()
    assert callable(provider.send)


# --- success -------------------------------------------------------------------------------


def test_SPEC001_AC4_success_with_empty_queue_returns_ok_and_records_message():
    provider = make_provider()

    result = provider.send("+15550001", "Reminder: 2030-01-01 09:00")

    assert result == SendResult(ok=True)
    assert provider.sent == [("+15550001", "Reminder: 2030-01-01 09:00")]
    assert provider.calls == 1


def test_SPEC001_AC4_success_records_every_message_in_order():
    provider = make_provider()

    provider.send("+15550001", "first")
    provider.send("+15550002", "second")

    assert provider.sent == [("+15550001", "first"), ("+15550002", "second")]
    assert provider.calls == 2


def test_SPEC001_AC4_queued_success_result_is_recorded_and_consumed():
    provider = make_provider([SendResult(ok=True)])

    result = provider.send("+15550001", "hello")

    assert result.ok is True
    assert provider.sent == [("+15550001", "hello")]
    assert provider.queue == []


# --- transient failure (AC-4) ---------------------------------------------------------------


def test_SPEC001_AC4_transient_failure_is_returned_as_retryable():
    provider = make_provider([SendResult(ok=False, transient=True, error="timeout")])

    result = provider.send("+15550001", "hello")

    assert result.ok is False
    assert result.transient is True
    assert result.error == "timeout"


def test_SPEC001_AC4_transient_failure_is_not_recorded_as_sent_but_counts_as_a_call():
    provider = make_provider([SendResult(ok=False, transient=True, error="timeout")])

    provider.send("+15550001", "hello")

    assert provider.sent == []
    assert provider.calls == 1
    assert provider.queue == []


def test_SPEC001_AC4_transient_failures_then_success_are_consumed_one_per_call():
    provider = make_provider(
        [
            SendResult(ok=False, transient=True, error="t1"),
            SendResult(ok=False, transient=True, error="t2"),
        ]
    )

    first = provider.send("+15550001", "hello")
    second = provider.send("+15550001", "hello")
    third = provider.send("+15550001", "hello")

    assert (first.ok, first.transient, first.error) == (False, True, "t1")
    assert (second.ok, second.transient, second.error) == (False, True, "t2")
    assert third.ok is True
    assert provider.calls == 3
    assert provider.sent == [("+15550001", "hello")]
    assert provider.queue == []


# --- permanent failure (AC-5) ---------------------------------------------------------------


def test_SPEC001_AC5_permanent_failure_is_returned_as_not_retryable():
    provider = make_provider([SendResult(ok=False, transient=False, error="invalid number")])

    result = provider.send("+15550001", "hello")

    assert result.ok is False
    assert result.transient is False
    assert result.error == "invalid number"


def test_SPEC001_AC5_permanent_failure_is_not_recorded_as_sent_but_counts_as_a_call():
    provider = make_provider([SendResult(ok=False, transient=False, error="invalid number")])

    provider.send("+15550001", "hello")

    assert provider.sent == []
    assert provider.calls == 1
    assert provider.queue == []


def test_SPEC001_AC5_failure_does_not_affect_later_sends_once_queue_is_empty():
    provider = make_provider([SendResult(ok=False, transient=False, error="invalid number")])

    provider.send("+15550001", "hello")
    later = provider.send("+15550002", "again")

    assert later.ok is True
    assert provider.sent == [("+15550002", "again")]
    assert provider.calls == 2
