# Деплой на test-domain.ru

## Подготовка сервера (первый раз)

### 1. SSH на сервер
```bash
ssh user@test-domain.ru
```

### 2. Установите Docker & Docker Compose
```bash
# Если Ubuntu/Debian:
sudo apt-get update
sudo apt-get install -y docker.io docker-compose-plugin git

# Добавьте пользователя в группу docker
sudo usermod -aG docker $USER
newgrp docker

# Проверьте установку:
docker --version
docker compose version
```

### 3. Клонируйте репозиторий
```bash
cd /opt  # или другая директория
git clone https://github.com/yourusername/iSdelal.git
cd iSdelal
```

### 4. Создайте `.env` с правильными значениями
```bash
cd backend
cp .env.example .env
# Отредактируйте:
nano .env
# Установите:
# - OPENAI_API_KEY=sk-...
# - API_KEY=ваш-сильный-секрет-из-генератора
cd ..
```

### 5. Настройте HTTPS (Let's Encrypt + Certbot)
```bash
sudo apt-get install -y certbot python3-certbot-nginx

# Получить сертификат (остановите сначала nginx контейнер)
docker compose down nginx
sudo certbot certonly --standalone -d test-domain.ru -d www.test-domain.ru

# Сертификаты будут в: /etc/letsencrypt/live/test-domain.ru/
```

### 6. Обновите `nginx/default.conf`
```nginx
# Добавьте SSL блок:
server {
    listen 443 ssl http2;
    server_name test-domain.ru www.test-domain.ru;

    ssl_certificate /etc/letsencrypt/live/test-domain.ru/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/test-domain.ru/privkey.pem;
    
    # ... остальная конфигурация ...
}

# Редирект HTTP → HTTPS
server {
    listen 80;
    server_name test-domain.ru www.test-domain.ru;
    return 301 https://$server_name$request_uri;
}
```

### 7. Монтируйте сертификаты в docker-compose.yml
```yaml
nginx:
  volumes:
    - ./widget:/usr/share/nginx/html/widget:ro
    - /etc/letsencrypt/live/test-domain.ru:/etc/nginx/certs:ro
```

### 8. Первый запуск
```bash
docker compose up --build -d

# Проверьте логи
docker compose logs -f backend
docker compose logs -f qdrant
```

## Регулярный деплой (обновления)

### На локальной машине:
```powershell
# Разработайте, протестируйте
git add .
git commit -m "Feature: description"
git push origin main
```

### На сервере (test-domain.ru):
```bash
cd /opt/iSdelal

# Получите последние изменения
git pull origin main

# Перестройте контейнеры
docker compose up --build -d

# Проверьте здоровье
curl https://test-domain.ru/api/health

# Просмотрите логи (если нужно)
docker compose logs backend
```

## Автоматический деплой (Optional - GitHub Actions)

### 1. Создайте Deploy Key на GitHub
```bash
ssh-keygen -t ed25519 -C "github-actions" -f ~/.ssh/github-deploy
# Скопируйте публичный ключ на сервер в ~/.ssh/authorized_keys
```

### 2. Добавьте приватный ключ как GitHub Secret
```
Settings → Secrets → DEPLOY_KEY = <содержимое приватного ключа>
```

### 3. Создайте `.github/workflows/deploy.yml`
```yaml
name: Deploy to test-domain.ru

on:
  push:
    branches: [ main ]

jobs:
  deploy:
    runs-on: ubuntu-latest
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Deploy to server
      uses: appleboy/ssh-action@master
      with:
        host: test-domain.ru
        username: deploy_user
        key: ${{ secrets.DEPLOY_KEY }}
        script: |
          cd /opt/iSdelal
          git pull origin main
          docker compose up --build -d
          docker compose logs backend | head -20
```

## Мониторинг и обслуживание

### Регулярные проверки:
```bash
# Статус контейнеров
docker compose ps

# Логи backend
docker compose logs -f backend

# Использование дискового пространства
docker system df

# Очистка старых образов/контейнеров
docker system prune -a

# Обновление сертификатов (раз в месяц)
sudo certbot renew --quiet
```

### Резервные копии Qdrant:
```bash
# Qdrant данные хранятся в volume qdrant_storage
# Регулярная резервная копия:
docker compose exec qdrant tar czf /backup/qdrant_$(date +%Y%m%d_%H%M%S).tar.gz /qdrant/storage

# Или просто синхронизируйте в облако:
docker run --rm -v qdrant_storage:/data -v /backup:/backup \
  alpine tar czf /backup/qdrant_backup.tar.gz /data
```

## Откатитесь на предыдущую версию (если нужно)

```bash
cd /opt/iSdelal

# Посмотрите историю
git log --oneline

# Откатитесь на конкретный коммит
git checkout <commit-hash>
docker compose up --build -d

# Или вернитесь на main
git checkout main
git pull
docker compose up --build -d
```

## Troubleshooting

**API не отвечает:**
```bash
docker compose logs backend
curl -v https://test-domain.ru/api/health
```

**Qdrant не подключается:**
```bash
docker compose logs qdrant
docker compose exec backend curl http://qdrant:6333/collections
```

**Память или диск переполнены:**
```bash
docker system df
docker system prune -a  # Осторожно! Удалит неиспользуемые образы

# Очистить logs:
docker compose logs --tail 0 -f backend > /dev/null
```

**Сертификат истёк:**
```bash
sudo certbot renew
docker compose restart nginx
```

---

## Быстрая команда для полного деплоя

```bash
#!/bin/bash
cd /opt/iSdelal
git pull origin main
docker compose down
docker compose up --build -d
sleep 5
curl https://test-domain.ru/api/health
echo "Deploy complete!"
```

Сохраните как `deploy.sh` и запускайте: `bash deploy.sh`
