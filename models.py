from typing import List

try:
    from openenv import Action, Observation, State
except ImportError:
    from openenv.core import Action, Observation, State


class CyberAction(Action):
    message: str


class CyberObservation(Observation):
    alerts: List[str]
    risk_score: int
    time_left: int
    history: List[str]


class CyberState(State):
    alerts: List[str]
    risk_score: int
    time_left: int
    history: List[str]
