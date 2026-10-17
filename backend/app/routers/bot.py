"""Public Telegram-bot availability endpoint (for deep links)."""
from typing import Optional

from fastapi import APIRouter, Request
from pydantic import BaseModel

router = APIRouter(prefix="/bot", tags=["dashboard"])


class BotInfoResponse(BaseModel):
    enabled: bool
    username: Optional[str] = None


@router.get("/info", response_model=BotInfoResponse)
async def bot_info(request: Request) -> BotInfoResponse:
    """Public endpoint: Telegram bot availability + username for deep links.

    Used by the landing banner and dashboard to build
    https://t.me/<username>?start=<collection_name> links.
    """
    import os as _os

    bot = getattr(request.app.state, "telegram_bot", None)
    username = getattr(bot, "username", None) if bot is not None else None
    enabled = bot is not None or bool(_os.getenv("TG_BOT_TOKEN", "").strip())
    if not username:
        username = _os.getenv("TG_BOT_USERNAME") or None
    return BotInfoResponse(enabled=enabled, username=username)
