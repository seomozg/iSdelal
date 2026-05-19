from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime
from typing import List

from .database import get_session
from .models import User, Site, UsageStats, Subscription, Tariff, Payment
from .auth import get_current_user
from .qdrant_client import get_qdrant_client
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
        # Get real pages count from Qdrant
        real_pages = site.pages_indexed
        try:
            qdrant = get_qdrant_client()
            coll = qdrant.get_collection(site.collection_name)
            real_pages = coll.points_count or 0
            # Update DB cache
            if real_pages != site.pages_indexed:
                site.pages_indexed = real_pages
                await session.flush()
        except Exception:
            pass
        response.append(SiteResponse(
            id=site.id,
            user_id=site.user_id,
            collection_name=site.collection_name,
            url=site.url,
            widget_config=site.widget_config or {},
            pages_indexed=real_pages,
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
            "title": "AI Ассистент",
            "welcomeMessage": "Привет! Чем я могу помочь?",
            "color": "#3B82F6",
            "sendText": "Отправить",
            "placeholder": "Задайте вопрос...",
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
    # Get real pages count from Qdrant
    real_pages = site.pages_indexed
    try:
        qdrant = get_qdrant_client()
        coll = qdrant.get_collection(site.collection_name)
        real_pages = coll.points_count or 0
        if real_pages != site.pages_indexed:
            site.pages_indexed = real_pages
            await session.flush()
    except Exception:
        pass
    return SiteResponse(
        id=site.id,
        user_id=site.user_id,
        collection_name=site.collection_name,
        url=site.url,
        widget_config=site.widget_config or {},
        pages_indexed=real_pages,
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


# ===================== YooKassa Webhook =====================

@router.post("/webhooks/yookassa")
async def yookassa_webhook(
    request: "Request",
    session: AsyncSession = Depends(get_session),
):
    """Receive YooKassa webhook events. Always verify via API before processing."""
    import requests as http_requests
    import os

    body = await request.json()
    event = body.get("event", "")
    payment_id = body.get("object", {}).get("id", "")

    if not payment_id:
        return {"status": "ok", "message": "no payment id"}

    YOOKASSA_SHOP_ID = os.getenv("YOOKASSA_SHOP_ID", "")
    YOOKASSA_SECRET_KEY = os.getenv("YOOKASSA_SECRET_KEY", "")

    if not YOOKASSA_SHOP_ID or not YOOKASSA_SECRET_KEY:
        return {"status": "error", "message": "YooKassa not configured"}

    # Always verify payment via API
    try:
        resp = http_requests.get(
            f"https://api.yookassa.ru/v3/payments/{payment_id}",
            auth=(YOOKASSA_SHOP_ID, YOOKASSA_SECRET_KEY),
            timeout=10,
        )
        if resp.status_code != 200:
            return {"status": "ok", "message": f"payment lookup failed: {resp.status_code}"}

        data = resp.json()
        actual_status = data.get("status", "")
    except Exception as e:
        print(f"Webhook verification failed: {e}")
        return {"status": "ok", "message": "verification error"}

    if actual_status != "succeeded":
        return {"status": "ok", "message": f"not succeeded: {actual_status}"}

    # Find payment record
    stmt = select(Payment).where(Payment.yookassa_id == payment_id)
    result = await session.execute(stmt)
    payment = result.scalar_one_or_none()

    if not payment:
        return {"status": "ok", "message": "payment record not found"}

    if payment.status == "succeeded":
        return {"status": "ok", "message": "already processed"}

    # Mark payment as succeeded
    payment.status = "succeeded"

    # Upgrade user's subscription
    metadata = data.get("metadata", {})
    tariff_name = metadata.get("tariff_name", payment.tariff_name)

    if tariff_name:
        # Find tariff
        stmt = select(Tariff).where(Tariff.name == tariff_name)
        result = await session.execute(stmt)
        tariff = result.scalar_one_or_none()

        if tariff:
            # Update or create subscription
            stmt = select(Subscription).where(Subscription.user_id == payment.user_id)
            result = await session.execute(stmt)
            sub = result.scalar_one_or_none()

            if sub:
                sub.tariff_id = tariff.id
                sub.active = True
            else:
                sub = Subscription(
                    user_id=payment.user_id,
                    tariff_id=tariff.id,
                    active=True,
                )
                session.add(sub)

    await session.flush()
    await session.commit()
    return {"status": "ok", "message": "payment verified and processed"}


class YooKassaRequest(BaseModel):
    tariff_name: str  # free, tariff_100, tariff_500, tariff_1000

@router.post("/payments/yookassa")
async def create_yookassa_payment(
    req: YooKassaRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Create a YooKassa payment for tariff upgrade."""
    import uuid
    import requests as http_requests
    import os

    YOOKASSA_SHOP_ID = os.getenv("YOOKASSA_SHOP_ID", "")
    YOOKASSA_SECRET_KEY = os.getenv("YOOKASSA_SECRET_KEY", "live_j4-TTfmrr3VMrbDRZYUfLc2eXzRXUVm8vsubW151YBM")

    if not YOOKASSA_SHOP_ID or not YOOKASSA_SECRET_KEY:
        raise HTTPException(status_code=500, detail="YooKassa not configured")

    # Price mapping
    prices = {
        "tariff_100": {"amount": 1000.00, "description": "Site-Agent: 100 страниц"},
        "tariff_500": {"amount": 5000.00, "description": "Site-Agent: 500 страниц"},
        "tariff_1000": {"amount": 10000.00, "description": "Site-Agent: 1000 страниц"},
    }

    if req.tariff_name not in prices:
        raise HTTPException(status_code=400, detail=f"Unknown tariff: {req.tariff_name}")

    price_info = prices[req.tariff_name]
    idempotency_key = str(uuid.uuid4())

    yookassa_body = {
        "amount": {
            "value": f"{price_info['amount']:.2f}",
            "currency": "RUB"
        },
        "capture": True,
        "confirmation": {
            "type": "redirect",
            "return_url": os.getenv("SITE_URL", "https://site-agent.online") + "/dashboard/billing"
        },
        "description": price_info["description"],
        "metadata": {
            "user_id": user.id,
            "tariff_name": req.tariff_name
        }
    }

    try:
        resp = http_requests.post(
            "https://api.yookassa.ru/v3/payments",
            headers={
                "Content-Type": "application/json",
                "Idempotence-Key": idempotency_key,
            },
            auth=(YOOKASSA_SHOP_ID, YOOKASSA_SECRET_KEY),
            json=yookassa_body,
            timeout=15,
        )

        if resp.status_code not in (200, 201):
            print(f"YooKassa error: {resp.status_code} {resp.text}")
            raise HTTPException(status_code=502, detail="Payment service error")

        data = resp.json()

        # Record payment in DB
        payment = Payment(
            user_id=user.id,
            amount=price_info["amount"],
            tariff_name=req.tariff_name,
            status="pending",
            yookassa_id=data.get("id"),
        )
        session.add(payment)
        await session.flush()
        await session.commit()

        # Return confirmation URL
        confirmation_url = data.get("confirmation", {}).get("confirmation_url", "")
        return {
            "payment_id": payment.id,
            "yookassa_id": data.get("id"),
            "confirmation_url": confirmation_url,
            "amount": price_info["amount"],
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"YooKassa request failed: {e}")
        raise HTTPException(status_code=502, detail=str(e))
