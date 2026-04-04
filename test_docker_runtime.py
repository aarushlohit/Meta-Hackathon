from fastapi.testclient import TestClient

from env import CyberEnv
from server.app import app


def test_runtime_environment_initializes():
    env = CyberEnv(task="easy")
    obs = env.reset()

    assert obs is not None
    assert isinstance(obs.alerts, list)
    assert isinstance(obs.risk_score, int)


def test_runtime_reset_after_startup():
    client = TestClient(app)

    r1 = client.post("/reset", json={"task": "easy"})
    r2 = client.post("/reset", json={"task": "medium"})

    assert r1.status_code == 200
    assert r2.status_code == 200

    payload_2 = r2.json()
    assert "observation" in payload_2
    assert isinstance(payload_2["observation"], dict)


def test_runtime_step_after_startup_no_crash():
    client = TestClient(app)

    client.post("/reset", json={"task": "hard"})
    step_response = client.post("/step", json={"message": "resolve failed_login"})

    assert step_response.status_code == 200
    payload = step_response.json()

    assert isinstance(payload, dict)
    assert isinstance(payload.get("observation"), dict)
    assert isinstance(payload.get("reward"), float)
    assert isinstance(payload.get("done"), bool)
    assert isinstance(payload.get("info"), dict)
