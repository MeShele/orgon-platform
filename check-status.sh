#!/bin/bash

# ORGON Status Check Script
# Quick health check for ORGON platform

echo "🔧 ORGON Platform Status Check"
echo "=============================="

# PM2 Status
echo "📦 PM2 Process Status:"
pm2 status

echo ""
echo "🌐 API Health Check:"
API_RESPONSE=$(curl -s localhost:8000/api/dashboard/stats)

if [ $? -eq 0 ]; then
    echo "✅ API is responding"
    echo "📊 Dashboard Stats:"
    echo "$API_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$API_RESPONSE"
else
    echo "❌ API is not responding"
fi

echo ""
echo "💾 Recent PM2 Logs (last 10 lines):"
pm2 logs orgon-backend --lines 10 --nostream

echo ""
echo "✅ Status check complete!"