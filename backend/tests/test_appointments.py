def _payload(**overrides):
    body = {
        "patient_id": 1,
        "starts_at": "2030-01-15T09:00:00",
        "duration_min": 30,
        "reason": "Annual check-up",
    }
    body.update(overrides)
    return body


def test_create_and_get_appointment(client):
    created = client.post("/appointments", json=_payload())
    assert created.status_code == 201
    appt_id = created.json()["id"]

    fetched = client.get(f"/appointments/{appt_id}")
    assert fetched.status_code == 200
    assert fetched.json()["reason"] == "Annual check-up"


def test_get_missing_appointment_returns_problem_document(client):
    resp = client.get("/appointments/999")
    assert resp.status_code == 404
    assert resp.json()["title"] == "Not Found"


def test_create_rejects_too_short_reason(client):
    resp = client.post("/appointments", json=_payload(reason="x"))
    assert resp.status_code == 422


def test_list_filters_by_patient(client):
    client.post("/appointments", json=_payload(patient_id=1))
    client.post("/appointments", json=_payload(patient_id=2, starts_at="2030-01-16T09:00:00"))
    resp = client.get("/appointments", params={"patient_id": 2})
    assert [a["patient_id"] for a in resp.json()] == [2]
