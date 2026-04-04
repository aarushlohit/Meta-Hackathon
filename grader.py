from models import CyberState


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
    resolved_alerts_ratio = min(1.0, resolved_count / float(total_alerts))

    current_risk = max(0, min(100, state.risk_score))
    # Baseline initial risk is 20 in the environment design.
    risk_reduction_score = max(0.0, min(1.0, (20.0 - current_risk + 80.0) / 80.0))

    if first_priority_event_index < 0:
        prioritization_score = 0.0
    else:
        prioritization_score = max(0.0, min(1.0, 1.0 - (first_priority_event_index / 20.0)))

    time_efficiency = max(0.0, min(1.0, state.time_left / 14.0))

    score = (
        (risk_reduction_score * 0.40)
        + (prioritization_score * 0.25)
        + (time_efficiency * 0.20)
        + (resolved_alerts_ratio * 0.15)
    )

    return max(0.0, min(1.0, score))
