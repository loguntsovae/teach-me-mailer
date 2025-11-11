import os
from typing import Optional

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr

load_dotenv()  # загружает переменные из .env


class TriggerRequest(BaseModel):
    to: EmailStr
    subject: str
    html: Optional[str] = None
    text: Optional[str] = None


app = FastAPI(title="Mailer client service", version="0.1.0")


def get_config():
    return {
        "mailer_send_url": os.getenv("MAILER_SEND_URL", "http://localhost:8088/api/v1/send"),
        "api_key": os.getenv("MAILER_API_KEY"),
        "timeout": float(os.getenv("MAILER_TIMEOUT", "5")),
    }


@app.post("/trigger", status_code=202)
async def trigger_send(req: TriggerRequest):
    cfg = get_config()
    if not cfg["api_key"]:
        raise HTTPException(status_code=500, detail="MAILER_API_KEY is not configured")

    payload = req.dict()
    headers = {"X-API-Key": cfg["api_key"], "Content-Type": "application/json"}

    async with httpx.AsyncClient(timeout=cfg["timeout"]) as client:
        try:
            r = await client.post(cfg["mailer_send_url"], json=payload, headers=headers)
        except httpx.RequestError as exc:
            raise HTTPException(status_code=502, detail=f"Failed to reach mailer: {exc}")

    if r.status_code >= 400:
        raise HTTPException(status_code=r.status_code, detail=r.text)

    return r.json()


@app.get("/", include_in_schema=False)
async def root():
    cfg = get_config()
    return {"client": "mailer-client", "mailer_send_url": cfg["mailer_send_url"]}
