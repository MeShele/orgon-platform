#!/bin/bash
# Check Docker build status

echo "╔═══════════════════════════════════════════════════════════╗"
echo "║   📊 Проверка статуса сборки Docker образов             ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""

# Check if build process is running
if ps aux | grep -q "[d]ocker-compose build"; then
    echo "🔨 Сборка в процессе..."
    echo ""
    echo "📝 Последние строки из build.log:"
    tail -n 20 build.log 2>/dev/null || echo "Логи ещё не созданы"
else
    echo "✅ Процесс сборки не запущен"
fi

echo ""
echo "─────────────────────────────────────────────────────────────"
echo ""

# Check if images are built
echo "📦 Проверка собранных образов:"
if docker images | grep -q "orgon"; then
    docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}" | grep -E "REPOSITORY|orgon"
    echo ""
    echo "✅ Образы собраны!"
    echo ""
    echo "🚀 Следующий шаг: Запустите контейнеры"
    echo "   ./quick-start.sh"
else
    echo "⏳ Образы ещё не собраны"
    echo ""
    echo "💡 Если сборка не идёт, запустите:"
    echo "   docker-compose build"
fi

echo ""
echo "─────────────────────────────────────────────────────────────"
echo ""

# Check if containers are running
echo "🐳 Статус контейнеров:"
if docker-compose ps 2>/dev/null | grep -q "orgon"; then
    docker-compose ps
else
    echo "⏹️  Контейнеры не запущены"
    echo ""
    echo "💡 Для запуска после сборки:"
    echo "   ./quick-start.sh"
fi

echo ""
