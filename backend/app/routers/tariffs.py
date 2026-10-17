"""Tariff plans."""
from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_session
from ..models import Tariff
from ..schemas import TariffResponse

router = APIRouter(prefix="/tariffs", tags=["dashboard"])


@router.get("", response_model=List[TariffResponse])
async def list_tariffs(session: AsyncSession = Depends(get_session)):
    stmt = select(Tariff).order_by(Tariff.price_rub_month)
    result = await session.execute(stmt)
    tariffs = result.scalars().all()
    return tariffs
