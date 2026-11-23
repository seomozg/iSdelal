"""Entry point: `python -m app.docbot` (no HTTP server, long polling only)."""
import asyncio
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from ..database import init_db
from .bot import DocBot


async def _run(token: str) -> None:
    await init_db()
    bot = DocBot(token)
    await bot.run()


def main() -> None:
    # Local convenience: backend/.env then backend/.env.docbot (overrides the token).
    # In Docker env comes from compose env_file — load_dotenv won't override it.
    base = Path(__file__).resolve().parents[2]  # .../backend
    load_dotenv(base / ".env")
    load_dotenv(base / ".env.docbot")

    token = os.getenv("TG_BOT_TOKEN", "").strip()
    if not token:
        print(
            "TG_BOT_TOKEN is not set — add it to backend/.env.docbot "
            "(or export it before running).",
            file=sys.stderr,
        )
        sys.exit(1)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    logging.getLogger("docbot").info("Document bot starting…")

    try:
        asyncio.run(_run(token))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
