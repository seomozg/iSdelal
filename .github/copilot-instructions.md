# Repo quick reference (for AI assistants)

## What this project is

A RAG kit: **Qdrant** (vector DB) + **FastAPI** backend (**Jina** embeddings,
**DeepSeek** chat) + a small **JS widget** + a **React SPA** (landing + admin
dashboard) + a **Telegram bot** that reuses the chat pipeline + a standalone
**document bot** (`backend/app/docbot/`, `python -m app.docbot`).

## Key files

- `backend/app/main.py` — FastAPI app factory, middleware, mounts, lifespan (starts the Telegram bot), `/health`.
- `backend/app/routers/` — route modules (auth, ingest, chat, sites, payments, stats, tariffs, bot).
- `backend/app/ingest.py` — crawl/index orchestration; `crawler.py` (fetch), `embeddings.py` (Jina), `jobs.py` (in-memory job tracker).
- `backend/app/rag.py` — Qdrant search + LLM prompt/stream (`call_llm_stream(..., usage=)` optionally returns token usage).
- `backend/app/telegram_bot.py` — long-polling bot, per-chat collection binding (`telegram_chats` table).
- `backend/app/docbot/` — document bot: `bot.py` (`DocBot(TelegramBot)` — commands, file intake, RAG answers), `store.py` (its data layer), `collections.py` (Qdrant create/stats), `models.py` (own DB tables); entry `python -m app.docbot`.
- `backend/tests/` — pytest suite (API + bot).
- `widget/widget.js` — calls `/chat/stream`, reads `window.AIWidgetConfig`.
- `click-ai-widget/src` — React SPA (landing `pages/Index.tsx`, dashboard `pages/dashboard/`).
- `docker-compose.yml` — `qdrant` + `backend` + `docbot` (same image, `python -m app.docbot`).

## Chat/answer pipeline (shared by widget, API and bot)

1. embed question (`embed_texts` → returns `(embeddings, jina_tokens)` tuple)
2. search Qdrant (`query_and_build_context`)
3. stream answer (`call_llm_stream`, model `deepseek-chat`)

## Env vars

See `backend/.env.example`. Key: `JINA_API_KEY`, `DEEPSEEK_API_KEY`,
`QDRANT_HOST/PORT`, `EMBED_MODEL`, `TG_BOT_TOKEN`, `TG_DAILY_LIMIT`.

## Conventions to preserve

- Incremental indexing via `upsert()` — never recreate collections.
- Points stored without a named vector key; distance `Cosine`.
- `embed_texts` returns a tuple; unpack before indexing (`embs[0]`).
- Telegram bot: long polling assumes a single uvicorn worker; private chats only.
- Document bot: all its data access goes through `app/docbot/store.py`; its own DB
  (`DATABASE_URL` overridden in the compose `docbot` service), registry `docbot_collections`,
  token lives only in `backend/.env.docbot` (git-ignored, not in `.env.example`).
- Secrets live only in `backend/.env` (git-ignored) — never hardcode keys.
