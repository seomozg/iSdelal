#!/usr/bin/env powershell
# Quick setup script for Windows
# Usage: .\setup.ps1

Write-Host "🚀 iSdelal RAG Kit - Setup Script" -ForegroundColor Cyan
Write-Host "=================================" -ForegroundColor Cyan
Write-Host ""

# Check if Docker is installed
Write-Host "✓ Checking Docker..." -ForegroundColor Yellow
if (!(Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host "✗ Docker not found! Please install Docker Desktop from https://www.docker.com/products/docker-desktop" -ForegroundColor Red
    exit 1
}
docker --version
Write-Host ""

# Check if Docker is running
Write-Host "✓ Checking if Docker is running..." -ForegroundColor Yellow
docker ps > $null 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ Docker is not running! Please start Docker Desktop." -ForegroundColor Red
    exit 1
}
Write-Host "Docker is running ✓" -ForegroundColor Green
Write-Host ""

# Check .env file
Write-Host "✓ Checking backend/.env..." -ForegroundColor Yellow
if (!(Test-Path "backend/.env")) {
    Write-Host "Creating backend/.env from .env.example..." -ForegroundColor Yellow
    Copy-Item "backend/.env.example" "backend/.env"
    Write-Host "✓ Created backend/.env" -ForegroundColor Green
    Write-Host ""
    Write-Host "⚠️  IMPORTANT: Edit backend/.env and set:" -ForegroundColor Yellow
    Write-Host "   - OPENAI_API_KEY=sk-... (your OpenAI API key)" -ForegroundColor Yellow
    Write-Host "   - API_KEY=... (strong random key for X-API-Key header)" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Then run: .\setup.ps1" -ForegroundColor Cyan
    exit 0
} else {
    Write-Host "✓ backend/.env exists" -ForegroundColor Green
}
Write-Host ""

# Ask for confirmation to start
Write-Host "Ready to start services?" -ForegroundColor Cyan
$response = Read-Host "Start docker compose? (y/n)"
if ($response -ne "y" -and $response -ne "Y") {
    Write-Host "Cancelled." -ForegroundColor Yellow
    exit 0
}

Write-Host ""
Write-Host "🐳 Starting Docker Compose..." -ForegroundColor Cyan
docker compose up --build

# Cleanup on exit
Write-Host ""
Write-Host "✓ Setup complete!" -ForegroundColor Green
Write-Host "Services are running on:" -ForegroundColor Green
Write-Host "  - Backend:  http://localhost:8000" -ForegroundColor Green
Write-Host "  - API:      http://localhost:8081/api/" -ForegroundColor Green
Write-Host "  - Qdrant:   http://localhost:6333/collections" -ForegroundColor Green
Write-Host ""
Write-Host "Test the API: curl http://localhost:8081/api/health" -ForegroundColor Green
Write-Host "View logs: docker compose logs -f backend" -ForegroundColor Green
