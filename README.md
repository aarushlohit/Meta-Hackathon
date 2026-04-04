# Adaptive Cyber Crisis Environment

A deterministic OpenEnv-compatible cybersecurity environment where an agent handles alerts under escalating risk.

## Environment Description

The agent acts as a SOC analyst processing alerts with a limited timeline. Incorrect actions increase risk and generate deterministic new alerts.

## Actions

`CyberAction` uses a single text field:

- `investigate <alert>`
- `block <target>`
- `resolve <alert>`

Also supported by parser compatibility:

- `block_ip <target>` (mapped to `block <target>`)

Any other message is treated as invalid.

## Observation Format

`CyberObservation` fields:

- `alerts: list[str]`
- `risk_score: int`
- `time_left: int`
- `history: list[str]`

## Core Rules

- Initial reset state:
  - alerts: `["phishing_email", "failed_login"]`
  - risk_score: `20`
  - time_left: task-dependent (`10`, `12`, `14`)
- Wrong actions raise risk and create deterministic new alerts.
- Reward is always clamped to `[0.0, 1.0]`.
- Episode ends when:
  - `risk_score >= 90`, or
  - `time_left == 0`, or
  - `alerts` is empty.

## Run Locally

1. Install dependencies:

   `pip install -r requirements.txt`

2. Run API server:

   `uvicorn server.app:app --host 0.0.0.0 --port 7860`

3. Run inference loop:

   `python inference.py`

## API Expectations

OpenEnv FastAPI integration is created with:

- `create_fastapi_app(env, CyberAction, CyberObservation)`

This serves reset/step routes through OpenEnv conventions and should return HTTP 200 on reset when the server is running.

## Docker

Build:

`docker build -t adaptive-cyber-env .`

Run:

`docker run --rm -p 7860:7860 adaptive-cyber-env`

## HuggingFace Spaces Deployment

- Use Docker Space type.
- Include this repository with `Dockerfile` at root.
- Expose port `7860`.
- Set optional environment variables for inference:
  - `API_BASE_URL`
  - `MODEL_NAME`
  - `HF_TOKEN`
