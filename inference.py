import os
from typing import Optional

from openai import OpenAI

from env import CyberEnv
from grader import grade_state
from models import CyberAction, CyberObservation
from parser import parse_message_to_action


API_BASE_URL = os.getenv("API_BASE_URL", "https://gen.pollinations.ai")
MODEL_NAME = os.getenv("MODEL_NAME", "gemini-fast")
HF_TOKEN = os.getenv("HF_TOKEN", "dummy") or "dummy"

client = OpenAI(
    base_url=API_BASE_URL,
    api_key=HF_TOKEN,
)


def _coerce_valid_action(message: str, last_obs: CyberObservation, step: int) -> str:
    parsed = parse_message_to_action(message)
    if parsed.is_valid:
        return f"{parsed.verb} {parsed.target}"
    return fallback_logic(step, last_obs)


def fallback_logic(step: int, last_obs: CyberObservation) -> str:
    text = str(last_obs).lower()

    if "phishing" in text:
        return "investigate phishing_email"
    if "malware" in text:
        return "block 192.168.1.1"
    if "login" in text:
        return "resolve failed_login"

    if getattr(last_obs, "alerts", None):
        return f"investigate {last_obs.alerts[0]}"

    if step % 2 == 0:
        return "resolve phishing_email"
    return "investigate failed_login"


def get_model_message(
    step: int,
    last_obs: CyberObservation,
    last_reward: float,
    history: list[str],
) -> str:
    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {
                    "role": "system",
                    "content": "You are a cybersecurity SOC analyst. Respond with a single valid action.",
                },
                {
                    "role": "user",
                    "content": (
                        f"Observation: {last_obs}\n"
                        f"Reward: {last_reward}\n"
                        f"History: {history[-3:]}"
                    ),
                },
            ],
            temperature=0.2,
        )

        content: Optional[str] = None
        if response.choices:
            msg = response.choices[0].message
            content = msg.content if msg else None

        if not content:
            return fallback_logic(step, last_obs)

        line = content.strip().splitlines()[0].strip()
        if not line:
            return fallback_logic(step, last_obs)

        return _coerce_valid_action(line, last_obs, step)
    except Exception:
        return fallback_logic(step, last_obs)


def main() -> None:
    env = CyberEnv()

    print("[START]")
    try:
        observation = env.reset()
    except Exception:
        print("[END]")
        return

    done = False
    step_idx = 0
    step_logged = False
    reward = 0.0
    decision_history: list[str] = []

    while not done and step_idx < 50:
        step_idx += 1

        try:
            message = get_model_message(step_idx, observation, reward, decision_history)
        except Exception:
            message = fallback_logic(step_idx, observation)

        message = _coerce_valid_action(message, observation, step_idx)
        decision_history.append(message)

        action = CyberAction(message=message)

        try:
            step_result = env.step(action)
            if isinstance(step_result, tuple) and len(step_result) == 4:
                observation, reward, done, info = step_result
            else:
                info = {}
                observation, reward, done = step_result  # backward compatibility
        except Exception:
            try:
                fallback = CyberAction(message=fallback_logic(step_idx, observation))
                step_result = env.step(fallback)
                if isinstance(step_result, tuple) and len(step_result) == 4:
                    observation, reward, done, info = step_result
                else:
                    info = {}
                    observation, reward, done = step_result
            except Exception:
                info = {}
                done = True

        if not step_logged:
            print("[STEP]")
            step_logged = True

    try:
        _ = grade_state(env.state)
    except Exception:
        pass
    print("[END]")


if __name__ == "__main__":
    main()
