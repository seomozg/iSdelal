"""Ingestion endpoints (background jobs + status)."""
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import get_current_user_or_none
from ..database import get_session
from ..ingest import ingest_background
from ..jobs import (
    _active_collection_ingests,
    _create_job,
    _get_collection_active_ingests,
    _get_job_status,
    _ingest_jobs,
)
from ..models import Site, User
from ..tracking import check_ingest_quota

router = APIRouter(tags=["ingest"])


class IngestRequest(BaseModel):
    url: Optional[str] = None
    urls: Optional[List[str]] = None
    collection: str = 'site_collection'


@router.post('/ingest')
async def ingest(
    req: IngestRequest,
    user: User | None = Depends(get_current_user_or_none),
    session: AsyncSession = Depends(get_session),
):
    try:
        # Check quota (only if authenticated)
        if user:
            await check_ingest_quota(user, session, new_pages=1)

        # Create a job ID for this ingest task
        job_id = str(uuid.uuid4())

        # Determine mode
        if req.urls:
            mode = "urls"
            target = str(req.urls)
        elif req.url:
            mode = "url"
            target = req.url
        else:
            raise HTTPException(status_code=400, detail="Either 'url' or 'urls' must be provided")

        # Create the job record with collection
        _create_job(job_id, mode, target, req.collection)

        # Create or update Site record for tracking (only if authenticated)
        if user:
            stmt = select(Site).where(
                Site.user_id == user.id,
                Site.collection_name == req.collection,
            )
            result = await session.execute(stmt)
            site = result.scalar_one_or_none()
            if not site:
                site = Site(
                    user_id=user.id,
                    collection_name=req.collection,
                    url=req.url or (req.urls[0] if req.urls else ""),
                )
                session.add(site)
                await session.flush()

        # Submit background task via asyncio.create_task
        import asyncio as _asyncio
        _asyncio.create_task(
            ingest_background(
                job_id,
                url=req.url,
                urls=req.urls,
                collection_name=req.collection
            )
        )

        await session.commit()

        # Return immediately with 202 Accepted
        return {
            "status": "accepted",
            "job_id": job_id,
            "message": "Ingest job submitted. Check /ingest/status/{job_id} to monitor progress."
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get('/ingest/status/{job_id}')
async def ingest_status(job_id: str):
    status = _get_job_status(job_id)
    if status.get("status") == "not_found":
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    return status

@router.get('/ingest/active')
async def get_active_ingestions():
    """Get all active ingestion processes across all collections."""
    active_processes = []

    # Check all collections for active ingests
    for collection_name in _active_collection_ingests:
        active_jobs = _get_collection_active_ingests(collection_name)
        for job_info in active_jobs:
            process_info = {
                "job_id": None,
                "collection": collection_name,
                "url": job_info.get("target", ""),
                "status": job_info.get("status", "unknown"),
                "progress": job_info.get("progress", {}),
                "created_at": job_info.get("created_at")
            }

            for job_id, job_data in _ingest_jobs.items():
                if (job_data.get("collection") == collection_name and
                    job_data.get("status") in ["pending", "running"]):
                    process_info["job_id"] = job_id
                    break

            active_processes.append(process_info)

    return {"active_processes": active_processes}

@router.get('/ingest/jobs')
async def get_all_ingestions(limit: int = 10):
    """Get recent ingestion jobs across all collections."""
    recent_jobs = []

    sorted_jobs = sorted(
        _ingest_jobs.items(),
        key=lambda x: x[1].get("created_at", 0),
        reverse=True
    )[:limit]

    for job_id, job_data in sorted_jobs:
        recent_jobs.append({
            "job_id": job_id,
            "collection": job_data.get("collection"),
            "url": job_data.get("target", ""),
            "status": job_data.get("status", "unknown"),
            "progress": job_data.get("progress", {}),
            "created_at": job_data.get("created_at"),
            "error": job_data.get("error"),
            "result": job_data.get("result")
        })

    return {"jobs": recent_jobs}
