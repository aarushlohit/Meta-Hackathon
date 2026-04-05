---
sdk: docker
app_port: 7860
---

# Adaptive Cyber Crisis Environment

A deterministic, OpenEnv-style cybersecurity simulation where an agent performs SOC triage and containment actions under time pressure.

The environment is designed for reliable benchmarking: transitions are deterministic, escalation behavior is explicit, and rewards are bounded to `[0.0, 1.0]`.

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Project Structure](#project-structure)
- [Environment Model](#environment-model)
- [Action Contract](#action-contract)
- [Reward and Termination](#reward-and-termination)
- [HTTP API](#http-api)
- [Quickstart](#quickstart)
- [Inference Runner](#inference-runner)
- [Docker](#docker)
- [Hugging Face Spaces Deployment](#hugging-face-spaces-deployment)
- [Configuration](#configuration)
- [Scoring](#scoring)
- [Troubleshooting](#troubleshooting)

## Overview

`CyberEnv` simulates an incident queue with evolving risk:

- Baseline alerts begin as `phishing_email` and `failed_login`.
- The agent submits plain-text actions (`investigate`, `block`, `resolve`).
- Invalid or poor actions increase risk and can trigger deterministic escalation alerts.
- The objective is to reduce risk and clear alerts before failure conditions are met.

## Key Features

- Deterministic step logic suitable for evaluation and reproducibility.
- Task presets (`easy`, `medium`, `hard`) loaded from YAML.
- Explicit decision trace and risk-change metadata in `info`.
- FastAPI service with `/reset` and `/step` endpoints.
- Optional model-driven inference loop with robust fallback behavior.

## Project Structure

```
.
|- env.py              # Core simulation logic (CyberEnv)
|- models.py           # Action / observation / state schemas
|- parser.py           # Command parser and compatibility mappings
|- grader.py           # Final state scoring function
|- inference.py        # Optional model-in-the-loop rollout script
|- server/app.py       # FastAPI application
|- tasks/              # Difficulty presets
|  |- easy.yaml
|  |- medium.yaml
|  \- hard.yaml
|- Dockerfile
|- requirements.txt
\- README.md
```

## Environment Model

### Observation Schema

Each step returns `CyberObservation`:

- `alerts: list[str]`
- `risk_score: int`
- `time_left: int`
- `history: list[str]`

### Default Reset State

For all tasks, reset starts from:

- `alerts = ["phishing_email", "failed_login"]`
- `initial_risk_score = 20`
- `time_left = max_steps` where:
   - `easy = 10`
   - `medium = 12`
   - `hard = 14`

## Action Contract

`CyberAction` uses a single text field: `message`.

Supported commands:

- `investigate <alert>`
- `block <target>`
- `resolve <alert>`

Compatibility alias:

- `block_ip <target>` -> interpreted as `block <target>`

Any malformed or unsupported message is treated as invalid and increases risk.

## Reward and Termination

### Reward

Per-step reward is computed from:

- risk reduction
- resolution progress
- time efficiency
- optional completion bonus
- delay penalties for resolving certain alerts without investigation

Output reward is always clamped to `[0.0, 1.0]`.

### Episode Ends When

- `risk_score >= 90`, or
- `time_left == 0`, or
- all alerts are resolved.

## HTTP API

Base URL (local): `http://localhost:7860`

### `GET /`

Service metadata and available endpoints.

### `GET /health`

Simple liveness probe.

### `POST /reset`

Request body:

```json
{
   "task": "easy"
}
```

Response shape:

```json
{
   "observation": {
      "alerts": ["phishing_email", "failed_login"],
      "risk_score": 20,
      "time_left": 10,
      "history": ["reset:easy"]
   },
   "reward": 0.0,
   "done": false,
   "info": {}
}
```

### `POST /step`

Request body:

```json
{
   "message": "investigate phishing_email"
}
```

Response includes updated `observation`, bounded `reward`, `done`, and diagnostic `info` fields (`decision_trace`, `risk_explanation`, etc.).

### cURL Example

```bash
curl -s -X POST http://localhost:7860/reset \
   -H "Content-Type: application/json" \
   -d '{"task":"medium"}' | jq

curl -s -X POST http://localhost:7860/step \
   -H "Content-Type: application/json" \
   -d '{"message":"resolve failed_login"}' | jq
```

## Quickstart

### 1) Install Dependencies

```bash
python -m venv env
source env/bin/activate
pip install -r requirements.txt
```

### 2) Start API Server

```bash
uvicorn server.app:app --host 0.0.0.0 --port 7860
```

### 3) Validate Service

```bash
curl -s http://localhost:7860/health
```

## Inference Runner

Run the model-assisted rollout script:

```bash
python inference.py
```

`inference.py`:

- queries an OpenAI-compatible endpoint,
- coerces responses into valid environment actions,
- falls back deterministically when model output is invalid/unavailable,
- runs until done or step cap.

## Docker

Build:

```bash
docker build -t adaptive-cyber-env .
```

Run:

```bash
docker run --rm -p 7860:7860 adaptive-cyber-env
```

## Hugging Face Spaces Deployment

This repository is ready for Docker-based Spaces deployment.

- Use **Docker** SDK.
- Keep `Dockerfile` at repository root.
- Expose port `7860`.
- Configure optional runtime environment variables (see below).

## Configuration

Environment variables used by `inference.py`:

- `API_BASE_URL` (default: `https://gen.pollinations.ai`)
- `MODEL_NAME` (default: `gemini-fast`)
- `HF_TOKEN` (default fallback: `dummy`)

Example:

```bash
export API_BASE_URL="https://gen.pollinations.ai"
export MODEL_NAME="gemini-fast"
export HF_TOKEN="<your_token>"
python inference.py
```

## Scoring

`grader.py::grade_state` produces a final score in `[0.0, 1.0]` based on:

- risk reduction,
- prioritization timing,
- time remaining,
- fraction of alerts resolved.

## Troubleshooting

- `ModuleNotFoundError` for project deps:
   - Ensure virtual environment is activated and `pip install -r requirements.txt` completed.
- API requests fail locally:
   - Confirm server is running on port `7860`.
- Inference returns weak or inconsistent actions:
   - Verify `API_BASE_URL`, `MODEL_NAME`, and token validity.
- Unexpected invalid actions:
   - Ensure actions strictly follow `verb + target`, for example `investigate phishing_email`.
