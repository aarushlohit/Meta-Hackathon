from pathlib import Path

from env import CyberEnv
from grader import grade_state
from models import CyberAction


def test_task_files_exist_and_are_referenced():
    root = Path(__file__).resolve().parent
    task_dir = root / "tasks"
    openenv_yaml = (root / "openenv.yaml").read_text(encoding="utf-8")

    assert "id: easy" in openenv_yaml
    assert "id: medium" in openenv_yaml
    assert "id: hard" in openenv_yaml

    easy = task_dir / "easy.yaml"
    medium = task_dir / "medium.yaml"
    hard = task_dir / "hard.yaml"

    assert easy.exists()
    assert medium.exists()
    assert hard.exists()


def test_each_task_produces_valid_episode_and_grader_score():
    for task_name in ["easy", "medium", "hard"]:
        env = CyberEnv(task=task_name)
        obs = env.reset()

        assert obs is not None
        assert isinstance(obs.alerts, list)
        assert isinstance(obs.risk_score, int)

        done = False
        steps = 0
        # Deterministic safe strategy: investigate then resolve first available alert.
        while not done and steps < 50:
            steps += 1
            if env.alerts:
                first = env.alerts[0]
                env.step(CyberAction(message=f"investigate {first}"))
                _, reward, done, _ = env.step(CyberAction(message=f"resolve {first}"))
            else:
                _, reward, done, _ = env.step(CyberAction(message="investigate phishing_email"))

            assert 0.0 <= reward <= 1.0

        assert done is True

        score = grade_state(env.state)
        assert 0.0 <= score <= 1.0


def test_task_loader_fallback_for_unknown_task():
    env = CyberEnv(task="unknown")
    obs = env.reset()

    assert obs is not None
    assert isinstance(obs.time_left, int)
    assert obs.time_left > 0
