#!/bin/bash

# Quick health check for test-domain.ru
echo "🏥 Health Check - test-domain.ru"
echo "================================"

# Check containers
echo "Containers:"
docker compose ps --format "table {{.Name}}\t{{.Status}}"

echo ""
echo "Services:"

# Backend health
if curl -f -s -k https://test-domain.ru/health > /dev/null 2>&1; then
    echo "✅ Backend: OK"
else
    echo "❌ Backend: FAILED"
fi

# Frontend
if curl -f -s -k https://test-domain.ru/frontend/ > /dev/null 2>&1; then
    echo "✅ Frontend: OK"
else
    echo "❌ Frontend: FAILED"
fi

# Widget
if curl -f -s -k https://test-domain.ru/widget/widget.js > /dev/null 2>&1; then
    echo "✅ Widget: OK"
else
    echo "❌ Widget: FAILED"
fi

echo ""
echo "================================"
