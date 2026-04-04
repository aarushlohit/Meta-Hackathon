import random
from typing import List, Tuple

from env import CyberEnv
from models import CyberAction
from parser import parse_message_to_action


class Color:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"
    RESET = "\033[0m"


def ctext(text: str, color: str) -> str:
    return f"{color}{text}{Color.RESET}"


def print_header() -> None:
    print("========================================")
    print("ADAPTIVE CYBER CRISIS ENV TEST RUNNER")
    print("=====================================")


def safe_parse_preview(action_message: str) -> str:
    try:
        parsed = parse_message_to_action(action_message)
        if parsed.is_valid:
            return f"parsed={parsed.verb}:{parsed.target}"
        return "parsed=invalid"
    except Exception as exc:
        return f"parsed_error={type(exc).__name__}"


def choose_scripted_action(env: CyberEnv) -> str:
    alerts = list(env.alerts)
    if not alerts:
        return "investigate phishing_email"

    # Multi-path valid behavior:
    # 1) Investigate first, then resolve.
    # 2) Sometimes contain quickly with block for active known alert.
    target = alerts[0]
    if target == "failed_login":
        return f"block {target}"

    investigated_tag = f"investigated:{target}"
    if investigated_tag in env.history:
        return f"resolve {target}"
    return f"investigate {target}"


def choose_bad_action(step: int) -> str:
    bad_actions = [
        "ignore everything",
        "resolve unknown_alert",
        "block nothing_here",
        "investigate ghost_alert",
        "bad command",
    ]
    return bad_actions[step % len(bad_actions)]


def choose_random_action(rng: random.Random) -> str:
    random_actions = [
        "",
        "???",
        "investigate",
        "resolve",
        "block",
        "DROP TABLE alerts",
        "investigate random_alert",
        "resolve random_alert",
        "block 10.10.10.10",
        "hello world",
    ]
    return rng.choice(random_actions)


def print_step_log(
    step_number: int,
    action: str,
    before_risk: int,
    after_risk: int,
    reward: float,
    alert_count: int,
    done: bool,
    parse_preview: str,
) -> None:
    if after_risk < before_risk:
        tone = Color.GREEN
    elif after_risk > before_risk:
        tone = Color.RED
    else:
        tone = Color.YELLOW

    print("---")
    print(f"STEP: {step_number}")
    print(f"ACTION: {action} ({parse_preview})")
    print(ctext(f"RISK: {before_risk} -> {after_risk}", tone))
    print(ctext(f"REWARD: {reward:.4f}", tone))
    print(f"ALERT COUNT: {alert_count}")
    print(f"DONE: {str(done).lower()}")
    print("------------------")


def print_state_snapshot(env: CyberEnv) -> None:
    print(ctext("STATE:", Color.CYAN))
    print(f"- risk_score: {env.risk_score}")
    print(f"- alerts: {list(env.alerts)}")
    print(f"- time_left: {env.time_left}")


def scenario_status(done: bool, env: CyberEnv) -> str:
    if done and len(env.alerts) == 0 and env.risk_score < 90:
        return "SUCCESS"
    return "FAILURE"


def run_scenario(name: str, mode: str, max_steps: int = 20, debug_state: bool = True) -> None:
    print()
    print(ctext(f"===== {name} =====", Color.BOLD))

    try:
        env = CyberEnv(task="hard" if mode != "scripted" else "medium")
    except Exception as exc:
        print(ctext(f"ENV INIT ERROR: {type(exc).__name__}: {exc}", Color.RED))
        return

    try:
        observation = env.reset()
        print(f"Initial alerts: {observation.alerts}")
        print(f"Initial risk: {observation.risk_score}")
        print(f"Initial time_left: {observation.time_left}")
    except Exception as exc:
        print(ctext(f"RESET ERROR: {type(exc).__name__}: {exc}", Color.RED))
        return

    rewards: List[float] = []
    done = False
    rng = random.Random(42)

    for step in range(1, max_steps + 1):
        if done:
            break

        try:
            if mode == "scripted":
                action_str = choose_scripted_action(env)
            elif mode == "bad":
                action_str = choose_bad_action(step)
            else:
                action_str = choose_random_action(rng)
        except Exception as exc:
            print(ctext(f"ACTION GENERATION ERROR: {type(exc).__name__}: {exc}", Color.RED))
            action_str = ""

        parse_preview = safe_parse_preview(action_str)

        before_risk = env.risk_score

        try:
            result = env.step(CyberAction(message=action_str))
        except Exception as exc:
            print(ctext(f"STEP ERROR: {type(exc).__name__}: {exc}", Color.RED))
            continue

        try:
            if isinstance(result, tuple) and len(result) == 4:
                _, reward, done, info = result
            else:
                print(ctext("WARNING: step() returned unexpected format", Color.YELLOW))
                continue
        except Exception as exc:
            print(ctext(f"UNPACK ERROR: {type(exc).__name__}: {exc}", Color.RED))
            continue

        rewards.append(reward)
        after_risk = env.risk_score

        print_step_log(
            step_number=step,
            action=action_str,
            before_risk=before_risk,
            after_risk=after_risk,
            reward=reward,
            alert_count=len(env.alerts),
            done=done,
            parse_preview=parse_preview,
        )

        if isinstance(info, dict):
            trace = info.get("decision_trace", "")
            risk_explanation = info.get("risk_explanation", "")
            if trace:
                print(ctext(f"TRACE: {trace}", Color.CYAN))
            if risk_explanation:
                print(ctext(f"EXPLAIN: {risk_explanation}", Color.CYAN))

        if debug_state:
            print_state_snapshot(env)

    avg_reward = sum(rewards) / len(rewards) if rewards else 0.0
    status = scenario_status(done, env)

    print("========== SCENARIO RESULT ==========")
    print(f"Total Steps: {len(rewards)}")
    print(f"Final Risk: {env.risk_score}")
    print(f"Final Reward Avg: {avg_reward:.4f}")
    print(f"Status: {status}")
    print("=========================")


def main() -> None:
    print_header()

    # Scenario 1: Correct behavior (ideal path)
    run_scenario(
        name="Scenario 1: Correct behavior (ideal path)",
        mode="scripted",
        max_steps=20,
        debug_state=True,
    )

    # Scenario 2: Wrong actions (trigger escalation)
    run_scenario(
        name="Scenario 2: Wrong actions (trigger escalation)",
        mode="bad",
        max_steps=20,
        debug_state=True,
    )

    # Scenario 3: Random/invalid actions (robustness test)
    run_scenario(
        name="Scenario 3: Random/invalid actions (robustness test)",
        mode="random",
        max_steps=20,
        debug_state=True,
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(ctext(f"FATAL RUNNER ERROR: {type(exc).__name__}: {exc}", Color.RED))
