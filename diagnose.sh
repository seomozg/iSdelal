#!/bin/bash

# Diagnostic script for test-domain.ru
echo "🔍 Диагностика системы test-domain.ru"
echo "========================================"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_status() {
    echo -e "${GREEN}✅${NC} $1"
}

print_error() {
    echo -e "${RED}❌${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠️${NC} $1"
}

echo ""
echo "1. Проверка статуса контейнеров:"
echo "---------------------------------"
docker compose ps

echo ""
echo "2. Проверка сетей Docker:"
echo "-------------------------"
docker network ls | grep isdelal

echo ""
echo "3. Проверка внутренней связи:"
echo "------------------------------"

# Test nginx to backend connection
if docker compose exec -T nginx curl -f -s http://backend:8000/health > /dev/null 2>&1; then
    print_status "Nginx может подключиться к backend"
else
    print_error "Nginx НЕ может подключиться к backend"
fi

# Test backend internal health
if docker compose exec -T backend curl -f -s http://localhost:8000/health > /dev/null 2>&1; then
    print_status "Backend отвечает на health check"
else
    print_error "Backend НЕ отвечает на health check"
fi

echo ""
echo "4. Проверка внешней доступности:"
echo "----------------------------------"

# Test external health
if curl -f -s -k https://test-domain.ru/health > /dev/null 2>&1; then
    print_status "Внешний health check работает"
else
    print_error "Внешний health check НЕ работает"
fi

# Test frontend
if curl -f -s -k https://test-domain.ru/frontend/ > /dev/null 2>&1; then
    print_status "Frontend доступен"
else
    print_warning "Frontend НЕ доступен"
fi

echo ""
echo "5. Проверка переменных окружения:"
echo "-----------------------------------"
echo "OPENAI_API_KEY:"
docker compose exec -T backend env | grep OPENAI_API_KEY | cut -d'=' -f1
echo ""
echo "API_KEY:"
docker compose exec -T backend env | grep API_KEY | cut -d'=' -f1

echo ""
echo "6. Последние логи backend:"
echo "---------------------------"
docker compose logs --tail 10 backend

echo ""
echo "7. Последние логи nginx:"
echo "-------------------------"
docker compose logs --tail 5 nginx

echo ""
echo "========================================"
echo "Диагностика завершена"
echo ""
echo "Если есть проблемы:"
echo "- Запустите: docker compose restart"
echo "- Или: ./deploy.sh"
echo "- Проверьте логи подробнее: docker compose logs -f backend"
