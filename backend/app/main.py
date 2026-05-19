from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
import os
from typing import Optional, List
from contextlib import asynccontextmanager

from .ingest import ingest_url, ingest_urls, crawl_site, ingest_background, _get_job_status, _create_job, _get_collection_active_ingests, embed_texts, _active_collection_ingests, _ingest_jobs
from .qdrant_client import get_qdrant_client
import uuid
from .rag import query_and_build_context, call_llm_with_context, call_llm_stream

from .database import init_db, get_session, async_session_factory
from .models import Tariff, User, Site, Subscription
from .auth import (
    verify_google_token, get_or_create_user, create_jwt,
    get_current_user, get_current_user_or_none
)
from .schemas import TokenResponse, UserResponse
from .tracking import check_chat_quota, check_ingest_quota, record_jina_usage, get_total_usage
from .dashboard import router as dashboard_router
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# Production root path support (set to /iSdelal on server)
ROOT_PATH = os.getenv("ROOT_PATH", "")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: init DB and seed tariffs."""
    await init_db()
    await seed_tariffs()
    yield


app = FastAPI(root_path=ROOT_PATH, lifespan=lifespan)

# Add CORS middleware - more secure configuration
allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:8080,http://localhost:8000,http://localhost:4173,http://localhost:4174").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if os.getenv("ALLOW_ALL_ORIGINS", "false").lower() == "true" else allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

# Mount static files
app.mount("/widget", StaticFiles(directory="/app/widget"), name="widget")
app.mount("/admin/static", StaticFiles(directory="/app/frontend"), name="frontend_static")

# Include dashboard router
app.include_router(dashboard_router)


async def seed_tariffs():
    """Ensure default tariffs exist in the database."""
    async with async_session_factory() as session:
        try:
            stmt = select(Tariff)
            result = await session.execute(stmt)
            existing = result.scalars().all()
            existing_names = {t.name for t in existing}

            defaults = [
                Tariff(name="free", pages_limit=10, requests_limit=100, price_rub_month=0, description="First 10 pages and 100 requests free"),
                Tariff(name="tariff_100", pages_limit=100, requests_limit=-1, price_rub_month=1000, description="100 pages, unlimited requests"),
                Tariff(name="tariff_500", pages_limit=500, requests_limit=-1, price_rub_month=5000, description="500 pages, unlimited requests"),
                Tariff(name="tariff_1000", pages_limit=1000, requests_limit=-1, price_rub_month=10000, description="1000 pages, unlimited requests"),
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


# ===================== Auth Endpoints =====================

class GoogleAuthRequest(BaseModel):
    credential: str  # Google ID token from client-side Sign In With Google

@app.post("/auth/google")
async def google_auth(req: GoogleAuthRequest, session: AsyncSession = Depends(get_session)):
    """Exchange Google ID token for JWT. Create user if not exists."""
    try:
        google_data = await verify_google_token(req.credential)
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid Google token: {str(e)}")

    user, created = await get_or_create_user(session, google_data)
    await session.commit()

    token = create_jwt(user.id, user.email)
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse(
            id=user.id,
            email=user.email,
            name=user.name,
            avatar_url=user.avatar_url,
            created_at=user.created_at,
        ),
    )


@app.get("/auth/me")
async def auth_me(user: User = Depends(get_current_user)):
    """Get current user info from JWT."""
    return UserResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        avatar_url=user.avatar_url,
        created_at=user.created_at,
    )


# ===================== Legacy Endpoints (now protected) =====================

class IngestRequest(BaseModel):
    url: Optional[str] = None
    urls: Optional[List[str]] = None
    collection: str = 'site_collection'

class ChatRequest(BaseModel):
    question: str
    collection: str = 'site_collection'

@app.post('/ingest')
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

@app.get('/ingest/status/{job_id}')
async def ingest_status(job_id: str):
    status = _get_job_status(job_id)
    if status.get("status") == "not_found":
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    return status

@app.get('/ingest/active')
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

@app.get('/ingest/jobs')
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

@app.post('/chat')
async def chat(
    req: ChatRequest,
    user: User | None = Depends(get_current_user_or_none),
    session: AsyncSession = Depends(get_session),
):
    # Check quota (only if authenticated)
    if user:
        await check_chat_quota(user, session)

    # Check if there are any active ingest processes for this collection
    active_ingests = _get_collection_active_ingests(req.collection)

    if active_ingests:
        active_ingest = active_ingests[0]
        progress = active_ingest.get("progress", {})
        pages_fetched = progress.get("pages_fetched", 0)
        message = progress.get("message", "Processing website content...")

        return {
            'answer': f'🕒 AI is currently processing your website content. Status: {message} ({pages_fetched} pages indexed so far). Please check back in a few minutes when training is complete.',
            'status': 'processing',
            'progress': progress
        }

    # Find site for tracking
    site = None
    if user:
        stmt = select(Site).where(
            Site.user_id == user.id,
            Site.collection_name == req.collection,
        )
        result = await session.execute(stmt)
        site = result.scalar_one_or_none()
    if not site:
        # Fallback: find any site with this collection (for anonymous tracking)
        stmt = select(Site).where(
            Site.collection_name == req.collection,
        ).order_by(Site.id.asc()).limit(1)
        result = await session.execute(stmt)
        site = result.scalar_one_or_none()

    # 1) embed question
    embs = embed_texts([req.question])
    q_emb = embs[0]
    # 2) query qdrant
    snippets = query_and_build_context(q_emb, collection_name=req.collection)
    # 3) call LLM with context
    res = call_llm_with_context(req.question, snippets)

    # Track DeepSeek usage (always, if we found a site)
    if site:
        from .tracking import record_deepseek_usage
        tokens = res.get("usage_total_tokens", 0)
        await record_deepseek_usage(session, site.user_id, site.id, tokens)
        await session.commit()

    return {
        'answer': res['answer'],
        'status': 'ready',
    }


@app.post('/chat/stream')
async def chat_stream(
    req: ChatRequest,
    user: User | None = Depends(get_current_user_or_none),
    session: AsyncSession = Depends(get_session),
):
    # Check quota (only if authenticated)
    if user:
        await check_chat_quota(user, session)

    # Check active ingests
    active_ingests = _get_collection_active_ingests(req.collection)
    if active_ingests:
        return {
            'answer': 'AI is still processing your website content. Please wait.',
            'status': 'processing'
        }

    # Find site for tracking
    site = None
    if user:
        stmt = select(Site).where(
            Site.user_id == user.id,
            Site.collection_name == req.collection,
        )
        result = await session.execute(stmt)
        site = result.scalar_one_or_none()
    if not site:
        stmt = select(Site).where(
            Site.collection_name == req.collection,
        ).order_by(Site.id.asc()).limit(1)
        result = await session.execute(stmt)
        site = result.scalar_one_or_none()

    # 1) embed question
    embs = embed_texts([req.question])
    q_emb = embs[0]
    # 2) query qdrant
    snippets = query_and_build_context(q_emb, collection_name=req.collection)

    # 3) stream LLM response
    async def token_generator():
        total_tokens = 0
        for token in call_llm_stream(req.question, snippets):
            yield f"data: {token}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        token_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )

@app.get('/collections')
async def get_collections(user: User = Depends(get_current_user)):
    """Get list of available collections from Qdrant."""
    try:
        client = get_qdrant_client()
        collections_response = client.get_collections()
        return {
            "collections": [
                {"name": col.name} for col in collections_response.collections
            ]
        }
    except Exception as e:
        print(f"Error getting collections: {e}")
        return {"collections": []}

@app.get('/collections/{collection_name}')
async def get_collection_info(
    collection_name: str,
    user: User = Depends(get_current_user),
):
    """Get information about a specific collection."""
    try:
        client = get_qdrant_client()
        collection_info = client.get_collection(collection_name)
        return {
            "name": collection_name,
            "points_count": collection_info.points_count,
            "indexed_vectors_count": collection_info.indexed_vectors_count if hasattr(collection_info, 'indexed_vectors_count') else 0
        }
    except Exception as e:
        print(f"Error getting collection info for {collection_name}: {e}")
        raise HTTPException(status_code=404, detail=f"Collection {collection_name} not found")

# Routes that need to override static mounts should come AFTER the mounts
@app.get("/admin/")
async def serve_frontend_index():
    return FileResponse("/app/frontend/index.html", media_type="text/html")

@app.get('/health')
@app.head('/health')
async def health():
    return {'status': 'ok'}