"""Ingestion orchestration: crawl -> chunk -> embed -> upsert into Qdrant."""
import asyncio
import uuid

import requests

from .crawler import (
    CRAWL_MAX_PAGES,
    CRAWL_TIMEOUT,
    USE_PLAYWRIGHT,
    crawl_site,
    fetch_with_playwright,
)
from .embeddings import embed_texts
from .jobs import INGEST_TIMEOUT_SECONDS, _ingest_jobs
from .qdrant_client import get_qdrant_client
from .utils import chunk_text, html_to_text


async def ingest_url(url: str, collection_name: str = "site_collection", job_id: str | None = None):
    """
    Crawl site starting from url and index ALL pages to a single collection.
    Collection is created once; subsequent calls add/update pages.
    """
    # 1. Crawl the site
    print(f"Starting crawl from {url} (max {CRAWL_MAX_PAGES} pages)...")
    if job_id in _ingest_jobs:
        _ingest_jobs[job_id]["progress"].update({
            "message": f"Crawling from {url}...",
            "pages_fetched": 0,
            "chunks_extracted": 0,
            "embeddings_created": 0,
            "points_upserted": 0,
        })

    pages = await crawl_site(url, max_pages=CRAWL_MAX_PAGES, timeout=CRAWL_TIMEOUT, job_id=job_id)
    
    if not pages:
        if job_id in _ingest_jobs:
            _ingest_jobs[job_id]["progress"].update({
                "message": "No pages crawled",
                "pages_fetched": 0
            })
        return {"status": "error", "detail": "No pages crawled"}
    
    print(f"Crawled {len(pages)} page(s), now processing...")
    if job_id in _ingest_jobs:
        _ingest_jobs[job_id]["progress"].update({
            "pages_fetched": len(pages),
            "message": f"Processing {len(pages)} page(s)..."
        })
    
    # 2. Collect all chunks and their metadata across all pages
    all_chunks = []
    all_urls = []

    # Limit total chunks to avoid excessive API costs and processing time
    MAX_TOTAL_CHUNKS = 100
    chunks_per_page = MAX_TOTAL_CHUNKS // len(pages) if pages else MAX_TOTAL_CHUNKS

    for page_url, html_content in pages:
        if len(all_chunks) >= MAX_TOTAL_CHUNKS:
            break  # Stop if we've reached the limit

        try:
            text = html_to_text(html_content)

            # Skip pages that are too short or too long
            word_count = len(text.split())
            if word_count < 10:  # Skip nearly empty pages
                continue
            if word_count > 5000:  # Limit very large pages
                # Take first part of long pages only
                text = ' '.join(text.split()[:5000])

            chunks = chunk_text(text)
            # Limit chunks per page to distribute evenly
            chunks = chunks[:chunks_per_page] if chunks else []

            all_chunks.extend(chunks)
            all_urls.extend([page_url] * len(chunks))

            if job_id in _ingest_jobs:
                _ingest_jobs[job_id]["progress"].update({
                    "chunks_extracted": len(all_chunks),
                    "message": f"Extracting chunks... ({len(all_chunks)}/{MAX_TOTAL_CHUNKS})"
                })
        except Exception as e:
            print(f"Warning: Failed to process {page_url}: {e}")
            continue

    if not all_chunks:
        if job_id in _ingest_jobs:
            _ingest_jobs[job_id]["progress"].update({
                "message": "No chunks extracted from pages"
            })
        return {"status": "error", "detail": "No chunks extracted from pages"}

    print(f"Total chunks extracted: {len(all_chunks)} (limited to {MAX_TOTAL_CHUNKS} max)")

    # 3. Create embeddings for all chunks (run sync embedding in thread)
    print("Creating embeddings...")
    if job_id in _ingest_jobs:
        _ingest_jobs[job_id]["progress"]["message"] = "Creating embeddings..."

    result = await asyncio.to_thread(embed_texts, all_chunks)
    embeddings, jina_tokens = result if isinstance(result, tuple) else (result, 0)
    vector_size = len(embeddings[0]) if embeddings else 1536

    if job_id in _ingest_jobs:
        _ingest_jobs[job_id]["progress"].update({
            "embeddings_created": len(embeddings),
            "message": "Connecting to Qdrant..."
        })
    
    # 4. Connect to Qdrant
    client_qdrant = get_qdrant_client()
    
    # 5. Create collection if it doesn't exist (don't recreate on each ingest!)
    try:
        # Try to get collection to check if it exists
        collections = client_qdrant.get_collections()
        collection_exists = any(col.name == collection_name for col in collections.collections)

        if not collection_exists:
            print(f"Creating new collection '{collection_name}'...")
            client_qdrant.create_collection(
                collection_name=collection_name,
                vectors_config={
                    "size": vector_size,
                    "distance": "Cosine"
                }
            )
        else:
            print(f"Collection '{collection_name}' exists, will add/update points")

    except Exception as e:
        print(f"Warning: Collection check/create failed ({e}), attempting upsert anyway")
        # Collection might already exist or creation is in progress, upsert will work either way
    
    # 6. Create points (without vector name)
    points = []
    for i, (chunk, page_url, vec) in enumerate(zip(all_chunks, all_urls, embeddings)):
        point_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{page_url}-{i}"))
        points.append({
            "id": point_id,
            "vector": vec,  # <— WITHOUT VECTOR NAME
            "payload": {
                "text": chunk,
                "url": page_url,
                "chunk_id": i
            }
        })
    
    # 7. Upsert points (update or insert)
    print(f"Upserting {len(points)} points to Qdrant...")
    if job_id in _ingest_jobs:
        _ingest_jobs[job_id]["progress"]["message"] = f"Upserting {len(points)} points to Qdrant..."
    client_qdrant.upsert(
        collection_name=collection_name,
        points=points
    )
    
    # 8. Get final collection stats
    collection_info = client_qdrant.get_collection(collection_name)
    points_count = collection_info.points_count

    if job_id in _ingest_jobs:
        _ingest_jobs[job_id]["progress"].update({
            "points_upserted": len(points),
            "message": "Completed indexing"
        })
    
    return {
        "status": "ok",
        "pages_crawled": len(pages),
        "chunks_indexed": len(points),
        "total_points_in_collection": points_count,
        "collection": collection_name
    }


async def ingest_urls(urls: list, collection_name: str = "site_collection", job_id: str | None = None):
    """
    Index a list of explicitly provided URLs (useful for SPA or when crawling fails).
    
    Args:
        urls: List of full URLs to index
        collection_name: Qdrant collection name
        job_id: Optional job ID for progress tracking
        
    Returns: dict with indexing stats
    """
    if not urls:
        return {"status": "error", "detail": "No URLs provided"}
    
    print(f"Processing {len(urls)} provided URL(s)...")
    
    # 1. Fetch and process each URL
    pages = []
    for url in urls:
        try:
            print(f"Fetching {url}...")
            # try Playwright fetch first for JS-rendered pages
            if USE_PLAYWRIGHT:
                try:
                    html = await fetch_with_playwright(url, timeout=CRAWL_TIMEOUT)
                    pages.append((url, html))
                    continue
                except Exception:
                    pass
            r = requests.get(url, timeout=CRAWL_TIMEOUT, allow_redirects=True)
            r.raise_for_status()
            pages.append((url, r.text))
        except requests.RequestException as e:
            print(f"Warning: Failed to fetch {url}: {e}")
            continue
    
    if not pages:
        return {"status": "error", "detail": "Failed to fetch any URLs"}
    
    print(f"Successfully fetched {len(pages)} page(s), now processing...")
    
    # 2. Collect all chunks across all pages
    all_chunks = []
    all_urls = []
    
    for page_url, html_content in pages:
        try:
            text = html_to_text(html_content)
            chunks = chunk_text(text)
            all_chunks.extend(chunks)
            all_urls.extend([page_url] * len(chunks))
        except Exception as e:
            print(f"Warning: Failed to process {page_url}: {e}")
            continue
    
    if not all_chunks:
        return {"status": "error", "detail": "No chunks extracted from URLs"}
    
    print(f"Total chunks extracted: {len(all_chunks)}")
    
    # 3. Create embeddings
    print("Creating embeddings...")
    result = await asyncio.to_thread(embed_texts, all_chunks)
    embeddings, jina_tokens = result if isinstance(result, tuple) else (result, 0)
    vector_size = len(embeddings[0]) if embeddings else 1536
    
    # 4. Connect to Qdrant
    client_qdrant = get_qdrant_client()
    
    # 5. Create collection if it doesn't exist
    try:
        collections = client_qdrant.get_collections()
        collection_exists = any(col.name == collection_name for col in collections.collections)
    except Exception:
        collection_exists = False
    
    if collection_exists:
        print(f"Collection '{collection_name}' exists, will add/update points")
    else:
        print(f"Creating new collection '{collection_name}'...")
        try:
            client_qdrant.create_collection(
                collection_name=collection_name,
                vectors_config={
                    "size": vector_size,
                    "distance": "Cosine"
                }
            )
        except Exception as e:
            print(f"Warning: create_collection failed ({e}), attempting upsert anyway")
    
    # 6. Create points
    points = []
    for i, (chunk, page_url, vec) in enumerate(zip(all_chunks, all_urls, embeddings)):
        point_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{page_url}-{i}"))
        points.append({
            "id": point_id,
            "vector": vec,
            "payload": {
                "text": chunk,
                "url": page_url,
                "chunk_id": i
            }
        })
    
    # 7. Upsert points
    print(f"Upserting {len(points)} points to Qdrant...")
    client_qdrant.upsert(
        collection_name=collection_name,
        points=points
    )
    
    # 8. Get final stats
    collection_info = client_qdrant.get_collection(collection_name)
    points_count = collection_info.points_count
    
    return {
        "status": "ok",
        "pages_indexed": len(pages),
        "chunks_indexed": len(points),
        "total_points_in_collection": points_count,
        "collection": collection_name
    }


async def ingest_background(job_id: str, url: str = None, urls: list = None, collection_name: str = 'site_collection'):
    """
    Background ingest task: crawls/fetches and indexes without blocking the HTTP response.
    Updates job status in _ingest_jobs as it progresses.
    """
    try:
        _ingest_jobs[job_id]["status"] = "running"

        async def _run_ingest():
            if urls:
                return await ingest_urls(urls, collection_name=collection_name, job_id=job_id)
            elif url:
                return await ingest_url(url, collection_name=collection_name, job_id=job_id)
            else:
                raise ValueError("Either url or urls must be provided")

        try:
            res = await asyncio.wait_for(_run_ingest(), timeout=INGEST_TIMEOUT_SECONDS)
            _ingest_jobs[job_id]["status"] = "completed"
            _ingest_jobs[job_id]["result"] = res
        except asyncio.TimeoutError:
            msg = f"Ingest job {job_id} timed out after {INGEST_TIMEOUT_SECONDS} seconds"
            print(msg)
            _ingest_jobs[job_id]["status"] = "failed"
            _ingest_jobs[job_id]["error"] = msg
            if job_id in _ingest_jobs:
                _ingest_jobs[job_id]["progress"]["message"] = msg
    except Exception as e:
        print(f"Background ingest job {job_id} failed: {e}")
        _ingest_jobs[job_id]["status"] = "failed"
        _ingest_jobs[job_id]["error"] = str(e)
