from typing import Any

from models import CyberState


def clamp_score(x: float) -> float:
    if x <= 0:
        return 0.05
    if x >= 1:
        return 0.99
    return max(0.01, min(0.99, x))


def _compute_cyber_state_score(state: CyberState) -> float:
    resolved_count = 0
    generated_count = 0
    first_priority_event_index = -1

    for idx, event in enumerate(state.history):
        if event.startswith("resolved:") or event.startswith("blocked:"):
            resolved_count += 1
        if event.startswith("new_alert:"):
            generated_count += 1
        if first_priority_event_index < 0 and (
            event in {"resolved:failed_login", "blocked:failed_login", "blocked:ioc"}
        ):
            first_priority_event_index = idx

    total_alerts = max(1, 2 + generated_count)
    resolved_alerts_ratio = clamp_score(resolved_count / float(total_alerts))

    current_risk = max(0, min(100, state.risk_score))
    # Baseline initial risk is 20 in the environment design.
    risk_reduction_score = clamp_score((20.0 - current_risk + 80.0) / 80.0)

    if first_priority_event_index < 0:
        prioritization_score = 0.05
    else:
        prioritization_score = clamp_score(1.0 - (first_priority_event_index / 20.0))

    time_efficiency = clamp_score(state.time_left / 14.0)

    score = (
        (risk_reduction_score * 0.40)
        + (prioritization_score * 0.25)
        + (time_efficiency * 0.20)
        + (resolved_alerts_ratio * 0.15)
    )
    return clamp_score(score)


def compute_score(state) -> float:
    # Use existing logic (risk reduction, etc.) when a CyberState object is provided.
    if isinstance(state, CyberState):
        score = _compute_cyber_state_score(state)
        return clamp_score(float(score))

    if isinstance(state, dict):
        score = state.get("score", 0.5)
        try:
            return clamp_score(float(score))
        except (TypeError, ValueError):
            score = 0.05
            return clamp_score(float(score))

    score = 0.05
    return clamp_score(float(score))


def grade_easy(state):
    return float(clamp_score(compute_score(state)))


def grade_medium(state):
    return float(clamp_score(compute_score(state)))


def grade_hard(state):
    return float(clamp_score(compute_score(state)))


def grade_state(state: Any) -> float:
    # Backward-compatible entrypoint used by inference code.
    return float(clamp_score(compute_score(state)))
