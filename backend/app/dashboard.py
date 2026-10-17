"""Dashboard API router — aggregates per-domain sub-routers."""
from fastapi import APIRouter

from .routers import bot, payments, sites, tariffs, user

router = APIRouter(prefix="/api", tags=["dashboard"])

router.include_router(sites.router)
router.include_router(user.router)
router.include_router(tariffs.router)
router.include_router(payments.router)
router.include_router(bot.router)
