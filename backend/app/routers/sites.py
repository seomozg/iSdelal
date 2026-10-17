"""Sites CRUD + widget config (per-user)."""
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import get_current_user
from ..database import get_session
from ..models import Site, User
from ..qdrant_client import get_qdrant_client
from ..schemas import SiteCreate, SiteResponse, WidgetConfigUpdate
from ..tracking import get_site_usage

router = APIRouter(prefix="/sites", tags=["dashboard"])


@router.get("", response_model=List[SiteResponse])
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


@router.post("", response_model=SiteResponse)
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


@router.get("/{site_id}", response_model=SiteResponse)
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


@router.put("/{site_id}/widget", response_model=SiteResponse)
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


@router.delete("/{site_id}")
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
