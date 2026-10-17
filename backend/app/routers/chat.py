"""RAG chat endpoints (non-streaming + SSE stream) and Qdrant collections."""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import get_current_user, get_current_user_or_none
from ..database import get_session
from ..embeddings import embed_texts
from ..jobs import _get_collection_active_ingests
from ..models import Site, User
from ..qdrant_client import get_qdrant_client
from ..rag import call_llm_stream, call_llm_with_context, query_and_build_context
from ..tracking import check_chat_quota

router = APIRouter(tags=["chat"])


class ChatRequest(BaseModel):
    question: str
    collection: str = 'site_collection'


@router.post('/chat')
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
    embs_result = embed_texts([req.question])
    embs, jina_tokens = embs_result if isinstance(embs_result, tuple) else (embs_result, 0)
    q_emb = embs[0]
    # 2) query qdrant
    snippets = query_and_build_context(q_emb, collection_name=req.collection)
    # 3) call LLM with context
    res = call_llm_with_context(req.question, snippets)

    # Track usage (always, if we found a site)
    if site:
        from ..tracking import record_deepseek_usage, record_jina_usage
        deepseek_tokens = res.get("usage_total_tokens", 0)
        await record_deepseek_usage(session, site.user_id, site.id, deepseek_tokens)
        if jina_tokens > 0:
            await record_jina_usage(session, site.user_id, site.id, jina_tokens)
        await session.commit()

    return {
        'answer': res['answer'],
        'status': 'ready',
    }


@router.post('/chat/stream')
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

    # 1) embed question (embed_texts returns (embeddings, jina_tokens) tuple)
    embs_result = embed_texts([req.question])
    embs, jina_tokens = embs_result if isinstance(embs_result, tuple) else (embs_result, 0)
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


@router.get('/collections')
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

@router.get('/collections/{collection_name}')
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
