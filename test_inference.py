import io
import os
from contextlib import redirect_stdout

import inference


class FakeMessage:
    def __init__(self, content):
        self.content = content


class FakeChoice:
    def __init__(self, content):
        self.message = FakeMessage(content)


class FakeCompletion:
    def __init__(self, content):
        self.choices = [FakeChoice(content)]


class FakeCompletionsAPI:
    def __init__(self):
        self._count = 0

    def create(self, **kwargs):
        self._count += 1
        if self._count == 1:
            return FakeCompletion("investigate phishing_email")
        if self._count == 2:
            return FakeCompletion("resolve phishing_email")
        return FakeCompletion("resolve failed_login")


class FakeChatAPI:
    def __init__(self):
        self.completions = FakeCompletionsAPI()


class FakeOpenAI:
    def __init__(self, **kwargs):
        self.chat = FakeChatAPI()


def test_inference_loop_no_crash_and_log_format(monkeypatch):
    monkeypatch.setattr(inference, "OpenAI", FakeOpenAI)

    monkeypatch.setenv("API_BASE_URL", "http://fake.local")
    monkeypatch.setenv("MODEL_NAME", "fake-model")
    monkeypatch.setenv("HF_TOKEN", "fake-token")

    output = io.StringIO()
    with redirect_stdout(output):
        inference.main()

    text = output.getvalue().strip().splitlines()

    assert len(text) >= 3
    assert text[0] == "[START]"
    assert text[-1] == "[END]"

    step_lines = [line for line in text if line == "[STEP]"]
    assert len(step_lines) >= 1


def test_inference_handles_model_failure(monkeypatch):
    class FailingOpenAI:
        def __init__(self, **kwargs):
            class _Chat:
                class _Completions:
                    @staticmethod
                    def create(**kwargs):
                        raise RuntimeError("simulated API failure")

                completions = _Completions()

            self.chat = _Chat()

    monkeypatch.setattr(inference, "OpenAI", FailingOpenAI)
    monkeypatch.setenv("API_BASE_URL", "http://fake.local")
    monkeypatch.setenv("MODEL_NAME", "fake-model")
    monkeypatch.setenv("HF_TOKEN", "fake-token")

    output = io.StringIO()
    with redirect_stdout(output):
        inference.main()

    text = output.getvalue().strip().splitlines()
    assert text[0] == "[START]"
    assert text[-1] == "[END]"


def test_inference_collects_rewards_indirectly_from_env_steps(monkeypatch):
    rewards = []

    class TrackingEnv(inference.CyberEnv):
        def step(self, action):
            result = super().step(action)
            rewards.append(result[1])
            return result

    monkeypatch.setattr(inference, "CyberEnv", TrackingEnv)
    monkeypatch.setattr(inference, "OpenAI", FakeOpenAI)
    monkeypatch.setenv("API_BASE_URL", "http://fake.local")
    monkeypatch.setenv("MODEL_NAME", "fake-model")
    monkeypatch.setenv("HF_TOKEN", "fake-token")

    output = io.StringIO()
    with redirect_stdout(output):
        inference.main()

    assert len(rewards) >= 1
    assert all(0.0 <= r <= 1.0 for r in rewards)
