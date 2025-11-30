# Частые команды разработки

## Запуск и остановка

```powershell
# Стартовать все сервисы
docker compose up --build

# Стартовать в фоне (-d = detached)
docker compose up --build -d

# Остановить все
docker compose down

# Остановить и удалить volumes (данные!)
docker compose down -v

# Перезагрузить specific контейнер
docker compose restart backend
docker compose restart qdrant
docker compose restart nginx
```

## Логи и диагностика

```powershell
# Смотреть логи в реальном времени
docker compose logs -f                  # Все сервисы
docker compose logs -f backend          # Только backend
docker compose logs -f qdrant           # Только Qdrant
docker compose logs -f nginx            # Только Nginx

# Последние N строк
docker compose logs backend --tail 50

# Логи конкретного контейнера
docker logs -f rag-backend              # По имени контейнера

# Статус контейнеров
docker compose ps

# Размер и использование
docker system df
```

## Тестирование API (локально)

```powershell
# Health check
curl http://localhost:8081/api/health

# Инжект контента (авто-краул)
curl -X POST "http://localhost:8081/api/ingest" `
  -H "Content-Type: application/json" `
  -H "X-API-Key: your-local-dev-key-123" `
  -d '{\"url\":\"https://example.com\",\"collection\":\"test_col\"}'

# Инжект конкретных URL
curl -X POST "http://localhost:8081/api/ingest" `
  -H "Content-Type: application/json" `
  -H "X-API-Key: your-local-dev-key-123" `
  -d '{\"urls\":[\"https://example.com/page1\",\"https://example.com/page2\"],\"collection\":\"test_col\"}'

# Chat запрос
curl -X POST "http://localhost:8081/api/chat" `
  -H "Content-Type: application/json" `
  -H "X-API-Key: your-local-dev-key-123" `
  -d '{\"question\":\"What is this?\",\"collection\":\"test_col\"}'

# Swagger UI документация (если нужна)
# http://localhost:8000/docs
```

## Работа с Python кодом

```powershell
# Перейти в директорию backend
cd backend

# Установить зависимости локально (если нужно)
pip install -r requirements.txt

# Запустить тесты
pytest tests/test_api.py -v

# Запустить конкретный тест
pytest tests/test_api.py::test_health -v

# Запустить с покрытием
pytest tests/test_api.py --cov=app --cov-report=html

# Линтинг (опционально)
pip install flake8
flake8 app

# Type checking (опционально)
pip install mypy
mypy app
```

## Работа с Qdrant

```powershell
# Список коллекций
curl http://localhost:6333/collections | jq

# Информация о коллекции
curl http://localhost:6333/collections/test_col/info | jq

# Количество точек в коллекции
curl http://localhost:6333/collections/test_col | jq '.result.points_count'

# Удалить коллекцию (будьте осторожны!)
curl -X DELETE http://localhost:6333/collections/test_col

# Qdrant веб-интерфейс (если включен)
# http://localhost:6333/dashboard
```

## Git workflow

```powershell
# Проверить статус
git status

# Добавить все изменения
git add .

# Создать коммит
git commit -m "Feature: description or Fix: bug"

# Пушить на GitHub
git push origin main

# Создать новую ветку для фичи
git checkout -b feature/my-feature
# ... разработка ...
git commit -am "Add: feature"
git push origin feature/my-feature
# Затем создайте PR на GitHub

# Обновить main из GitHub
git pull origin main

# Откатиться на предыдущий коммит
git reset --hard HEAD~1
```

## Проблемы и их решения

```powershell
# Контейнер не запускается — смотрите логи
docker compose logs backend

# Горячая перезагрузка не работает
docker compose restart backend
# Убедитесь, что есть docker-compose.override.yml

# Память переполнена
docker system prune -a  # Осторожно! Удалит неиспользуемые образы

# Qdrant не отвечает
docker compose restart qdrant
docker compose logs qdrant

# Очистить кэш Python
rm -r backend/__pycache__
rm -r backend/.pytest_cache

# Переполнение диска
docker system df          # Посмотреть использование
docker system prune       # Очистить неиспользуемое
docker volume prune       # Очистить old volumes
```

## Переменные окружения

```powershell
# Изменить переменные окружения
# 1. Отредактируйте backend\.env
# 2. Перезагрузите контейнер:
docker compose restart backend

# Проверить переменные в контейнере
docker compose exec backend sh -c 'echo $OPENAI_API_KEY'
```

## Сборка собственного образа

```powershell
# Собрать образ вручную (обычно не требуется)
docker build -t my-backend:latest ./backend

# Тегировать образ
docker tag my-backend:latest my-backend:v1.0

# Отправить в registry (если нужно)
docker push registry.example.com/my-backend:latest
```

## Полезные одноличные команды

```powershell
# Все контейнеры остановить и очистить + пересобрать
docker compose down -v; docker compose up --build

# Проверить, что всё работает (все три сервиса)
docker compose ps; `
curl http://localhost:8081/api/health; `
curl http://localhost:6333/collections | jq '.status'

# Скопировать файл из контейнера на хост
docker compose cp backend:/app/app/ingest.py ./backend/app/

# Войти в bash контейнера backend (для отладки)
docker compose exec backend sh
# Внутри контейнера:
# python -c "import openai; print(openai.api_key)"
# curl http://qdrant:6333/collections
```

## Шпаргалка для prod сервера

```bash
# SSH на сервер
ssh user@test-domain.ru

# Быстрая проверка
docker compose ps
docker compose logs backend --tail 20

# Обновление с GitHub
cd /opt/iSdelal
git pull origin main
docker compose up --build -d

# Отката на старую версию
git log --oneline
git checkout commit-hash
docker compose up --build -d

# Очистка старых образов
docker system prune -a

# Просмотр использования памяти
docker stats

# Просмотр лога Qdrant
docker compose logs qdrant --tail 50
```

---

**Сохраняйте эту шпаргалку!** 🚀
