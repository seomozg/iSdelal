from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime
from typing import List

from .database import get_session
from .models import User, Site, UsageStats, Subscription, Tariff, Payment
from .auth import get_current_user
from .schemas import (
    SiteCreate, SiteResponse, WidgetConfigUpdate,
    UserStatsResponse, TariffResponse, SubscriptionResponse,
    PaymentResponse, UserResponse,
)
from .tracking import get_site_usage, get_total_usage, get_user_limits

router = APIRouter(prefix="/api", tags=["dashboard"])


# ===================== User =====================

@router.get("/user/me", response_model=UserResponse)
async def get_me(user: User = Depends(get_current_user)):
    return user


# ===================== Sites =====================

@router.get("/sites", response_model=List[SiteResponse])
async def list_sites(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    stmt = select(Site).where(Site.user_id == user.id).order_by(Site.created_at.desc())
    result = await session.execute(stmt)
    sites = result.scalars().all()

    response = []
    for site in sites:
        usage = await get_site_usage(session, site.id)
        response.append(SiteResponse(
            id=site.id,
            user_id=site.user_id,
            collection_name=site.collection_name,
            url=site.url,
            widget_config=site.widget_config or {},
            pages_indexed=site.pages_indexed,
            created_at=site.created_at,
            deepseek_tokens=usage["deepseek_tokens"],
            jina_tokens=usage["jina_tokens"],
            chat_requests=usage["chat_requests"],
        ))

    return response


@router.post("/sites", response_model=SiteResponse)
async def create_site(
    site_data: SiteCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    from urllib.parse import urlparse

    # Generate collection name from domain
    parsed = urlparse(site_data.url if "://" in site_data.url else f"https://{site_data.url}")
    domain = parsed.hostname.replace("www.", "") if parsed.hostname else site_data.url
    collection_name = domain.replace(".", "_").replace("-", "_")

    # Check for duplicates
    stmt = select(Site).where(
        Site.user_id == user.id,
        Site.collection_name == collection_name,
    )
    result = await session.execute(stmt)
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Site with collection '{collection_name}' already exists",
        )

    site = Site(
        user_id=user.id,
        collection_name=collection_name,
        url=site_data.url,
        widget_config={
            "title": "AI Assistant",
            "welcomeMessage": "Hello! How can I help you today?",
            "color": "#3B82F6",
            "sendText": "Send",
            "placeholder": "Type your message...",
        },
    )
    session.add(site)
    await session.flush()

    return SiteResponse(
        id=site.id,
        user_id=site.user_id,
        collection_name=site.collection_name,
        url=site.url,
        widget_config=site.widget_config or {},
        pages_indexed=site.pages_indexed,
        created_at=site.created_at,
    )


@router.get("/sites/{site_id}", response_model=SiteResponse)
async def get_site(
    site_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    stmt = select(Site).where(Site.id == site_id, Site.user_id == user.id)
    result = await session.execute(stmt)
    site = result.scalar_one_or_none()

    if not site:
        raise HTTPException(status_code=404, detail="Site not found")

    usage = await get_site_usage(session, site.id)
    return SiteResponse(
        id=site.id,
        user_id=site.user_id,
        collection_name=site.collection_name,
        url=site.url,
        widget_config=site.widget_config or {},
        pages_indexed=site.pages_indexed,
        created_at=site.created_at,
        deepseek_tokens=usage["deepseek_tokens"],
        jina_tokens=usage["jina_tokens"],
        chat_requests=usage["chat_requests"],
    )


@router.put("/sites/{site_id}/widget", response_model=SiteResponse)
async def update_widget_config(
    site_id: int,
    config: WidgetConfigUpdate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    stmt = select(Site).where(Site.id == site_id, Site.user_id == user.id)
    result = await session.execute(stmt)
    site = result.scalar_one_or_none()

    if not site:
        raise HTTPException(status_code=404, detail="Site not found")

    current_config = site.widget_config or {}
    updates = config.model_dump(exclude_unset=True)
    current_config.update(updates)
    site.widget_config = current_config
    await session.flush()

    usage = await get_site_usage(session, site.id)
    return SiteResponse(
        id=site.id,
        user_id=site.user_id,
        collection_name=site.collection_name,
        url=site.url,
        widget_config=site.widget_config or {},
        pages_indexed=site.pages_indexed,
        created_at=site.created_at,
        deepseek_tokens=usage["deepseek_tokens"],
        jina_tokens=usage["jina_tokens"],
        chat_requests=usage["chat_requests"],
    )


@router.delete("/sites/{site_id}")
async def delete_site(
    site_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    stmt = select(Site).where(Site.id == site_id, Site.user_id == user.id)
    result = await session.execute(stmt)
    site = result.scalar_one_or_none()

    if not site:
        raise HTTPException(status_code=404, detail="Site not found")

    await session.delete(site)
    await session.flush()
    return {"status": "deleted"}


# ===================== Stats =====================

@router.get("/user/stats", response_model=UserStatsResponse)
async def get_user_stats(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    usage = await get_total_usage(session, user.id)

    # Get per-site breakdown
    stmt = select(Site).where(Site.user_id == user.id)
    result = await session.execute(stmt)
    sites = result.scalars().all()

    sites_list = []
    for site in sites:
        site_usage = await get_site_usage(session, site.id)
        sites_list.append({
            "site_id": site.id,
            "collection_name": site.collection_name,
            "url": site.url,
            "deepseek_tokens": site_usage["deepseek_tokens"],
            "jina_tokens": site_usage["jina_tokens"],
            "chat_requests": site_usage["chat_requests"],
        })

    return UserStatsResponse(
        total_deepseek_tokens=usage["deepseek_tokens"],
        total_jina_tokens=usage["jina_tokens"],
        total_chat_requests=usage["chat_requests"],
        total_pages_indexed=usage["ingest_pages"],
        sites=sites_list,
    )


# ===================== Tariffs =====================

@router.get("/tariffs", response_model=List[TariffResponse])
async def list_tariffs(session: AsyncSession = Depends(get_session)):
    stmt = select(Tariff).order_by(Tariff.price_rub_month)
    result = await session.execute(stmt)
    tariffs = result.scalars().all()
    return tariffs


@router.get("/user/subscription", response_model=SubscriptionResponse)
async def get_subscription(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    stmt = (
        select(Subscription, Tariff)
        .join(Tariff, Tariff.id == Subscription.tariff_id)
        .where(Subscription.user_id == user.id, Subscription.active == True)
    )
    result = await session.execute(stmt)
    row = result.first()

    if not row:
        raise HTTPException(status_code=404, detail="No active subscription")

    subscription, tariff = row
    return SubscriptionResponse(
        id=subscription.id,
        user_id=subscription.user_id,
        tariff=TariffResponse.model_validate(tariff),
        active=subscription.active,
        created_at=subscription.created_at,
        expires_at=subscription.expires_at,
    )


# ===================== Payments =====================

@router.get("/user/payments", response_model=List[PaymentResponse])
async def list_payments(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    stmt = (
        select(Payment)
        .where(Payment.user_id == user.id)
        .order_by(Payment.created_at.desc())
        .limit(50)
    )
    result = await session.execute(stmt)
    payments = result.scalars().all()
    return payments