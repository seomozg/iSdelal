#!/bin/bash
# Quick setup script for Linux/Mac
# Usage: bash setup.sh

set -e

echo "🚀 iSdelal RAG Kit - Setup Script"
echo "================================="
echo ""

# Check if Docker is installed
echo "✓ Checking Docker..."
if ! command -v docker &> /dev/null; then
    echo "✗ Docker not found! Please install Docker from https://docs.docker.com/get-docker/"
    exit 1
fi
docker --version
echo ""

# Check if Docker Compose is installed
echo "✓ Checking Docker Compose..."
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "✗ Docker Compose not found! Please install Docker Compose."
    exit 1
fi
docker compose version
echo ""

# Check if Docker daemon is running
echo "✓ Checking if Docker daemon is running..."
if ! docker ps &> /dev/null; then
    echo "✗ Docker daemon is not running! Please start Docker."
    exit 1
fi
echo "Docker is running ✓"
echo ""

# Check .env file
echo "✓ Checking backend/.env..."
if [ ! -f "backend/.env" ]; then
    echo "Creating backend/.env from .env.example..."
    cp backend/.env.example backend/.env
    echo "✓ Created backend/.env"
    echo ""
    echo "⚠️  IMPORTANT: Edit backend/.env and set:"
    echo "   - OPENAI_API_KEY=sk-... (your OpenAI API key)"
    echo "   - API_KEY=... (strong random key for X-API-Key header)"
    echo ""
    echo "Then run: bash setup.sh"
    exit 0
else
    echo "✓ backend/.env exists"
fi
echo ""

# Ask for confirmation
echo "Ready to start services?"
read -p "Start docker compose? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled."
    exit 0
fi

echo ""
echo "🐳 Starting Docker Compose..."
docker compose up --build

# Show info on exit
echo ""
echo "✓ Setup complete!"
echo "Services are running on:"
echo "  - Backend:  http://localhost:8000"
echo "  - API:      http://localhost:8081/api/"
echo "  - Qdrant:   http://localhost:6333/collections"
echo ""
echo "Test the API: curl http://localhost:8081/api/health"
echo "View logs: docker compose logs -f backend"
