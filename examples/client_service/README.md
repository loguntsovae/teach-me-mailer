# Minimal Mailer Client Service

This folder contains a very small example FastAPI application that demonstrates how to call the mailer service in this repository.

Purpose
- Show how an external service can call the mailer endpoint at `/api/v1/send` using an API key.

Files
- `app.py` – FastAPI application exposing `POST /trigger` which forwards the request to the mailer service.
- `requirements.txt` – Python dependencies for the example.
- `.env.example` – Example environment variables.

Quick start
1. Copy `.env.example` to `.env` and set `MAILER_API_KEY` to a valid API key from this repo (or create one via admin endpoints).
2. Install dependencies:

```
pip install -r examples/client_service/requirements.txt
```

3. Run the client:

```
uvicorn examples.client_service.app:app --reload --port 9000
```

4. Trigger a send (example using curl):

```
curl -X POST "http://localhost:9000/trigger" -H "Content-Type: application/json" -d '{"to":"user@example.com","subject":"Hello","text":"Hi"}'
```

The client will forward the request to the configured `MAILER_SEND_URL` with the header `X-API-Key` set from `MAILER_API_KEY`.
