def _make(client, **overrides):
    body = {
        "patient_id": 1,
        "starts_at": "2030-01-15T09:00:00",
        "duration_min": 30,
        "reason": "Annual check-up",
    }
    body.update(overrides)
    resp = client.post("/appointments", json=body)
    assert resp.status_code == 201
    return resp.json()


def test_reschedule_moves_the_appointment(client):
    appt = _make(client)
    resp = client.patch(
        f"/appointments/{appt['id']}/reschedule", json={"starts_at": "2030-01-20T10:00:00"}
    )
    assert resp.status_code == 200
    assert resp.json()["starts_at"] == "2030-01-20T10:00:00"
    assert client.get(f"/appointments/{appt['id']}").json()["starts_at"] == "2030-01-20T10:00:00"


def test_reschedule_overlap_returns_conflict_and_leaves_original_unchanged(client):
    first = _make(client, starts_at="2030-01-15T09:00:00")
    second = _make(client, starts_at="2030-01-16T09:00:00")

    resp = client.patch(
        f"/appointments/{second['id']}/reschedule", json={"starts_at": "2030-01-15T09:15:00"}
    )

    assert resp.status_code == 409
    body = resp.json()
    assert body["title"] == "Conflict"
    assert str(first["id"]) in body["detail"]
    # The rejected move must not have changed anything.
    assert client.get(f"/appointments/{second['id']}").json()["starts_at"] == "2030-01-16T09:00:00"


def test_reschedule_back_to_back_is_allowed(client):
    _make(client, starts_at="2030-01-15T09:00:00", duration_min=30)
    second = _make(client, starts_at="2030-01-16T09:00:00")
    resp = client.patch(
        f"/appointments/{second['id']}/reschedule", json={"starts_at": "2030-01-15T09:30:00"}
    )
    assert resp.status_code == 200


def test_reschedule_into_the_past_is_rejected(client):
    appt = _make(client)
    resp = client.patch(
        f"/appointments/{appt['id']}/reschedule", json={"starts_at": "2020-01-01T09:00:00"}
    )
    assert resp.status_code == 422
    assert resp.json()["title"] == "Invalid Time"
    assert client.get(f"/appointments/{appt['id']}").json()["starts_at"] == "2030-01-15T09:00:00"


def test_reschedule_unknown_appointment_is_404(client):
    resp = client.patch("/appointments/999/reschedule", json={"starts_at": "2030-02-01T09:00:00"})
    assert resp.status_code == 404
