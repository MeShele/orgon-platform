#!/bin/bash
# ORGON Restart Script

echo "🔄 Restarting ORGON services..."

# Stop all services
echo "⏹️  Stopping services..."
pkill -f "uvicorn backend.main"
pkill -f "npm run dev"
pkill -f "cloudflared tunnel"

sleep 2

# Start Backend
echo "🚀 Starting Backend..."
cd /Users/urmatmyrzabekov/AGENT/ORGON
# Install/update dependencies if venv exists
if [ -d "backend/venv" ]; then
    source backend/venv/bin/activate
    pip install -q -r backend/requirements.txt > /dev/null 2>&1 || true
fi
nohup uvicorn backend.main:app --host 0.0.0.0 --port 8890 > backend.log 2>&1 &
BACKEND_PID=$!
echo "   Backend PID: $BACKEND_PID"

# Start Frontend
echo "🚀 Starting Frontend..."
cd /Users/urmatmyrzabekov/AGENT/ORGON/frontend
nohup npm run dev > frontend.log 2>&1 &
FRONTEND_PID=$!
echo "   Frontend PID: $FRONTEND_PID"

# Start Cloudflare Tunnel
echo "🚀 Starting Cloudflare Tunnel..."
cd /Users/urmatmyrzabekov/AGENT/ORGON
nohup cloudflared tunnel run --token eyJhIjoiMTlkMWFkMzBkY2VlNTY4Yjg2MmVlZTUwNTRkODc0YzYiLCJ0IjoiODFkOWY5MmEtZTBjNi00ZDg1LWE5OGMtOGRjNDdjNTVmMjQzIiwicyI6InNSb0MwY2FUaWZsWGp3VzJiRGthZlpSdVlHV1lEYnNQUmVjd2FBRnlWamM9In0= > cloudflared.log 2>&1 &
TUNNEL_PID=$!
echo "   Tunnel PID: $TUNNEL_PID"

echo ""
echo "✅ All services restarted!"
echo ""
echo "📊 Status:"
echo "   Backend:  http://localhost:8890"
echo "   Frontend: http://localhost:3000"
echo "   Public:   https://orgon.asystem.ai"
echo ""
echo "📝 Logs:"
echo "   Backend:  tail -f backend.log"
echo "   Frontend: tail -f frontend/frontend.log"
echo "   Tunnel:   tail -f cloudflared.log"
