from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime

from .database import get_session
from .models import UsageStats, Site, Subscription, Tariff, User


async def record_deepseek_usage(
    session: AsyncSession,
    user_id: int,
    site_id: int | None,
    tokens: int,
) -> None:
    """Record DeepSeek token usage for a chat request."""
    stat = UsageStats(
        user_id=user_id,
        site_id=site_id,
        deepseek_tokens=tokens,
        chat_requests=1,
        date=datetime.utcnow(),
    )
    session.add(stat)
    await session.flush()


async def record_jina_usage(
    session: AsyncSession,
    user_id: int,
    site_id: int | None,
    tokens: int,
    pages: int = 1,
) -> None:
    """Record Jina token usage for an embedding request."""
    stat = UsageStats(
        user_id=user_id,
        site_id=site_id,
        jina_tokens=tokens,
        ingest_pages=pages,
        date=datetime.utcnow(),
    )
    session.add(stat)
    await session.flush()


async def get_user_limits(session: AsyncSession, user_id: int) -> tuple[Tariff | None, Subscription | None]:
    """Get user's current tariff and subscription."""
    stmt = (
        select(Subscription)
        .where(Subscription.user_id == user_id, Subscription.active == True)
    )
    result = await session.execute(stmt)
    subscription = result.scalar_one_or_none()

    if subscription:
        stmt = select(Tariff).where(Tariff.id == subscription.tariff_id)
        result = await session.execute(stmt)
        tariff = result.scalar_one_or_none()
        return tariff, subscription

    return None, None


async def get_total_usage(session: AsyncSession, user_id: int) -> dict:
    """Get aggregated usage stats for a user."""
    stmt = (
        select(
            func.coalesce(func.sum(UsageStats.deepseek_tokens), 0).label("deepseek"),
            func.coalesce(func.sum(UsageStats.jina_tokens), 0).label("jina"),
            func.coalesce(func.sum(UsageStats.chat_requests), 0).label("chats"),
            func.coalesce(func.sum(UsageStats.ingest_pages), 0).label("pages"),
        )
        .where(UsageStats.user_id == user_id)
    )
    result = await session.execute(stmt)
    row = result.one()
    return {
        "deepseek_tokens": row.deepseek,
        "jina_tokens": row.jina,
        "chat_requests": row.chats,
        "ingest_pages": row.pages,
    }


async def get_site_usage(session: AsyncSession, site_id: int) -> dict:
    """Get aggregated usage stats for a specific site."""
    stmt = (
        select(
            func.coalesce(func.sum(UsageStats.deepseek_tokens), 0).label("deepseek"),
            func.coalesce(func.sum(UsageStats.jina_tokens), 0).label("jina"),
            func.coalesce(func.sum(UsageStats.chat_requests), 0).label("chats"),
            func.coalesce(func.sum(UsageStats.ingest_pages), 0).label("pages"),
        )
        .where(UsageStats.site_id == site_id)
    )
    result = await session.execute(stmt)
    row = result.one()
    return {
        "deepseek_tokens": row.deepseek,
        "jina_tokens": row.jina,
        "chat_requests": row.chats,
        "ingest_pages": row.pages,
    }


async def check_chat_quota(
    user: User,
    session: AsyncSession,
) -> None:
    """Check if user can make a chat request. Raises HTTPException if quota exceeded."""
    tariff, subscription = await get_user_limits(session, user.id)

    if tariff and tariff.requests_limit >= 0:
        usage = await get_total_usage(session, user.id)
        current_requests = usage["chat_requests"]

        if current_requests >= tariff.requests_limit:
            raise HTTPException(
                status_code=402,
                detail=f"Chat request limit reached ({current_requests}/{tariff.requests_limit}). Upgrade your tariff to continue.",
            )


async def check_ingest_quota(
    user: User,
    session: AsyncSession,
    new_pages: int = 1,
) -> None:
    """Check if user can index more pages. Raises HTTPException if quota exceeded."""
    tariff, subscription = await get_user_limits(session, user.id)

    if tariff:
        usage = await get_total_usage(session, user.id)
        current_pages = usage["ingest_pages"]

        if current_pages + new_pages > tariff.pages_limit:
            raise HTTPException(
                status_code=402,
                detail=f"Pages limit reached ({current_pages}/{tariff.pages_limit}). Upgrade your tariff to add more pages.",
            )