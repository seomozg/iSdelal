## Quick Repo Summary

This project is a lightweight RAG kit: Qdrant (vector DB) + FastAPI backend (Jina embeddings + DeepSeek chat) + Nginx reverse-proxy + a small JS widget. The backend lives in `backend/app`; static widget files live in `widget/`. Docker Compose wires the three services together.

**Why this structure**: containers isolate Qdrant, the API, and static delivery. The backend is responsible for crawling/ingesting pages into Qdrant and exposing two main API endpoints (`/ingest`, `/chat`) which are proxied under `/api/` by Nginx.

**Key files**
- `backend/app/main.py` — FastAPI endpoints and API-key check (header `X-API-Key`).
- `backend/app/ingest.py` — **crawls site from URL** (with auto-link discovery) **or indexes explicit list of URLs**. Chunks text, creates embeddings, upserts to Qdrant (incremental, no collection recreation).
- `backend/app/rag.py` — search Qdrant using query embedding and build prompt for LLM.
- `backend/app/qdrant_client.py` — Qdrant connection helper with version-agnostic fallback for old `qdrant-client` versions.
- `backend/.env.example` — env vars: `JINA_API_KEY`, `DEEPSEEK_API_KEY`, `API_KEY`, `QDRANT_HOST/PORT`, `EMBED_MODEL`, `CRAWL_MAX_PAGES`, `CRAWL_TIMEOUT`.
- `backend/tests/test_api.py` — pytest suite for health, auth, chat, ingest, and Qdrant connection.
- `widget/widget.js` — calls backend `/api/chat`, expects `window.AIWidgetConfig` or `AIWidget.init()`.
- `docker-compose.yml` / `docker-compose.override.yml` — prod vs dev (override mounts backend, enables hot-reload).

**Ingest workflow** (key change: incremental, no recreate)
1. **Auto-crawl mode**: `POST /ingest` with `{"url":"https://site.com","collection":"col"}` crawls the entire domain, follows links up to `CRAWL_MAX_PAGES` (default 50).
2. **Explicit URLs mode**: `POST /ingest` with `{"urls":["url1","url2",...]}` indexes only those URLs (useful for SPA or controlled indexing).
3. Both modes: extract text → chunk (800 words, 200 overlap) → embed → **upsert** (preserves existing points, incremental).

**Run & dev workflows**
- Production: `docker compose up --build -d` (uses `backend/.env`).
- Local dev: auto-uses `docker-compose.override.yml` (mounts `./backend`, hot-reload via `uvicorn --reload`).
- Logs: `docker compose logs -f backend` or `docker compose logs -f qdrant`.

**API surface & examples**
- Health: `GET /api/health`
- Ingest (auto-crawl): `POST /api/ingest` with `{"url":"https://example.com","collection":"site_collection"}`
- Ingest (explicit URLs): `POST /api/ingest` with `{"urls":["url1","url2"],"collection":"site_collection"}`
- Chat: `POST /api/chat` with `{"question":"...","collection":"site_collection"}` — requires `X-API-Key` header
- All `/ingest` and `/chat` require header `X-API-Key: <api_key>`

**Important env vars** (see `backend/.env.example`)
- `JINA_API_KEY` — Jina AI key for embeddings
- `DEEPSEEK_API_KEY` — DeepSeek key for LLM responses
- `API_KEY` — shared secret (sent in `X-API-Key` header)
- `QDRANT_HOST`, `QDRANT_PORT` — Qdrant address (default: `qdrant`, `6333`)
- `EMBED_MODEL` — Jina embedding model (default: `jina-embeddings-v2-base-en`)
- `RAG_TOP_K` — max context snippets for chat (default: `5`)
- `CRAWL_MAX_PAGES` — max pages to crawl (default: `50`)
- `CRAWL_TIMEOUT` — seconds per page (default: `30`)

**Project-specific patterns** (do not change without thought)
- **Incremental indexing**: `ingest.py` uses `upsert()` (no `recreate_collection`). Re-ingesting appends/updates; old chunks stay unless replaced by same URL-chunk pair.
- **Playwright support**: `ingest.py` can render JavaScript via `playwright.async_api` for SPAs; auto-detects if needed.
- **Vector shape**: points stored without named vector key (Qdrant config: `{"size": ..., "distance": "Cosine"}`). Never add vector naming.
- **Chunking**: `chunk_text(text, chunk_size=800, overlap=200)` — word-based splitting. Overlap prevents context loss.
- **OpenAI client**: modern style (`from openai import OpenAI`), used for both embeddings + chat completions (gpt-4.1 in `rag.py`).
- **Version compatibility**: `qdrant-client==1.16.0` pinned; fallback logic in `qdrant_client.py` handles version mismatches.

**Widget integration**
- Embed in host page:
  ```html
  <script>window.AIWidgetConfig = { apiBase: 'http://your-host', collection: 'site_collection', apiKey: 'your_key' };</script>
  <script src="http://your-host/widget/widget.js"></script>
  ```
- Or call: `window.AIWidget.init({ apiBase, collection, apiKey })`
- Widget posts to `http://host/api/chat` with JSON body and `X-API-Key` header

**Testing & debugging**
- Run tests: `docker compose exec backend pytest tests/test_api.py -v`
- Health check: `curl http://localhost:8081/api/health`
- Qdrant collections: `curl http://localhost:6333/collections | jq`
- Collection stats: `curl http://localhost:6333/collections/site_collection/info`
- View logs: `docker compose logs backend` or `docker compose logs qdrant`

**What AI agents should/should not modify**
- **Should**: refactor `backend/app/*` (preserve signatures); add tests; improve error messages; optimize chunk sizes or embedding models.
- **Should not**: change upsert semantics or add recreate calls; alter point vector shape; break API-key contract; remove Playwright support without migration plan.

**Quick reference**
- Main entry: `backend/app/main.py` (routes) → `ingest.py` (crawl/index) → `rag.py` (search/prompt) → `qdrant_client.py` (DB)
- Tests: `backend/tests/test_api.py` (11 pytest tests covering auth, endpoints, Qdrant)
- Deployment: `Dockerfile`, `docker-compose.yml`, `nginx/default.conf`
