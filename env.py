from pathlib import Path
from typing import Dict, List, Tuple

try:
    from openenv import Environment
except ImportError:
    from openenv.core import Environment

from models import CyberAction, CyberObservation, CyberState
from parser import parse_message_to_action


class CyberEnv(Environment):
    def __init__(self, task: str = "easy") -> None:
        super().__init__()
        self.task = task
        self._max_time_by_task: Dict[str, int] = {
            "easy": 10,
            "medium": 12,
            "hard": 14,
        }
        self._escalation_alerts: List[str] = [
            "suspicious_attachment",
            "brute_force_attempt",
            "privilege_escalation",
            "data_exfiltration",
            "service_disruption",
        ]
        self._generated_alert_idx = 0
        self._resolved_alerts = 0
        self._max_time = 10
        self._elapsed_steps = 0
        self._correct_actions = 0
        self._delay_penalty_total = 0.0
        self._initial_risk_score = 20
        self._decision_trace: List[str] = []
        self._noise_alert_name = "suspicious_dns_noise"
        self._noise_alert_spawned = False
        self._investigated_alerts: set[str] = set()
        self._risk_before_step = 20
        self._risk_after_step = 20
        self.alerts: List[str] = []
        self.risk_score = 20
        self.time_left = 10
        self.history: List[str] = []
        self._task_config = self._load_task_config(self.task)

    def _load_task_config(self, task_name: str) -> Dict[str, int]:
        default = {"max_steps": self._max_time_by_task.get(task_name, 10), "initial_risk_score": 20}
        task_file = Path(__file__).resolve().parent / "tasks" / f"{task_name}.yaml"

        if not task_file.exists():
            return default

        config: Dict[str, int] = dict(default)
        try:
            for raw_line in task_file.read_text(encoding="utf-8").splitlines():
                line = raw_line.strip()
                if not line or line.startswith("#"):
                    continue
                if line.startswith("max_steps:"):
                    value = line.split(":", 1)[1].strip()
                    config["max_steps"] = int(value)
                elif line.startswith("initial_risk_score:"):
                    value = line.split(":", 1)[1].strip()
                    config["initial_risk_score"] = int(value)
        except Exception:
            return default

        return config

    def reset(self) -> CyberObservation:
        self._task_config = self._load_task_config(self.task)
        self._max_time = int(self._task_config.get("max_steps", self._max_time_by_task.get(self.task, 10)))
        self.alerts = ["phishing_email", "failed_login"]
        self.risk_score = int(self._task_config.get("initial_risk_score", 20))
        self._initial_risk_score = self.risk_score
        self.time_left = self._max_time
        self.history = [f"reset:{self.task}"]
        self._generated_alert_idx = 0
        self._resolved_alerts = 0
        self._elapsed_steps = 0
        self._correct_actions = 0
        self._delay_penalty_total = 0.0
        self._decision_trace = ["Reset completed with deterministic baseline alerts."]
        self._noise_alert_spawned = False
        self._investigated_alerts = set()
        self._risk_before_step = self.risk_score
        self._risk_after_step = self.risk_score
        return self._observation()

    def step(self, action: CyberAction) -> Tuple[CyberObservation, float, bool, Dict[str, str]]:
        try:
            self._elapsed_steps += 1
            self._risk_before_step = self.risk_score
            message = getattr(action, "message", "")
            parsed = parse_message_to_action(message)
            self.history.append(f"action:{message}")

            if parsed.is_valid:
                if parsed.verb == "investigate":
                    self._handle_investigate(parsed.target)
                elif parsed.verb == "block":
                    self._handle_block(parsed.target)
                elif parsed.verb == "resolve":
                    self._handle_resolve(parsed.target)
                else:
                    self.history.append("invalid_action")
                    self._decision_trace.append("Unsupported action verb routed to invalid action handling.")
                    self._increase_risk_and_escalate(10)
            else:
                self.history.append("invalid_action")
                self._decision_trace.append("Invalid action format increased operational risk.")
                self._increase_risk_and_escalate(10)

            self._maybe_add_noise_alert()

            self.time_left = max(0, self.time_left - 1)
            self.risk_score = max(0, min(100, self.risk_score))
            self._risk_after_step = self.risk_score

            done = self.risk_score >= 90 or self.time_left == 0 or len(self.alerts) == 0
            reward = self._compute_reward(done)
            reward = max(0.0, min(1.0, reward))
            info = self._build_info(done)
            return self._observation(), reward, done, info
        except Exception as exc:
            self.history.append("step_exception")
            self._decision_trace.append("Step exception recovered with safe fallback transition.")
            self._increase_risk_and_escalate(5)
            self.time_left = max(0, self.time_left - 1)
            self.risk_score = max(0, min(100, self.risk_score))
            self._risk_after_step = self.risk_score
            done = self.risk_score >= 90 or self.time_left == 0 or len(self.alerts) == 0
            reward = max(0.0, min(1.0, self._compute_reward(done)))
            self.history.append(f"step_error:{type(exc).__name__}")
            info = self._build_info(done)
            info["error"] = type(exc).__name__
            return self._observation(), reward, done, info

    @property
    def state(self) -> CyberState:
        return CyberState(
            alerts=list(self.alerts),
            risk_score=self.risk_score,
            time_left=self.time_left,
            history=list(self.history),
        )

    def _observation(self) -> CyberObservation:
        return CyberObservation(
            alerts=list(self.alerts),
            risk_score=self.risk_score,
            time_left=self.time_left,
            history=list(self.history),
        )

    def _handle_investigate(self, target: str) -> None:
        if target in self.alerts:
            if target == self._noise_alert_name:
                self.risk_score -= 2
                self._decision_trace.append(
                    f"Investigated {target}; identified as low-confidence false positive with minor risk reduction."
                )
            else:
                self.risk_score -= 5
                self._decision_trace.append(f"Investigated {target}; confidence improved for follow-up containment.")
            self._correct_actions += 1
            self._investigated_alerts.add(target)
            self.history.append(f"investigated:{target}")
        else:
            self.history.append(f"bad_investigate:{target}")
            self._decision_trace.append(f"Investigation target {target} not found; escalation risk increased.")
            self._increase_risk_and_escalate(8)

    def _handle_block(self, target: str) -> None:
        if target in self.alerts:
            if target == self._noise_alert_name:
                self.risk_score += 2
                self.history.append(f"bad_block:{target}")
                self._decision_trace.append(
                    "Blocked false-positive noise alert; unnecessary containment increased operational risk."
                )
            else:
                self.risk_score -= 10
                self.alerts.remove(target)
                self._resolved_alerts += 1
                self._correct_actions += 1
                self.history.append(f"blocked:{target}")
                self._decision_trace.append(f"Blocked {target}; containment executed successfully.")
        elif target == "192.168.1.1":
            self.risk_score -= 3
            self._correct_actions += 1
            self.history.append("blocked:ioc")
            self._decision_trace.append("Blocked known IOC 192.168.1.1; reduced external attack surface.")
        else:
            self.history.append(f"bad_block:{target}")
            self._decision_trace.append(f"Block target {target} invalid; risk increased due to ineffective response.")
            self._increase_risk_and_escalate(10)

    def _handle_resolve(self, target: str) -> None:
        if target in self.alerts:
            if target == self._noise_alert_name:
                self.alerts.remove(target)
                self._resolved_alerts += 1
                self._correct_actions += 1
                self.risk_score -= 1
                self.history.append(f"resolved:{target}")
                self._decision_trace.append("Resolved false-positive noise alert to reduce analyst backlog.")
            else:
                if target not in self._investigated_alerts:
                    self._delay_penalty_total += 0.05
                    self._decision_trace.append(
                        f"Resolved {target} without prior investigation; applied small quality penalty."
                    )
                self.alerts.remove(target)
                self._resolved_alerts += 1
                self._correct_actions += 1
                self.risk_score -= 12
                self.history.append(f"resolved:{target}")
                self._decision_trace.append(f"Resolved {target}; incident impact reduced.")
        else:
            self.history.append(f"bad_resolve:{target}")
            self._decision_trace.append(f"Resolve target {target} not active; risk increased due to mis-prioritization.")
            self._increase_risk_and_escalate(12)

    def _increase_risk_and_escalate(self, delta: int) -> None:
        self.risk_score += delta
        self._generate_new_alert()

    def _generate_new_alert(self) -> None:
        if self._generated_alert_idx >= len(self._escalation_alerts):
            return

        candidate = self._escalation_alerts[self._generated_alert_idx]
        self._generated_alert_idx += 1

        if candidate not in self.alerts:
            self.alerts.append(candidate)
            self.history.append(f"new_alert:{candidate}")
            self._decision_trace.append(f"Escalation generated new alert {candidate} due to unresolved risk.")

    def _maybe_add_noise_alert(self) -> None:
        # Deterministic false-positive noise appears once under pressure in medium/hard tasks.
        if self._noise_alert_spawned:
            return
        if self.task not in {"medium", "hard"}:
            return
        if self._elapsed_steps >= 3 and self._noise_alert_name not in self.alerts:
            self.alerts.append(self._noise_alert_name)
            self._noise_alert_spawned = True
            self.history.append(f"new_alert:{self._noise_alert_name}")
            self._decision_trace.append(
                "Detected low-confidence noise alert; can be investigated and resolved as false positive."
            )

    def _compute_reward(self, done: bool) -> float:
        risk_component = (100 - self.risk_score) / 100.0
        initial_and_generated = 2 + self._generated_alert_idx
        unresolved_ratio = len(self.alerts) / float(max(1, initial_and_generated))
        resolution_component = 1.0 - min(1.0, unresolved_ratio)
        time_component = self.time_left / float(max(1, self._max_time))

        reward = (0.45 * risk_component) + (0.30 * resolution_component) + (0.25 * time_component)

        if done and len(self.alerts) == 0 and self._elapsed_steps <= max(1, self._max_time // 2):
            reward += 0.10

        reward -= min(0.20, self._delay_penalty_total)

        if self.risk_score >= 90:
            reward = min(reward, 0.1)
        if done and len(self.alerts) == 0:
            reward = max(reward, 0.95)

        return max(0.0, min(1.0, reward))

    def _build_info(self, done: bool) -> Dict[str, str]:
        risk_delta = self._risk_after_step - self._risk_before_step
        risk_direction = "decreased" if risk_delta < 0 else "increased" if risk_delta > 0 else "unchanged"
        latest_trace = self._decision_trace[-3:] if self._decision_trace else []

        summary = (
            f"risk {risk_direction} by {abs(risk_delta)}; "
            f"alerts_open={len(self.alerts)}; "
            f"correct_actions={self._correct_actions}; "
            f"done={done}"
        )

        return {
            "decision_trace": " | ".join(latest_trace) if latest_trace else "No decision trace available.",
            "risk_explanation": summary,
            "risk_before": str(self._risk_before_step),
            "risk_after": str(self._risk_after_step),
            "risk_change": str(risk_delta),
        }
