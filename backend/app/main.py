from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
import os
from typing import Optional, List
from .ingest import ingest_url, ingest_urls, crawl_site, ingest_background, _get_job_status, _create_job, _get_collection_active_ingests, embed_texts, _active_collection_ingests, _ingest_jobs
from .qdrant_client import get_qdrant_client
import uuid
from .rag import query_and_build_context, call_llm_with_context

app = FastAPI()

# Add CORS middleware - more secure configuration
allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:8080,http://localhost:8000,http://localhost:4173,http://localhost:4174").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if os.getenv("ALLOW_ALL_ORIGINS", "false").lower() == "true" else allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],  # Added GET for frontend route
    allow_headers=["*"],
)

# Mount static files
app.mount("/widget", StaticFiles(directory="/app/widget"), name="widget")
app.mount("/frontend/static", StaticFiles(directory="/app/frontend"), name="frontend_static")

# Routes that need to override static mounts should come AFTER the mounts
@app.get("/frontend/")
async def serve_frontend_index():
    return FileResponse("/app/frontend/index.html", media_type="text/html")

class IngestRequest(BaseModel):
    url: Optional[str] = None
    urls: Optional[List[str]] = None
    collection: str = 'site_collection'

class ChatRequest(BaseModel):
    question: str
    collection: str = 'site_collection'

@app.post('/ingest')
async def ingest(req: IngestRequest, background_tasks: BackgroundTasks = None):
    try:
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
        
        # Submit background task
        if background_tasks:
            background_tasks.add_task(
                ingest_background,
                job_id,
                url=req.url,
                urls=req.urls,
                collection_name=req.collection
            )
        
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
                "job_id": None,  # Find job_id from status
                "collection": collection_name,
                "url": job_info.get("target", ""),
                "status": job_info.get("status", "unknown"),
                "progress": job_info.get("progress", {}),
                "created_at": job_info.get("created_at")
            }

            # Find matching job_id
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

    # Sort jobs by creation time (most recent first)
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
async def chat(req: ChatRequest):
    # Check if there are any active ingest processes for this collection
    active_ingests = _get_collection_active_ingests(req.collection)

    if active_ingests:
        # Return processing status instead of answering
        active_ingest = active_ingests[0]  # Take first active ingest
        progress = active_ingest.get("progress", {})
        pages_fetched = progress.get("pages_fetched", 0)
        message = progress.get("message", "Processing website content...")

        return {
            'answer': f'🕒 AI is currently processing your website content. Status: {message} ({pages_fetched} pages indexed so far). Please check back in a few minutes when training is complete.',
            'status': 'processing',
            'progress': progress
        }

    # No active ingest processes - proceed with normal chat
    # 1) embed question
    embs = embed_texts([req.question])
    q_emb = embs[0]
    # 2) query qdrant
    snippets = query_and_build_context(q_emb, collection_name=req.collection)
    # 3) call LLM with context
    res = call_llm_with_context(req.question, snippets)
    return {'answer': res['answer'], 'status': 'ready'}

@app.get('/collections')
async def get_collections():
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
async def get_collection_info(collection_name: str):
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

@app.get('/health')
@app.head('/health')
async def health():
    return {'status': 'ok'}
