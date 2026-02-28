"""Webhook routes for receiving messages from Evolution API."""

from fastapi import APIRouter, Request
from pydantic import BaseModel

router = APIRouter()


class WebhookResponse(BaseModel):
    status: str
    message: str | None = None


@router.post("/webhook/{event}")
async def receive_message(event: str, request: Request):
    body = await request.json()
    print("EVENT:", event)
    print("BODY:", body)
    return {"status": "ok"}
