from fastapi.testclient import TestClient

from server.app import app


client = TestClient(app)


def _validate_step_like_response(payload):
    assert isinstance(payload, dict)
    assert "observation" in payload
    assert "reward" in payload
    assert "done" in payload
    assert "info" in payload

    assert isinstance(payload["observation"], dict)
    assert isinstance(payload["reward"], float)
    assert isinstance(payload["done"], bool)
    assert isinstance(payload["info"], dict)


def test_post_reset_returns_200_and_valid_structure():
    response = client.post("/reset", json={"task": "easy"})
    assert response.status_code == 200

    payload = response.json()
    _validate_step_like_response(payload)

    obs = payload["observation"]
    assert "alerts" in obs
    assert "risk_score" in obs
    assert "time_left" in obs
    assert "history" in obs


def test_post_step_returns_200_and_valid_structure():
    client.post("/reset", json={"task": "medium"})

    response = client.post("/step", json={"message": "investigate phishing_email"})
    assert response.status_code == 200

    payload = response.json()
    _validate_step_like_response(payload)

    assert 0.0 <= payload["reward"] <= 1.0


def test_api_never_crashes_on_bad_payloads():
    client.post("/reset", json={"task": "hard"})

    # Missing expected semantic command but valid JSON shape
    response = client.post("/step", json={"message": ""})
    assert response.status_code == 200
    payload = response.json()
    _validate_step_like_response(payload)

    # Unknown task should still be safely handled
    response_reset = client.post("/reset", json={"task": "unknown_task"})
    assert response_reset.status_code == 200
    _validate_step_like_response(response_reset.json())
