"""FastAPI app entrypoint: app factory, middleware, mounts, lifespan, health."""
import asyncio
import logging
import os
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select

from .dashboard import router as dashboard_router
from .database import async_session_factory, init_db
from .models import Tariff
from .routers import auth, chat, ingest

# Production root path support (set to /iSdelal on server)
ROOT_PATH = os.getenv("ROOT_PATH", "")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: init DB, seed tariffs, start Telegram bot (if TG_BOT_TOKEN set)."""
    await init_db()
    await seed_tariffs()

    tg_task: Optional[asyncio.Task] = None
    tg_token = os.getenv("TG_BOT_TOKEN", "").strip()
    if tg_token:
        from .telegram_bot import TelegramBot
        tg_logger = logging.getLogger("telegram_bot")
        if not tg_logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(
                logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
            )
            tg_logger.addHandler(handler)
            tg_logger.setLevel(logging.INFO)
        bot = TelegramBot(tg_token)
        app.state.telegram_bot = bot
        tg_task = asyncio.create_task(bot.run())
        tg_task.add_done_callback(_log_tg_task_done)
        logging.getLogger("telegram_bot").info("Telegram bot task scheduled")
    else:
        logging.getLogger("telegram_bot").info("TG_BOT_TOKEN not set — Telegram bot disabled")

    try:
        yield
    finally:
        if tg_task is not None:
            tg_task.cancel()
            try:
                await tg_task
            except asyncio.CancelledError:
                pass
            except Exception:
                logging.getLogger("telegram_bot").exception("telegram bot task shutdown error")


def _log_tg_task_done(task: asyncio.Task) -> None:
    if task.cancelled():
        return
    exc = task.exception()
    if exc is not None:
        logging.getLogger("telegram_bot").error("telegram bot task failed: %s", exc)


async def seed_tariffs():
    """Ensure default tariffs exist in the database."""
    async with async_session_factory() as session:
        try:
            result = await session.execute(select(Tariff))
            existing_names = {t.name for t in result.scalars().all()}

            defaults = [
                Tariff(name="free", pages_limit=10, requests_limit=100, price_rub_month=0,
                       description="First 10 pages and 100 requests free"),
                Tariff(name="tariff_100", pages_limit=100, requests_limit=-1, price_rub_month=1000,
                       description="100 pages, unlimited requests"),
                Tariff(name="tariff_500", pages_limit=500, requests_limit=-1, price_rub_month=5000,
                       description="500 pages, unlimited requests"),
                Tariff(name="tariff_1000", pages_limit=1000, requests_limit=-1, price_rub_month=10000,
                       description="1000 pages, unlimited requests"),
            ]

            added = False
            for t in defaults:
                if t.name not in existing_names:
                    session.add(t)
                    added = True

            if added:
                await session.commit()
                print("Default tariffs seeded.")
        except Exception as e:
            await session.rollback()
            print(f"Warning: Could not seed tariffs: {e}")


app = FastAPI(root_path=ROOT_PATH, lifespan=lifespan)

# CORS middleware
allowed_origins = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:3000,http://localhost:8080,http://localhost:8000,http://localhost:4173,http://localhost:4174",
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if os.getenv("ALLOW_ALL_ORIGINS", "false").lower() == "true" else allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

# Static files (chat widget served by the backend)
app.mount("/widget", StaticFiles(directory="/app/widget"), name="widget")

# Routers
app.include_router(dashboard_router)
app.include_router(auth.router)
app.include_router(ingest.router)
app.include_router(chat.router)


@app.get('/health')
@app.head('/health')
async def health():
    return {'status': 'ok'}
