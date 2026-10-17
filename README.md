# iSdelal — RAG system for websites

Context-aware AI answers over website content, delivered as an embeddable chat
widget and a Telegram bot, managed from an admin dashboard. Built on
**Qdrant + FastAPI + DeepSeek + Jina embeddings**.

## ✨ Features

- **🔍 Semantic search** — Qdrant-powered vector similarity.
- **🕷️ Web crawling & indexing** — auto-crawl a site, chunk text, embed, upsert
  incrementally (Playwright support for JS-heavy pages).
- **🤖 Context-aware chat** — streaming answers (SSE) grounded in the indexed
  content.
- **💬 Embeddable widget** — a small vanilla-JS chat widget with no dependencies.
- **📱 Telegram bot** — same RAG pipeline in Telegram, with per-collection deep
  links (`t.me/<bot>?start=<collection>`).
- **📊 Admin dashboard** — React SPA: sites, usage stats, widget code generator,
  tariffs, YooKassa payments.
- **🔐 Auth** — Google Sign-In + JWT, per-user data isolation.
- **🐳 Docker** — one `docker compose up` for the whole stack.

## 🏗️ Architecture

```
Browser  ── widget/widget.js ──────────┐
Telegram ── Bot API (long polling) ────┤
React SPA ── REST /api/* ──────────────┤── FastAPI backend ──┬─ Qdrant (vectors)
                                       │                    ├─ DeepSeek (LLM)
                                       │                    └─ Jina (embeddings)
                                       └─ nginx (TLS, reverse proxy, static)
```

| Component | Location | Role |
|-----------|----------|------|
| `backend/` | `backend/app` | FastAPI app: REST API, ingestion, RAG, auth, Telegram bot |
| `widget/` | `widget/` | Vanilla JS embeddable chat widget (`widget.js`, `widget.css`) |
| `click-ai-widget/` | `click-ai-widget/src` | React SPA: landing page + admin dashboard |
| `qdrant` | `docker-compose.yml` | Vector database |

The data flow for a chat message is: **embed question → search Qdrant →
prompt LLM with retrieved snippets → stream answer**. The Telegram bot reuses
the exact same pipeline as the widget endpoint (`/chat/stream`).

## 📁 Repository layout

```
backend/
  app/
    main.py            app factory, middleware, mounts, lifespan, /health
    routers/           route modules (auth, ingest, chat, sites, payments, …)
    ingest.py          crawl + index orchestration
    crawler.py         page fetching (HTTP + Playwright)
    embeddings.py      Jina embeddings
    jobs.py            in-memory ingest job tracker
    rag.py             Qdrant search + LLM prompt/stream
    qdrant_client.py   Qdrant connection
    database.py        SQLAlchemy async engine/session
    models.py          ORM models
    schemas.py         Pydantic response models
    auth.py            Google OAuth + JWT
    tracking.py        usage tracking and quotas
    telegram_bot.py    Telegram bot (long polling)
  tests/               pytest suite
widget/                embeddable widget (widget.js, widget.css)
click-ai-widget/       React SPA (Vite + TypeScript + Tailwind + shadcn/ui)
docker-compose.yml     qdrant + backend services
```

## 🛠️ Tech stack

- **Backend**: Python 3.11, FastAPI, SQLAlchemy (async, aiosqlite), Qdrant,
  OpenAI SDK (DeepSeek), httpx, requests, BeautifulSoup, Playwright.
- **Frontend**: React 18, TypeScript, Vite, Tailwind CSS, shadcn/ui, framer-motion.
- **Widget**: vanilla JavaScript (no dependencies).
- **Infra**: Docker Compose, nginx (reverse proxy + TLS).

## 🚀 Quick start

### Prerequisites

- Docker & Docker Compose
- [Jina AI](https://jina.ai) API key (embeddings)
- [DeepSeek](https://platform.deepseek.com) API key (LLM)

### 1. Configure

```bash
git clone https://github.com/seomozg/iSdelal.git
cd iSdelal
cp backend/.env.example backend/.env
# edit backend/.env: JINA_API_KEY, DEEPSEEK_API_KEY
```

### 2. Run

```bash
docker compose up -d --build
docker compose ps
curl http://localhost:8000/health   # {"status":"ok"}
```

### 3. Frontend (development)

```bash
cd click-ai-widget
npm install
npm run dev          # http://localhost:8080
```

## ⚙️ Configuration

Key variables in `backend/.env` (full list in `backend/.env.example`):

| Variable | Description |
|----------|-------------|
| `JINA_API_KEY` | Jina AI key (embeddings) |
| `DEEPSEEK_API_KEY` | DeepSeek key (LLM) |
| `QDRANT_HOST` / `QDRANT_PORT` | Qdrant address (default `qdrant` / `6333`) |
| `EMBED_MODEL` | embedding model (default `jina-embeddings-v2-base-en`) |
| `RAG_TOP_K` | context snippets per answer (default `3`) |
| `CRAWL_MAX_PAGES` | max pages per crawl (default `50`) |
| `USE_PLAYWRIGHT` | render JS before crawling (default `true`) |
| `TG_BOT_TOKEN` | enables the Telegram bot (empty = disabled) |
| `TG_DAILY_LIMIT` | bot messages per chat per day (default `50`, `0` = unlimited) |

## 🔌 API

Public endpoints:

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | health check |
| `POST` | `/ingest` | start indexing (`url` or `urls` + `collection`) |
| `GET` | `/ingest/status/{job_id}` | job status |
| `GET` | `/ingest/jobs` | recent jobs |
| `POST` | `/chat` | non-streaming RAG answer |
| `POST` | `/chat/stream` | streaming RAG answer (SSE) |
| `GET` | `/api/bot/info` | Telegram bot availability + username |

Authenticated (Bearer JWT): `/auth/*`, `/collections`, `/api/sites*`,
`/api/user/*`, `/api/tariffs`, `/api/payments/*`. Interactive docs at `/docs`.

## 💬 Web widget

Embed on any page:

```html
<script>
window.AIWidgetConfig = {
  apiBase: 'https://your-host',
  collection: 'your_collection',
  title: 'AI Assistant',
  welcomeMessage: 'How can I help you?'
};
</script>
<script src="https://your-host/widget/widget.js"></script>
```

## 🤖 Telegram bot

1. Get a token from [@BotFather](https://t.me/BotFather), set `TG_BOT_TOKEN` in `.env`.
2. Restart the backend (`docker compose up -d --force-recreate backend`).
3. Open a deep link to bind a chat to a collection:

```
https://t.me/<bot_username>?start=<collection_name>
```

Commands: `/start <collection>`, `/collection <collection>`, `/help`.

> ⚠️ Telegram ignores arbitrary query params — `t.me/<bot>?collection=...` does
> **not** work. Only `?start=<payload>` is passed to the bot (as `/start <payload>`).

## 🧪 Testing

```bash
docker compose exec backend pytest tests/ -v
# or locally:
cd backend && pip install -r requirements.txt && pytest tests/ -v
```

The backend suite covers: health, auth, chat/RAG flow, ingest, Qdrant
connection, and the Telegram bot (routing, bindings, streaming, limits).

## 📄 License

MIT — see [LICENSE](LICENSE).

