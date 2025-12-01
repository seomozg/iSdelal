from fastapi import FastAPI, HTTPException, Header, BackgroundTasks
from pydantic import BaseModel
import os
from typing import Optional, List
from .ingest import ingest_url, ingest_urls, crawl_site, ingest_background, _get_job_status, _create_job, embed_texts
import asyncio
import uuid
from .rag import query_and_build_context, call_llm_with_context

app = FastAPI()

class IngestRequest(BaseModel):
    url: Optional[str] = None
    urls: Optional[List[str]] = None
    collection: str = 'site_collection'

class ChatRequest(BaseModel):
    question: str
    collection: str = 'site_collection'

def verify_api_key(x_api_key: str):
    expected = os.getenv('API_KEY')
    if not expected or x_api_key != expected:
        raise HTTPException(status_code=401, detail="Invalid API key")

@app.post('/ingest')
async def ingest(req: IngestRequest, x_api_key: str = Header(None), background_tasks: BackgroundTasks = None):
    verify_api_key(x_api_key)
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
        
        # Create the job record
        _create_job(job_id, mode, target)
        
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
async def ingest_status(job_id: str, x_api_key: str = Header(None)):
    verify_api_key(x_api_key)
    status = _get_job_status(job_id)
    if status.get("status") == "not_found":
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    return status

@app.post('/chat')
async def chat(req: ChatRequest, x_api_key: str = Header(None)):
    verify_api_key(x_api_key)
    # 1) embed question
    embs = embed_texts([req.question])
    q_emb = embs[0]
    # 2) query qdrant
    snippets = query_and_build_context(q_emb, collection_name=req.collection)
    # 3) call LLM with context
    res = call_llm_with_context(req.question, snippets)
    return {'answer': res['answer']}

@app.get('/health')
async def health():
    return {'status': 'ok'}
