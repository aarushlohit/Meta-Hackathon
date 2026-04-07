from fastapi import FastAPI, Request
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
	}


class ResetRequest(BaseModel):
	task: str = "easy"


class StepRequest(BaseModel):
	message: str = ""


@app.post("/reset")
async def reset(request: Request) -> dict:
	try:
		body = await request.json()
		task = body.get("task", "easy")

		env.task = task
		obs = env.reset()

		return {
			"observation": obs,
			"reward": 0.0,
			"done": False,
			"info": {},
		}
	except Exception:
		obs = env.reset()
		return {
			"observation": obs,
			"reward": 0.0,
			"done": False,
			"info": {},
		}


@app.post("/step")
async def step(request: Request) -> dict:
	try:
		body = await request.json()

		# CRITICAL FIX: map "action" -> "message"
		action_text = body.get("action", "")

		# fallback safety
		if not isinstance(action_text, str):
			action_text = ""

		action = CyberAction(message=action_text)

		obs, reward, done, info = env.step(action)

		return {
			"observation": obs,
			"reward": reward,
			"done": done,
			"info": info,
		}
	except Exception as exc:
		return {
			"observation": {},
			"reward": 0.05,
			"done": False,
			"info": {"error": str(exc)},
		}


def main() -> None:
	uvicorn.run("server.app:app", host="0.0.0.0", port=7860)


if __name__ == "__main__":
	main()
