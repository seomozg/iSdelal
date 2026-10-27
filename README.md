# iSdelal — RAG-система для сайтов

Контекстные ответы ИИ по содержимому сайта: встраиваемый чат-виджет, Telegram-бот
и админ-панель. Построено на **Qdrant + FastAPI + DeepSeek + Jina embeddings**.

## ✨ Возможности

- **🔍 Семантический поиск** — векторная близость на базе Qdrant.
- **🕷️ Краулинг и индексация** — автопарсинг сайта, разбивка на чанки, эмбеддинги,
  инкрементальный upsert (поддержка Playwright для JS-сайтов).
- **🤖 Контекстный чат** — стриминговые ответы (SSE) по проиндексированному контенту.
- **💬 Встраиваемый виджет** — маленький JS-виджет без зависимостей.
- **📎 Документы** — PDF, Excel, Google Docs и Google Sheets прямо в базе знаний
  проекта: ответы учитывают и сайт, и документы клиента.
- **📱 Telegram-бот** — тот же RAG-конвейер в Telegram, с deep-ссылками на коллекцию
  (`t.me/<bot>?start=<collection>`).
- **📊 Админ-панель** — React SPA: сайты, статистика, генератор кода виджета, тарифы,
  платежи YooKassa.
- **🔐 Аутентификация** — Google Sign-In + JWT, изоляция данных пользователей.
- **🐳 Docker** — один `docker compose up` для всего стека.

## 🏗️ Архитектура

```
Browser  ── widget/widget.js ──────────┐
Telegram ── Bot API (long polling) ────┤
React SPA ── REST /api/* ──────────────┤── FastAPI backend ──┬─ Qdrant (векторы)
                                       │                    ├─ DeepSeek (LLM)
                                       │                    └─ Jina (эмбеддинги)
                                       └─ nginx (TLS, прокси, статика)
```

| Компонент | Где | Роль |
|-----------|-----|------|
| `backend/` | `backend/app` | FastAPI: REST API, индексация, RAG, аутентификация, Telegram-бот |
| `widget/` | `widget/` | Встраиваемый JS-виджет (`widget.js`, `widget.css`) |
| `click-ai-widget/` | `click-ai-widget/src` | React SPA: лендинг + админ-панель |
| `qdrant` | `docker-compose.yml` | Векторная база данных |

Поток обработки сообщения: **эмбеддинг вопроса → поиск в Qdrant → промпт для LLM
с найденными сниппетами → стриминг ответа**. Telegram-бот использует ровно тот же
конвейер, что и эндпоинт виджета (`/chat/stream`).

## 📁 Структура репозитория

```
backend/
  app/
    main.py            фабрика приложения, middleware, mounts, lifespan, /health
    routers/           роутеры (auth, ingest, chat, sites, payments, …)
    ingest.py          оркестрация: краулинг → индексация
    crawler.py         загрузка страниц (HTTP + Playwright)
    embeddings.py      эмбеддинги Jina
    jobs.py            in-memory трекер задач индексации
    rag.py             поиск в Qdrant + промпт/стрим LLM
    qdrant_client.py   подключение к Qdrant
    database.py        async engine/session SQLAlchemy
    models.py          ORM-модели
    schemas.py         Pydantic-модели ответов
    auth.py            Google OAuth + JWT
    tracking.py        учёт использования и квоты
    telegram_bot.py    Telegram-бот (long polling)
  tests/               pytest
widget/                встраиваемый виджет (widget.js, widget.css)
click-ai-widget/       React SPA (Vite + TypeScript + Tailwind + shadcn/ui)
docker-compose.yml     сервисы qdrant + backend
```

## 🛠️ Технологии

- **Backend**: Python 3.11, FastAPI, SQLAlchemy (async, aiosqlite), Qdrant,
  OpenAI SDK (DeepSeek), httpx, requests, BeautifulSoup, Playwright.
- **Frontend**: React 18, TypeScript, Vite, Tailwind CSS, shadcn/ui, framer-motion.
- **Widget**: чистый JavaScript (без зависимостей).
- **Инфраструктура**: Docker Compose, nginx (прокси + TLS).

## 🚀 Быстрый старт

### Требования

- Docker и Docker Compose
- API-ключ [Jina AI](https://jina.ai) (эмбеддинги)
- API-ключ [DeepSeek](https://platform.deepseek.com) (LLM)

### 1. Настройка

```bash
git clone https://github.com/seomozg/iSdelal.git
cd iSdelal
cp backend/.env.example backend/.env
# отредактируйте backend/.env: JINA_API_KEY, DEEPSEEK_API_KEY
```

### 2. Запуск

```bash
docker compose up -d --build
docker compose ps
curl http://localhost:8000/health   # {"status":"ok"}
```

### 3. Frontend (разработка)

```bash
cd click-ai-widget
npm install
npm run dev          # http://localhost:8080
```

## ⚙️ Конфигурация

Ключевые переменные в `backend/.env` (полный список — в `backend/.env.example`):

| Переменная | Описание |
|-----------|----------|
| `JINA_API_KEY` | ключ Jina AI (эмбеддинги) |
| `DEEPSEEK_API_KEY` | ключ DeepSeek (LLM) |
| `QDRANT_HOST` / `QDRANT_PORT` | адрес Qdrant (по умолчанию `qdrant` / `6333`) |
| `EMBED_MODEL` | модель эмбеддингов (по умолчанию `jina-embeddings-v2-base-en`) |
| `RAG_TOP_K` | сниппетов контекста на ответ (по умолчанию `3`) |
| `CRAWL_MAX_PAGES` | максимум страниц за краулинг (по умолчанию `50`) |
| `USE_PLAYWRIGHT` | рендер JS перед парсингом (по умолчанию `true`) |
| `TG_BOT_TOKEN` | включает Telegram-бота (пусто = выключен) |
| `TG_DAILY_LIMIT` | сообщений бота на чат в день (по умолчанию `50`, `0` = без лимита) |

## 🔌 API

Публичные эндпоинты:

| Метод | Путь | Описание |
|-------|------|----------|
| `GET` | `/health` | проверка работоспособности |
| `POST` | `/ingest` | запустить индексацию (`url` или `urls` + `collection`) |
| `GET` | `/ingest/status/{job_id}` | статус задачи |
| `GET` | `/ingest/jobs` | последние задачи |
| `POST` | `/chat` | ответ RAG без стриминга |
| `POST` | `/chat/stream` | стриминговый ответ RAG (SSE) |
| `GET` | `/api/bot/info` | доступность Telegram-бота и username |
| `POST` | `/api/sites/{id}/documents` | добавить документ (multipart: `file` **или** `url`) |
| `GET` | `/api/sites/{id}/documents` | список документов проекта |
| `DELETE` | `/api/sites/{id}/documents/{docId}` | удалить документ из базы знаний |

С аутентификацией (Bearer JWT): `/auth/*`, `/collections`, `/api/sites*`,
`/api/user/*`, `/api/tariffs`, `/api/payments/*`. Интерактивная документация — `/docs`.

## 💬 Веб-виджет

Вставьте на любую страницу:

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

## 📎 Документы

В админке (страница проекта) можно дополнить базу знаний документами клиента:

- **Загрузка файлов** — PDF и Excel (`.xlsx`, до 10 МБ): все листы читаются как текст.
- **Google Docs / Google Sheets** — по ссылке. Документ должен быть опубликован:
  *Файл → Доступ → Все, у кого есть ссылка → Читатель*, иначе экспорт вернёт ошибку.

Документ нарезается на фрагменты, эмбеддится и попадает **в ту же коллекцию Qdrant**,
что и сайт, — пайплайн ответов (`/chat`, `/chat/stream`, виджет, Telegram-бот) работает
без изменений. Каждый чанк документа помечен `document_id`, поэтому удаление документа
забирает из Qdrant только его фрагменты, не затрагивая контент сайта.

Статусы документа: `processing` → `completed` (с числом фрагментов) или `failed`
(с причиной). Удаление — из списка документов на странице проекта.

## 🤖 Telegram-бот

1. Получите токен у [@BotFather](https://t.me/BotFather) и запишите `TG_BOT_TOKEN` в `.env`.
2. Перезапустите бэкенд (`docker compose up -d --force-recreate backend`).
3. Откройте deep-ссылку, чтобы привязать чат к коллекции:

```
https://t.me/<bot_username>?start=<collection_name>
```

Команды: `/start <collection>`, `/collection <collection>`, `/help`.

> ⚠️ Telegram игнорирует произвольные query-параметры — `t.me/<bot>?collection=...`
> **не** работает. Передаётся только `?start=<payload>` (как `/start <payload>`).

## 🧪 Тестирование

```bash
docker compose exec backend pytest tests/ -v
# или локально:
cd backend && pip install -r requirements.txt && pytest tests/ -v
```

Набор тестов покрывает: health, аутентификацию, чат/RAG-конвейер, индексацию,
подключение к Qdrant и Telegram-бота (роутинг, привязки, стриминг, лимиты).

## 📄 Лицензия

MIT — см. [LICENSE](LICENSE).

