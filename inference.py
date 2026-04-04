import os
from typing import Optional

from openai import OpenAI

from env import CyberEnv
from grader import grade_state
from models import CyberAction, CyberObservation


def _build_prompt(observation: CyberObservation) -> str:
    return (
        "You are a cybersecurity analyst. Return exactly one command using one of: "
        "investigate <alert>, block <target>, resolve <alert>. "
        f"alerts={observation.alerts}, risk_score={observation.risk_score}, "
        f"time_left={observation.time_left}, history_tail={observation.history[-3:]}"
    )


def _fallback_action(observation: CyberObservation) -> str:
    if observation.alerts:
        return f"investigate {observation.alerts[0]}"
    return "resolve phishing_email"


def _ask_model(client: OpenAI, model_name: str, observation: CyberObservation) -> str:
    prompt = _build_prompt(observation)
    completion = client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": "Return one valid command only."},
            {"role": "user", "content": prompt},
        ],
        temperature=0,
    )

    content: Optional[str] = None
    if completion.choices:
        message = completion.choices[0].message
        content = message.content if message else None

    if not content:
        return _fallback_action(observation)

    first_line = content.strip().splitlines()[0].strip()
    return first_line if first_line else _fallback_action(observation)


def main() -> None:
    api_base_url = os.getenv("API_BASE_URL", "https://api-inference.huggingface.co/v1")
    model_name = os.getenv("MODEL_NAME", "meta-llama/Llama-3.1-8B-Instruct")
    hf_token = os.getenv("HF_TOKEN", "")

    client = OpenAI(base_url=api_base_url, api_key=hf_token if hf_token else "hf_dummy")

    env = CyberEnv()

    print("[START]")
    try:
        observation = env.reset()
    except Exception:
        print("[END]")
        return

    done = False
    step_idx = 0

    while not done and step_idx < 50:
        step_idx += 1

        try:
            message = _ask_model(client, model_name, observation)
        except Exception:
            message = _fallback_action(observation)

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
                fallback = CyberAction(message=_fallback_action(observation))
                step_result = env.step(fallback)
                if isinstance(step_result, tuple) and len(step_result) == 4:
                    observation, reward, done, info = step_result
                else:
                    info = {}
                    observation, reward, done = step_result
            except Exception:
                info = {}
                done = True

        try:
            risk_change = info.get("risk_change", "0") if isinstance(info, dict) else "0"
        except Exception:
            risk_change = "0"

        print(
            f"[STEP] t={step_idx} risk={observation.risk_score} "
            f"change={risk_change} alerts={len(observation.alerts)}"
        )

    try:
        _ = grade_state(env.state)
    except Exception:
        pass
    print("[END]")


if __name__ == "__main__":
    main()
