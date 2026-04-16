#!/bin/bash
# Quick Start Script for ORGON Docker Deployment

set -e

echo "╔═══════════════════════════════════════════════════════════╗"
echo "║                                                           ║"
echo "║   🚀 ORGON Docker - Quick Start                         ║"
echo "║                                                           ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""

# Navigate to project directory
cd "$(dirname "$0")"

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker не запущен. Запуск Docker Desktop..."
    open -a Docker
    echo "⏳ Ожидание Docker Desktop (30 секунд)..."
    sleep 30
fi

# Check if images are built
if ! docker images | grep -q "orgon-backend"; then
    echo "🔨 Сборка Docker образов..."
    echo "⏳ Это займёт 5-10 минут при первом запуске..."
    docker-compose build
    echo "✅ Образы собраны!"
else
    echo "✅ Docker образы уже собраны"
fi

# Stop any running containers
echo "⏹️  Остановка запущенных контейнеров..."
docker-compose down 2>/dev/null || true

# Start containers
echo "🚀 Запуск контейнеров..."
docker-compose --env-file docker.env up -d

# Wait for health checks
echo "⏳ Ожидание health checks (30 секунд)..."
sleep 30

# Check status
echo ""
echo "📊 Статус контейнеров:"
docker-compose ps

echo ""
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║                                                           ║"
echo "║   ✅ ORGON запущен!                                      ║"
echo "║                                                           ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""
echo "🌐 Публичный доступ: https://orgon.asystem.ai"
echo "📊 Backend: http://localhost:8890"
echo "🎨 Frontend: http://localhost:3000"
echo ""
echo "📝 Логи: docker-compose logs -f"
echo "⏹️  Остановка: docker-compose down"
echo ""
