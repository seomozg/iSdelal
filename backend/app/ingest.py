import requests
from .utils import html_to_text, chunk_text
from .qdrant_client import get_qdrant_client
from openai import OpenAI
import uuid
import os
from urllib.parse import urljoin, urlparse
from collections import deque
import asyncio
from typing import Dict, Any

EMBED_MODEL = os.getenv("EMBED_MODEL", "text-embedding-3-large")
CRAWL_MAX_PAGES = int(os.getenv("CRAWL_MAX_PAGES", 50))
CRAWL_TIMEOUT = int(os.getenv("CRAWL_TIMEOUT", 30))
NAVIGATION_TIMEOUT = int(os.getenv("NAVIGATION_TIMEOUT", 60))
USE_PLAYWRIGHT = os.getenv("USE_PLAYWRIGHT", "true").lower() == "true"

client_openai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# In-memory job tracker for background ingest tasks
_ingest_jobs: Dict[str, Dict[str, Any]] = {}


def _get_job_status(job_id: str) -> Dict[str, Any]:
    """Get status of a background ingest job."""
    if job_id not in _ingest_jobs:
        return {"status": "not_found"}
    return _ingest_jobs[job_id]


def _create_job(job_id: str, mode: str, target: str) -> None:
    """Initialize a new ingest job."""
    _ingest_jobs[job_id] = {
        "status": "pending",
        "mode": mode,  # "url", "urls", or "crawl"
        "target": target,  # URL or list representation
        "progress": {"pages_fetched": 0, "chunks_extracted": 0, "embeddings_created": 0, "points_upserted": 0},
        "error": None,
        "result": None
    }


def embed_texts(texts):
    """Embed texts using OpenAI API."""
    resp = client_openai.embeddings.create(
        model=EMBED_MODEL,
        input=texts
    )
    return [item.embedding for item in resp.data]


async def fetch_with_playwright(url: str, timeout: int = CRAWL_TIMEOUT) -> str:
    """Fetch page content using Playwright Async API (renders JavaScript).
    Falls back to requests if Playwright is not available.
    """
    try:
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()
            try:
                await page.goto(url, timeout=timeout * 1000, wait_until="networkidle")
                content = await page.content()
                return content
            finally:
                try:
                    await browser.close()
                except Exception:
                    pass
    except Exception as e:
        print(f"Playwright async fetch failed for {url}, falling back to requests: {e}")
        # Fallback to requests (sync) executed in thread
        def _requests_get(u, t):
            r = requests.get(u, timeout=t, allow_redirects=True)
            r.raise_for_status()
            return r.text

        return await asyncio.to_thread(_requests_get, url, timeout)


async def runtime_crawl(start_url: str, max_pages: int = CRAWL_MAX_PAGES, timeout: int = CRAWL_TIMEOUT):
    """
    Use Playwright to explore a single-page app at runtime.
    - opens pages in headless browser
    - collects hrefs and attempts to click link-like elements
    - follows navigation changes (including client-side routing)

    Returns list of (url, html_content) tuples.
    """
    try:
        from playwright.async_api import async_playwright
    except Exception as e:
        print(f"Playwright async not available: {e}")
        return []

    visited = set()
    results = []
    queue = [start_url]
    start_origin = urlparse(start_url).netloc

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        while queue and len(results) < max_pages:
            url = queue.pop(0)
            if url in visited:
                continue
            try:
                # primary attempt: wait for networkidle
                try:
                    await page.goto(url, timeout=NAVIGATION_TIMEOUT * 1000, wait_until="networkidle")
                except Exception as e:
                    # fallback: try longer timeout and wait for full load
                    try:
                        await page.goto(url, timeout=(NAVIGATION_TIMEOUT * 2) * 1000, wait_until="load")
                    except Exception as e2:
                        print(f"Playwright failed to goto {url}: {e} / {e2}")
                # small pause to allow client-side rendering
                try:
                    await asyncio.sleep(0.5)
                except Exception:
                    pass
            except Exception as e:
                print(f"Playwright failed to goto {url}: {e}")
            visited.add(url)

            try:
                html = await page.content()
                results.append((page.url, html))
            except Exception:
                results.append((url, ""))

            # 1) collect anchor hrefs
            try:
                hrefs = await page.eval_on_selector_all('a[href]', 'els => els.map(e => e.href)')
            except Exception:
                hrefs = []

            for h in hrefs:
                try:
                    parsed = urlparse(h)
                    if parsed.netloc == start_origin:
                        full = h.split('#')[0]
                        if full not in visited and full not in queue and len(results) + len(queue) < max_pages:
                            queue.append(full)
                except Exception:
                    continue

            # 2) try clicking interactive elements
            try:
                clickable_selectors = [
                    'a[href]',
                    '[role=link]',
                    'button',
                    '[data-href]',
                    '[data-route]'
                ]
                clicks = 0
                for sel in clickable_selectors:
                    elements = await page.query_selector_all(sel)
                    for el in elements:
                        if clicks >= 20 or len(results) >= max_pages:
                            break
                        try:
                            before = page.url
                            await el.click(timeout=2000)
                            try:
                                await page.wait_for_load_state('networkidle', timeout=2000)
                            except Exception:
                                pass
                            after = page.url
                            if after and after != before:
                                full = after.split('#')[0]
                                if urlparse(full).netloc == start_origin and full not in visited and full not in queue:
                                    queue.append(full)
                                    clicks += 1
                        except Exception:
                            continue
                    if clicks >= 20 or len(results) >= max_pages:
                        break
            except Exception:
                pass

        try:
            await browser.close()
        except Exception:
            pass

    return results


async def crawl_site(start_url: str, max_pages: int = CRAWL_MAX_PAGES, timeout: int = CRAWL_TIMEOUT):
    """
    Crawl a website starting from start_url, following same-domain links.
    If Playwright runtime crawling is enabled, prefer that for SPAs.

    Returns: list of (url, html_content) tuples, max max_pages pages.
    """
    if USE_PLAYWRIGHT:
        print("Using Playwright runtime crawler...")
        pages = await runtime_crawl(start_url, max_pages=max_pages, timeout=timeout)
        if pages:
            return pages
        # fallback to static crawl if runtime crawl returned nothing

    # Static request-based crawl
    visited = set()
    to_visit = deque([start_url])
    pages = []
    start_domain = urlparse(start_url).netloc

    while to_visit and len(pages) < max_pages:
        url = to_visit.popleft()
        if url in visited:
            continue
        if urlparse(url).netloc != start_domain:
            continue
        visited.add(url)
        try:
            r = requests.get(url, timeout=timeout, allow_redirects=True)
            r.raise_for_status()
            html_content = r.text
            pages.append((url, html_content))
            try:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(html_content, 'html.parser')
                for link in soup.find_all('a', href=True):
                    href = link['href']
                    absolute_url = urljoin(url, href)
                    absolute_url = absolute_url.split('#')[0]
                    if absolute_url not in visited and absolute_url not in to_visit:
                        to_visit.append(absolute_url)
            except Exception as e:
                print(f"Warning: Failed to extract links from {url}: {e}")
        except Exception as e:
            print(f"Warning: Failed to fetch {url}: {e}")
            continue

    return pages



async def ingest_url(url: str, collection_name: str = "site_collection"):
    """
    Crawl site starting from url and index ALL pages to a single collection.
    Collection is created once; subsequent calls add/update pages.
    """
    # 1. Crawl the site
    print(f"Starting crawl from {url} (max {CRAWL_MAX_PAGES} pages)...")
    pages = await crawl_site(url, max_pages=CRAWL_MAX_PAGES, timeout=CRAWL_TIMEOUT)
    
    if not pages:
        return {"status": "error", "detail": "No pages crawled"}
    
    print(f"Crawled {len(pages)} page(s), now processing...")
    
    # 2. Collect all chunks and their metadata across all pages
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
        return {"status": "error", "detail": "No chunks extracted from pages"}
    
    print(f"Total chunks extracted: {len(all_chunks)}")

    # 3. Create embeddings for all chunks (run sync embedding in thread)
    print("Creating embeddings...")
    embeddings = await asyncio.to_thread(embed_texts, all_chunks)
    vector_size = len(embeddings[0]) if embeddings else 1536
    
    # 4. Connect to Qdrant
    client_qdrant = get_qdrant_client()
    
    # 5. Create collection if it doesn't exist (don't recreate on each ingest!)
    try:
        # Try to get collection to check if it exists
        collections = client_qdrant.get_collections()
        collection_exists = any(col.name == collection_name for col in collections.collections)
    except Exception:
        collection_exists = False
    
    if collection_exists:
        print(f"Collection '{collection_name}' exists, will add/update points")
    else:
        print(f"Creating new collection '{collection_name}'...")
        # Use modern create_collection for qdrant-client 1.x
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
            # Collection might already exist, upsert will work either way
    
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
    client_qdrant.upsert(
        collection_name=collection_name,
        points=points
    )
    
    # 8. Get final collection stats
    collection_info = client_qdrant.get_collection(collection_name)
    points_count = collection_info.points_count
    
    return {
        "status": "ok",
        "pages_crawled": len(pages),
        "chunks_indexed": len(points),
        "total_points_in_collection": points_count,
        "collection": collection_name
    }


async def ingest_urls(urls: list, collection_name: str = "site_collection"):
    """
    Index a list of explicitly provided URLs (useful for SPA or when crawling fails).
    
    Args:
        urls: List of full URLs to index
        collection_name: Qdrant collection name
        
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
    embeddings = await asyncio.to_thread(embed_texts, all_chunks)
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
        
        if urls:
            res = await ingest_urls(urls, collection_name=collection_name)
        elif url:
            res = await ingest_url(url, collection_name=collection_name)
        else:
            raise ValueError("Either url or urls must be provided")
        
        _ingest_jobs[job_id]["status"] = "completed"
        _ingest_jobs[job_id]["result"] = res
    except Exception as e:
        print(f"Background ingest job {job_id} failed: {e}")
        _ingest_jobs[job_id]["status"] = "failed"
        _ingest_jobs[job_id]["error"] = str(e)
