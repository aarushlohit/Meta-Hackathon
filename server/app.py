from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn

from env import CyberEnv
from models import CyberAction


env = CyberEnv()
app = FastAPI(title="Adaptive Cyber Crisis Environment")


@app.get("/")
def root() -> dict:
	return {
		"status": "running",
		"service": "Meta Hackathon OpenEnv API",
		"version": "1.0",
		"endpoints": ["/reset", "/step"],
	}


@app.get("/health")
def health() -> dict:
	return {
		"ok": True,
		"uptime": "alive",
	}


class ResetRequest(BaseModel):
	task: str = "easy"


class StepRequest(BaseModel):
	message: str = ""


@app.post("/reset")
def reset(request: ResetRequest | None = None) -> dict:
	try:
		task_name = request.task if request and request.task else "easy"
		env.task = task_name
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


def main() -> None:
	uvicorn.run("server.app:app", host="0.0.0.0", port=7860)


if __name__ == "__main__":
	main()
