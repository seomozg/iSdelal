# Production Deployment Guide - test-domain.ru

## 🚀 Быстрое Развертывание

### На сервере (test-domain.ru):

```bash
# 1. Установите зависимости
sudo apt update && sudo apt install -y docker.io docker-compose-plugin git certbot python3-certbot-nginx

# 2. Клонируйте проект
cd /opt
git clone https://github.com/yourusername/iSdelal.git
cd iSdelal

# 3. Настройте переменные окружения
cd backend
cp .env.example .env
nano .env  # Добавьте ваши API ключи

# 4. Получите SSL сертификат
cd ..
sudo certbot certonly --standalone -d test-domain.ru -d www.test-domain.ru

# 5. Запустите сервисы ПО ПОРЯДКУ
docker compose up -d qdrant
sleep 5
docker compose up --build -d backend
sleep 10
docker compose up --build -d nginx

# 6. Проверьте работу
curl https://test-domain.ru/health
curl https://test-domain.ru/frontend/
```

## 🔧 Конфигурация для test-domain.ru

### DNS Настройки
Убедитесь, что ваш домен указывает на IP сервера:
```
test-domain.ru     A     YOUR_SERVER_IP
www.test-domain.ru CNAME test-domain.ru
```

### Nginx Конфигурация
Автоматически настроена для:
- ✅ HTTPS с Let's Encrypt
- ✅ Проксирование API к backend
- ✅ Статические файлы widget и frontend
- ✅ HTTP → HTTPS редирект

### API Endpoints
Все endpoints доступны без префикса `/api/`:
```
https://test-domain.ru/health
https://test-domain.ru/chat
https://test-domain.ru/ingest
https://test-domain.ru/collections
https://test-domain.ru/frontend/
https://test-domain.ru/widget/
```

## 🔐 Безопасность

### API Ключи
- **OPENAI_API_KEY**: Ваш ключ от OpenAI
- **API_KEY**: Сгенерируйте случайный ключ для аутентификации

```bash
# Генерация безопасного API ключа:
openssl rand -hex 32
```

### SSL/TLS
- Автоматические сертификаты Let's Encrypt
- Автоматическое обновление каждые 90 дней

## 📊 Мониторинг

### Проверка Работоспособности
```bash
# Статус сервисов
docker compose ps

# Логи
docker compose logs -f backend
docker compose logs -f nginx

# Проверка API
curl https://test-domain.ru/health
```

### Резервные Копии
```bash
# Qdrant данные
docker compose exec qdrant tar czf /qdrant/backup/qdrant_$(date +%Y%m%d).tar.gz /qdrant/storage

# Полная резервная копия
docker run --rm -v qdrant_storage:/data -v $(pwd)/backup:/backup alpine tar czf /backup/full_backup.tar.gz /data
```

## 🔄 Обновления

### Автоматический Деплой
Используйте `deploy.sh`:
```bash
chmod +x deploy.sh
./deploy.sh
```

### Ручное Обновление
```bash
git pull origin main
docker compose up --build -d
```

## 🆘 Troubleshooting

### 502 Bad Gateway ошибка
```bash
# Проверьте статус контейнеров
docker compose ps

# Если backend не запущен:
docker compose up -d backend
sleep 5

# Проверьте логи backend
docker compose logs backend

# Проверьте внутреннюю связь
docker compose exec nginx curl -f http://backend:8000/health

# Перезапустите все сервисы по порядку
docker compose down
docker compose up -d qdrant && sleep 5
docker compose up --build -d backend && sleep 10
docker compose up --build -d nginx
```

### Сервис не запускается
```bash
# Проверьте логи
docker compose logs backend

# Проверьте переменные окружения
docker compose exec backend env | grep -E "(OPENAI|API_KEY)"

# Проверьте .env файл
cd backend && cat .env
```

### Nginx не может найти backend
```bash
# Проверьте Docker сеть
docker network ls
docker network inspect isdelal_app_network

# Перезапустите с новой сетью
docker compose down
docker compose up --build -d
```

### SSL проблемы
```bash
# Продлить сертификаты
sudo certbot renew
docker compose restart nginx

# Проверьте сертификаты
ls -la /etc/letsencrypt/live/test-domain.ru/
```

### DNS проблемы
```bash
# Проверьте DNS
nslookup test-domain.ru

# Проверьте сертификат
openssl s_client -connect test-domain.ru:443 -servername test-domain.ru
```

### Очистка и перезапуск
```bash
# Полная очистка
docker compose down -v
docker system prune -a

# Перезапуск
docker compose up --build -d
```

## 📞 Поддержка

При проблемах:
1. Проверьте логи: `docker compose logs`
2. Проверьте здоровье: `curl https://test-domain.ru/health`
3. Проверьте SSL: `openssl s_client -connect test-domain.ru:443`

---

**🎉 Готово! Ваш RAG сервис доступен на https://test-domain.ru**
