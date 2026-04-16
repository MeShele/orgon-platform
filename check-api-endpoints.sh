#!/bin/bash
# Check API endpoints health

echo "╔═══════════════════════════════════════════════════════════╗"
echo "║   🔍 Проверка API Endpoints                              ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""

BASE_URL="https://orgon.asystem.ai"

check_endpoint() {
    local endpoint=$1
    local name=$2
    
    echo -n "Проверка $name... "
    
    response=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL$endpoint" 2>/dev/null)
    
    if [ "$response" = "200" ]; then
        echo "✅ OK (HTTP $response)"
        return 0
    else
        echo "❌ FAIL (HTTP $response)"
        return 1
    fi
}

echo "═══════════════════════════════════════════════════════════"
echo "🌐 Backend API:"
echo "═══════════════════════════════════════════════════════════"

check_endpoint "/api/dashboard/stats" "Dashboard Stats"
check_endpoint "/api/wallets" "Wallets"
check_endpoint "/api/transactions" "Transactions"
check_endpoint "/api/networks" "Networks"
check_endpoint "/api/signatures/pending" "Pending Signatures"
check_endpoint "/api/signatures/history" "Signature History"
check_endpoint "/api/dashboard/alerts" "Dashboard Alerts"

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "🎨 Frontend:"
echo "═══════════════════════════════════════════════════════════"

check_endpoint "/" "Homepage"

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "🔌 WebSocket:"
echo "═══════════════════════════════════════════════════════════"

# Test WebSocket endpoint (will fail with 400 for HTTP GET, but means it's alive)
response=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/ws/updates" 2>/dev/null)

if [ "$response" = "400" ] || [ "$response" = "426" ]; then
    echo "✅ WebSocket endpoint alive (HTTP $response - expected for GET)"
elif [ "$response" = "200" ]; then
    echo "✅ WebSocket endpoint alive (HTTP $response)"
else
    echo "❌ WebSocket endpoint not responding (HTTP $response)"
fi

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "📊 Итог:"
echo "═══════════════════════════════════════════════════════════"
echo "Проверка завершена. Все endpoint'ы проверены."
echo ""
