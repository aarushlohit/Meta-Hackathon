from env import CyberEnv
from models import CyberAction


def test_reset_returns_valid_observation():
    env = CyberEnv(task="easy")
    obs = env.reset()

    assert obs is not None
    assert isinstance(obs.alerts, list)
    assert isinstance(obs.risk_score, int)
    assert isinstance(obs.time_left, int)
    assert isinstance(obs.history, list)


def test_step_returns_4_tuple():
    env = CyberEnv(task="easy")
    env.reset()

    result = env.step(CyberAction(message="investigate phishing_email"))

    assert isinstance(result, tuple)
    assert len(result) == 4

    obs, reward, done, info = result
    assert obs is not None
    assert isinstance(reward, float)
    assert isinstance(done, bool)
    assert isinstance(info, dict)


def test_reward_bounds():
    env = CyberEnv(task="hard")
    env.reset()

    actions = [
        "invalid",
        "random text",
        "resolve not_existing",
        "block unknown",
        "investigate failed_login",
        "resolve failed_login",
        "investigate phishing_email",
        "resolve phishing_email",
    ]

    for action_message in actions:
        _, reward, _, _ = env.step(CyberAction(message=action_message))
        assert 0.0 <= reward <= 1.0


def test_done_conditions():
    # done via no alerts
    env_success = CyberEnv(task="easy")
    env_success.reset()
    _, _, done_1, _ = env_success.step(CyberAction(message="resolve phishing_email"))
    assert done_1 is False
    _, _, done_2, _ = env_success.step(CyberAction(message="resolve failed_login"))
    assert done_2 is True

    # done via risk >= 90
    env_risk = CyberEnv(task="easy")
    env_risk.reset()
    done = False
    for _ in range(12):
        _, _, done, _ = env_risk.step(CyberAction(message="resolve unknown_alert"))
        if done:
            break
    assert done is True
    assert env_risk.risk_score >= 90 or env_risk.time_left == 0 or len(env_risk.alerts) == 0

    # done via time_left == 0 eventually
    env_time = CyberEnv(task="easy")
    env_time.reset()
    done = False
    for _ in range(20):
        _, _, done, _ = env_time.step(CyberAction(message="investigate unknown_alert"))
        if done:
            break
    assert done is True


def test_state_consistency():
    env = CyberEnv(task="medium")
    obs = env.reset()

    state_1 = env.state
    assert state_1.alerts == obs.alerts
    assert state_1.risk_score == obs.risk_score
    assert state_1.time_left == obs.time_left

    env.step(CyberAction(message="investigate phishing_email"))
    state_2 = env.state

    assert isinstance(state_2.alerts, list)
    assert 0 <= state_2.risk_score <= 100
    assert state_2.time_left <= state_1.time_left
    assert len(state_2.history) >= len(state_1.history)
