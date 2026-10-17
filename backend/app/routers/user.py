"""User profile, stats, subscription and payment history."""
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import get_current_user
from ..database import get_session
from ..models import Payment, Site, Subscription, Tariff, User
from ..qdrant_client import get_qdrant_client
from ..schemas import (
    PaymentResponse,
    SubscriptionResponse,
    TariffResponse,
    UserResponse,
    UserStatsResponse,
)
from ..tracking import get_site_usage, get_total_usage

router = APIRouter(prefix="/user", tags=["dashboard"])


@router.get("/me", response_model=UserResponse)
async def get_me(user: User = Depends(get_current_user)):
    return user


@router.get("/stats", response_model=UserStatsResponse)
async def get_user_stats(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    usage = await get_total_usage(session, user.id)

    # Get per-site breakdown
    stmt = select(Site).where(Site.user_id == user.id)
    result = await session.execute(stmt)
    sites = result.scalars().all()

    # Sum real points from Qdrant across all user sites
    total_qdrant_points = 0
    sites_list = []
    for site in sites:
        site_usage = await get_site_usage(session, site.id)
        # Get real points count from Qdrant
        real_points = 0
        try:
            qdrant = get_qdrant_client()
            coll = qdrant.get_collection(site.collection_name)
            real_points = coll.points_count or 0
        except Exception:
            pass
        total_qdrant_points += real_points
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
        total_pages_indexed=total_qdrant_points,
        sites=sites_list,
    )


@router.get("/subscription", response_model=SubscriptionResponse)
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


@router.get("/payments", response_model=List[PaymentResponse])
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

    # Auto-check pending payments against YooKassa
    import requests as http_requests
    import os as _os
    shop_id = _os.getenv("YOOKASSA_SHOP_ID", "")
    secret = _os.getenv("YOOKASSA_SECRET_KEY", "")
    if shop_id and secret:
        for p in payments:
            if p.status == "pending" and p.yookassa_id:
                try:
                    resp = http_requests.get(
                        f"https://api.yookassa.ru/v3/payments/{p.yookassa_id}",
                        auth=(shop_id, secret),
                        timeout=5,
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        if data.get("status") == "succeeded":
                            p.status = "succeeded"
                            # Upgrade subscription
                            tariff_name = data.get("metadata", {}).get("tariff_name", p.tariff_name)
                            t = (await session.execute(select(Tariff).where(Tariff.name == tariff_name))).scalar_one_or_none()
                            if t:
                                sub = (await session.execute(select(Subscription).where(Subscription.user_id == p.user_id))).scalar_one_or_none()
                                if sub:
                                    sub.tariff_id = t.id
                                    sub.active = True
                                else:
                                    session.add(Subscription(user_id=p.user_id, tariff_id=t.id, active=True))
                            await session.flush()
                except Exception:
                    pass

    return payments
