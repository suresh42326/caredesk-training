from datetime import datetime, timedelta

import pytest

from app.main import app
from app.routes.reminders import get_now

NOW = datetime(2030, 1, 15, 9, 0)


@pytest.fixture()
def clock(client):
    app.dependency_overrides[get_now] = lambda: NOW


def book(client, starts_at):
    resp = client.post(
        "/appointments",
        json={"patient_id": 1, "starts_at": starts_at.isoformat(), "duration_min": 30, "reason": "Check-up"},
    )
    assert resp.status_code == 201
    return resp.json()["id"]


def cancel(client, appt_id, reason="Patient is travelling"):
    return client.post(f"/appointments/{appt_id}/cancel", json={"reason": reason})


def test_SPEC002_AC1_cancelling_marks_the_appointment_and_records_reason_and_time(client, clock):
    appt_id = book(client, NOW + timedelta(days=5))

    resp = cancel(client, appt_id, "Patient is travelling")

    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == appt_id
    assert body["cancel_reason"] == "Patient is travelling"
    assert body["cancelled_at"] == NOW.isoformat()
    assert client.get(f"/appointments/{appt_id}").json()["cancelled_at"] == NOW.isoformat()


@pytest.mark.parametrize("reason", ["x", "  ", ""])
def test_SPEC002_AC2_a_missing_or_short_reason_is_rejected_and_nothing_changes(client, clock, reason):
    appt_id = book(client, NOW + timedelta(days=5))

    resp = cancel(client, appt_id, reason)

    assert resp.status_code == 422
    assert client.get(f"/appointments/{appt_id}").json()["cancelled_at"] is None


def test_SPEC002_AC2_a_missing_reason_field_is_rejected(client, clock):
    appt_id = book(client, NOW + timedelta(days=5))
    assert client.post(f"/appointments/{appt_id}/cancel", json={}).status_code == 422


def test_SPEC002_AC3_cancelling_twice_conflicts_and_keeps_the_first_cancellation(client, clock):
    appt_id = book(client, NOW + timedelta(days=5))
    cancel(client, appt_id, "First reason")

    resp = cancel(client, appt_id, "Second reason")

    assert resp.status_code == 409
    assert resp.json()["title"] == "Already Cancelled"
    assert client.get(f"/appointments/{appt_id}").json()["cancel_reason"] == "First reason"


@pytest.mark.parametrize(
    ("hours_ahead", "late"),
    [(23, True), (23.99, True), (24, False), (25, False), (72, False)],
)
def test_SPEC002_AC4_cancellations_less_than_24_hours_ahead_are_marked_late(client, clock, hours_ahead, late):
    appt_id = book(client, NOW + timedelta(hours=hours_ahead))

    body = cancel(client, appt_id).json()

    assert body["cancelled_late"] is late


def test_SPEC002_AC6_cancelling_an_unknown_appointment_returns_a_problem_document(client, clock):
    resp = cancel(client, 999)
    assert resp.status_code == 404
    assert resp.json()["title"] == "Not Found"
