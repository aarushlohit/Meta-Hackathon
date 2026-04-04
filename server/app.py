from fastapi import FastAPI
from pydantic import BaseModel

from env import CyberEnv
from models import CyberAction


env = CyberEnv()
app = FastAPI(title="Adaptive Cyber Crisis Environment")


class ResetRequest(BaseModel):
	task: str = "easy"


class StepRequest(BaseModel):
	message: str = ""


@app.post("/reset")
def reset(request: ResetRequest) -> dict:
	try:
		env.task = request.task if request.task else "easy"
		observation = env.reset()
		return {
			"observation": observation.model_dump(),
			"reward": 0.0,
			"done": False,
			"info": {},
		}
	except Exception as exc:
		return {
			"observation": {
				"alerts": ["phishing_email", "failed_login"],
				"risk_score": 20,
				"time_left": 10,
				"history": ["reset_fallback"],
			},
			"reward": 0.0,
			"done": False,
			"info": {"error": str(exc)},
		}


@app.post("/step")
def step(request: StepRequest) -> dict:
	try:
		action = CyberAction(message=request.message)
		observation, reward, done, info = env.step(action)
		return {
			"observation": observation.model_dump(),
			"reward": max(0.0, min(1.0, float(reward))),
			"done": bool(done),
			"info": info if isinstance(info, dict) else {},
		}
	except Exception as exc:
		return {
			"observation": env.state.model_dump(),
			"reward": 0.0,
			"done": True,
			"info": {"error": str(exc)},
		}
