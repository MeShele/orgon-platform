#!/bin/bash
# ORGON Status Check

echo "📊 ORGON Status Report"
echo "======================"
echo ""

# Check Backend
echo "🔧 Backend (uvicorn):"
BACKEND_PID=$(pgrep -f "uvicorn backend.main")
if [ ! -z "$BACKEND_PID" ]; then
    echo "   ✅ Running (PID: $BACKEND_PID)"
    curl -s -o /dev/null -w "   HTTP Status: %{http_code}\n" http://localhost:8890/docs
else
    echo "   ❌ Not running"
fi
echo ""

# Check Frontend
echo "🎨 Frontend (npm):"
FRONTEND_PID=$(pgrep -f "npm run dev")
if [ ! -z "$FRONTEND_PID" ]; then
    echo "   ✅ Running (PID: $FRONTEND_PID)"
    curl -s -o /dev/null -w "   HTTP Status: %{http_code}\n" http://localhost:3000
else
    echo "   ❌ Not running"
fi
echo ""

# Check Cloudflare Tunnel
echo "🌐 Cloudflare Tunnel:"
TUNNEL_PID=$(pgrep -f "cloudflared tunnel")
if [ ! -z "$TUNNEL_PID" ]; then
    echo "   ✅ Running (PID: $TUNNEL_PID)"
    curl -s -o /dev/null -w "   Public HTTPS Status: %{http_code}\n" https://orgon.asystem.ai
else
    echo "   ❌ Not running"
fi
echo ""

# Network Check
echo "🌍 Network:"
curl -s -o /dev/null -m 3 https://cloudflare.com
if [ $? -eq 0 ]; then
    echo "   ✅ Internet connected"
else
    echo "   ❌ No internet connection"
fi
echo ""

# Recent Errors
echo "⚠️  Recent errors (last 5):"
tail -n 100 backend.log 2>/dev/null | grep -i error | tail -5 || echo "   No errors found"
echo ""

echo "📝 Quick commands:"
echo "   Restart all: ./restart-all.sh"
echo "   View logs:   tail -f backend.log"
echo "   Public URL:  https://orgon.asystem.ai"
