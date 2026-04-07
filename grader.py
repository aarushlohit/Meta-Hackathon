from typing import Dict, Iterable, Tuple

from models import CyberState


TASK_IDS: Tuple[str, str, str] = ("easy", "medium", "hard")


def clamp_score(x: float) -> float:
    return max(0.01, min(0.99, x))


def _normalize_score(raw_score: float) -> float:
    score = raw_score
    if score == 0.0:
        score = 0.05
    if score == 1.0:
        score = 0.99
    return clamp_score(score)


def grade_state(state: CyberState) -> float:
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
    resolved_alerts_ratio = _normalize_score(resolved_count / float(total_alerts))

    current_risk = max(0, min(100, state.risk_score))
    # Baseline initial risk is 20 in the environment design.
    risk_reduction_score = _normalize_score((20.0 - current_risk + 80.0) / 80.0)

    if first_priority_event_index < 0:
        prioritization_score = 0.05
    else:
        prioritization_score = _normalize_score(1.0 - (first_priority_event_index / 20.0))

    time_efficiency = _normalize_score(state.time_left / 14.0)

    task_score = (
        (risk_reduction_score * 0.40)
        + (prioritization_score * 0.25)
        + (time_efficiency * 0.20)
        + (resolved_alerts_ratio * 0.15)
    )
    task_score = _normalize_score(task_score)
    return task_score


def grade_tasks(states_by_task: Dict[str, CyberState]) -> Dict[str, float]:
    task_scores: Dict[str, float] = {}

    for task in TASK_IDS:
        state = states_by_task.get(task)
        if state is None:
            task_score = 0.05
        else:
            task_score = grade_state(state)
        task_scores[task] = _normalize_score(task_score)

    return task_scores


def aggregate_final_score(task_scores: Iterable[float]) -> float:
    scores = [_normalize_score(score) for score in task_scores]

    while len(scores) < 3:
        scores.append(0.05)

    final_score = sum(scores) / len(scores)
    final_score = _normalize_score(final_score)
    return final_score


def validate_task_scores(task_scores: Dict[str, float]) -> None:
    if len(task_scores) < 3:
        raise ValueError("Not enough tasks with graders")

    if any(not (0.0 < score < 1.0) for score in task_scores.values()):
        raise ValueError("Task scores must be strictly between (0, 1)")
