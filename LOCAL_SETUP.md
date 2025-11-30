# Локальная разработка iSdelal RAG

## Быстрый старт (локально)

### 1. Установка зависимостей

**Требования:**
- Docker Desktop (с Docker Compose)
- Python 3.9+ (для локального тестирования)
- Git

### 2. Настройка окружения

```powershell
# 1. Убедитесь, что находитесь в корне проекта
cd c:\Users\HONOR\Desktop\dev\iSdelal

# 2. Создайте локальный .env файл для разработки
# Уже должен быть backend\.env (скопирован с .env.example)
# Проверьте, что там стоят корректные переменные:

# backend\.env должен содержать:
# OPENAI_API_KEY=sk-... (ваш ключ OpenAI)
# API_KEY=your-local-dev-key-123
# QDRANT_HOST=qdrant
# QDRANT_PORT=6333
# EMBED_MODEL=text-embedding-3-large
# RAG_TOP_K=5
# CRAWL_MAX_PAGES=50
# CRAWL_TIMEOUT=30
```

### 3. Запуск локально (с Docker Compose)

```powershell
# Получите последние изменения из гитхаба (если нужно)
git pull origin main

# Запустите все сервисы в режиме разработки
docker compose up --build

# В отдельном терминале тестируйте API:
curl http://localhost:8081/api/health

# Для горячей перезагрузки backend используйте docker-compose.override.yml
# (он автоматически создаёт mount для ./backend)
```

### 4. Тестирование

```powershell
# Запустите тесты в контейнере
docker compose exec backend pytest tests/test_api.py -v

# Или локально (если Python установлен):
cd backend
pip install -r requirements.txt
pytest tests/test_api.py -v
```

### 5. Локальная разработка (горячая перезагрузка)

Backend **автоматически** перезагружается при изменении файлов благодаря `docker-compose.override.yml`:
- Изменяете `backend/app/*.py` → uvicorn автоматически перезагружает
- Логи смотрите: `docker compose logs -f backend`
- API доступен на `http://localhost:8081/api/`

### 6. Команды разработки

```powershell
# Просмотр логов
docker compose logs -f backend      # Логи backend
docker compose logs -f qdrant        # Логи Qdrant
docker compose logs -f nginx         # Логи Nginx

# Полный перезапуск
docker compose down
docker compose up --build

# Очистка данных (Qdrant)
docker compose down -v  # -v удаляет volumes (все данные)

# Проверка здоровья приложения
curl http://localhost:8081/api/health

# Просмотр коллекций в Qdrant
curl http://localhost:6333/collections | jq

# Инжект контента локально
curl -X POST "http://localhost:8081/api/ingest" `
  -H "Content-Type: application/json" `
  -H "X-API-Key: your-local-dev-key-123" `
  -d '{\"url\":\"https://example.com\",\"collection\":\"test_collection\"}'
```

## Workflow разработки → Deploy

### На локальной машине:
1. Разработайте фичу в `backend/app/`
2. Протестируйте: `docker compose up`, `pytest`
3. Коммитьте в Git: `git commit -am "Fix: ..."` 
4. Пушьте: `git push origin your-feature-branch`

### На сервере (test-domain.ru):
1. SSH на сервер
2. `cd /path/to/isdeal && git pull origin main`
3. `docker compose up --build -d`
4. Проверьте: `curl https://test-domain.ru/api/health`

### Масштабирование:
- Для prod используйте **переменные окружения** вместо жёстких путей
- Настройте **HTTPS** через Nginx + Let's Encrypt
- Используйте **Docker secrets** вместо .env файлов
- Мониторьте логи: `docker compose logs backend`

## Структура проекта

```
backend/
  app/
    main.py       ← FastAPI routes (/api/ingest, /api/chat, /api/health)
    ingest.py     ← Crawling & indexing (Playwright support)
    rag.py        ← Vector search & LLM prompting
    qdrant_client.py ← Qdrant DB helper
    utils.py      ← Utilities (chunking, etc.)
  tests/
    test_api.py   ← Pytest suite (11 tests)
  .env            ← Local env vars (git-ignored)
  requirements.txt ← Dependencies

widget/
  widget.js       ← JS for embedding chat on websites
  widget.css      ← Styles

nginx/
  default.conf    ← Reverse proxy config
  Dockerfile      ← Nginx image

docker-compose.yml ← Production config
docker-compose.override.yml ← Dev overrides (hot reload)
```

## Полезные ссылки внутри проекта

- API: http://localhost:8081/api/ (когда контейнеры запущены)
- Qdrant UI: http://localhost:6333/dashboard (если включен)
- Backend напрямую: http://localhost:8000/docs (Swagger)

## Решение проблем

**Контейнеры не запускаются:**
```powershell
docker compose logs backend
docker compose logs qdrant
```

**Горячая перезагрузка не работает:**
- Убедитесь, что есть `docker-compose.override.yml`
- Перезагрузите контейнер: `docker compose restart backend`

**OPENAI_API_KEY не работает:**
- Проверьте `backend/.env` содержит правильный ключ
- Перезагрузите контейнер: `docker compose restart backend`

**Qdrant потерял данные:**
- Данные хранятся в `qdrant_storage` volume
- `docker compose down -v` удаляет всё (будьте осторожны!)
- Используйте `docker compose down` (без -v) для сохранения

## Workflow Git для GitHub → Сервер

```powershell
# 1. На локальной машине
git checkout -b feature/my-feature
# ... разработка ...
git commit -am "Add: my-feature"
git push origin feature/my-feature

# 2. На GitHub: создать Pull Request, review, merge в main

# 3. На сервере (test-domain.ru)
git pull origin main
docker compose up --build -d
curl https://test-domain.ru/api/health
```

---

**Начните здесь для локальной разработки:**
```powershell
cd c:\Users\HONOR\Desktop\dev\iSdelal
docker compose up --build
# В другом терминале:
docker compose logs -f backend
```
