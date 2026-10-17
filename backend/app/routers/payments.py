"""YooKassa payments: create payment + webhook."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import get_current_user
from ..database import get_session
from ..models import Payment, Subscription, Tariff, User

router = APIRouter(tags=["dashboard"])


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
    YOOKASSA_SECRET_KEY = os.getenv("YOOKASSA_SECRET_KEY", "")

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
