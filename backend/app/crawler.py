"""Site crawling: static HTTP fetch + Playwright for JS-rendered pages."""
import asyncio
import os
from collections import deque
from urllib.parse import urljoin, urlparse

import requests

from .utils import html_to_text
from .jobs import _ingest_jobs

CRAWL_MAX_PAGES = int(os.getenv("CRAWL_MAX_PAGES", 50))
PLAYWRIGHT_MAX_PAGES = int(os.getenv("PLAYWRIGHT_MAX_PAGES", 30))
CRAWL_TIMEOUT = int(os.getenv("CRAWL_TIMEOUT", 30))
NAVIGATION_TIMEOUT = int(os.getenv("NAVIGATION_TIMEOUT", 60))
USE_PLAYWRIGHT = os.getenv("USE_PLAYWRIGHT", "true").lower() == "true"

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


async def runtime_crawl(start_url: str, max_pages: int = PLAYWRIGHT_MAX_PAGES, timeout: int = CRAWL_TIMEOUT, job_id: str | None = None):
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
                # Progress: about to open URL with Playwright
                if job_id in _ingest_jobs:
                    _ingest_jobs[job_id]["progress"].update({
                        "message": f"Playwright: opening {url}...",
                    })
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
                # Progress: successfully crawled a page via Playwright
                if job_id in _ingest_jobs:
                    _ingest_jobs[job_id]["progress"].update({
                        "pages_fetched": len(results),
                        "message": f"Playwright: crawled {len(results)}/{max_pages} page(s)...",
                    })
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
                        if clicks >= 10 or len(results) >= max_pages:
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


async def crawl_site(start_url: str, max_pages: int = CRAWL_MAX_PAGES, timeout: int = CRAWL_TIMEOUT, job_id: str | None = None):
    """\n+    Crawl a website starting from start_url, following same-domain links.\n+\n+    Strategy:\n+    1) Try simple HTTP crawl via requests (fast, cheap).\n+    2) If it finds no pages and USE_PLAYWRIGHT is enabled, fallback to Playwright runtime crawler.\n+\n+    Returns: list of (url, html_content) tuples, max max_pages pages.\n+    """
    # Normalize URL: prepend https:// if no scheme
    if "://" not in start_url:
        start_url = "https://" + start_url

    # 1) Static request-based crawl first
    visited = set()
    to_visit = deque([start_url])
    pages = []
    start_domain = urlparse(start_url).netloc

    print("Trying static HTTP crawl first...")

    while to_visit and len(pages) < max_pages:
        url = to_visit.popleft()
        if url in visited:
            continue
        if urlparse(url).netloc != start_domain:
            continue
        visited.add(url)

        # Update progress before fetching URL
        if job_id in _ingest_jobs:
            _ingest_jobs[job_id]["progress"].update({
                "message": f"Fetching {url}...",
                "pages_fetched": len(pages)
            })
        try:
            # Run blocking requests.get in a thread so that the async ingest task
            # remains cancellable by asyncio.wait_for (global ingest timeout).
            def _fetch(u, t):
                r = requests.get(u, timeout=t, allow_redirects=True)
                r.raise_for_status()
                return r.text

            html_content = await asyncio.to_thread(_fetch, url, timeout)
            pages.append((url, html_content))

            # After successful fetch, bump pages_fetched
            if job_id in _ingest_jobs:
                _ingest_jobs[job_id]["progress"].update({
                    "pages_fetched": len(pages),
                    "message": f"Fetched {len(pages)} page(s), discovering links..."
                })
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
            if job_id in _ingest_jobs:
                _ingest_jobs[job_id]["progress"].update({
                    "message": f"Failed to fetch {url}: {e}"  # keep pages_fetched as is
                })
            continue

    # 2) If static crawl got pages, check if they have meaningful text
    #    (SPA pages may have only a skeleton with no real content)
    if pages:
        total_words = 0
        for _, html in pages:
            text = html_to_text(html)
            total_words += len(text.split())
        avg_words = total_words / len(pages) if pages else 0
        if avg_words >= 10:
            return pages  # pages have real text, use them
        else:
            print(f"Static crawl returned {len(pages)} page(s) with only ~{avg_words:.0f} words/page — trying Playwright for JS-rendered content...")

    # 3) Fallback to Playwright runtime crawl if static crawl found nothing or only empty pages
    if USE_PLAYWRIGHT:
        print("Starting Playwright runtime crawler...")
        pw_pages = await runtime_crawl(start_url, max_pages=PLAYWRIGHT_MAX_PAGES, timeout=timeout, job_id=job_id)
        if pw_pages:
            return pw_pages

    return pages
