#!/bin/bash

# Deploy script for test-domain.ru
echo "🚀 Starting deployment to test-domain.ru..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if we're in the right directory
if [ ! -f "docker-compose.yml" ]; then
    print_error "docker-compose.yml not found. Are you in the project root?"
    exit 1
fi

# Pull latest changes
print_status "Pulling latest changes from git..."
git pull origin main

if [ $? -ne 0 ]; then
    print_error "Failed to pull from git"
    exit 1
fi

# Stop containers
print_status "Stopping existing containers..."
docker compose down

# Build and start containers in correct order
print_status "Starting Qdrant..."
docker compose up -d qdrant
sleep 5

print_status "Starting Backend..."
docker compose up --build -d backend
sleep 10

print_status "Starting Nginx..."
docker compose up --build -d nginx
sleep 5

if [ $? -ne 0 ]; then
    print_error "Failed to start containers"
    exit 1
fi

# Wait for services to start
print_status "Waiting for services to be ready..."
sleep 5

# Check backend health
print_status "Checking backend health..."
if curl -f -s https://test-domain.ru/health > /dev/null; then
    print_status "✅ Backend is healthy!"
else
    print_warning "⚠️  Backend health check failed, but services might still be starting..."
fi

# Check if nginx is responding
print_status "Checking nginx..."
if curl -f -s -I https://test-domain.ru/ | head -1 | grep "200\|301" > /dev/null; then
    print_status "✅ Nginx is responding!"
else
    print_error "❌ Nginx is not responding properly"
    exit 1
fi

print_status "🎉 Deployment completed successfully!"
print_status "🌐 Your site should be available at: https://test-domain.ru"
print_status "📊 Admin interface: https://test-domain.ru/frontend/"
print_status "🤖 Widget assets: https://test-domain.ru/widget/"

# Show container status
echo ""
print_status "Container status:"
docker compose ps
