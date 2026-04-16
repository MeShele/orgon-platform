#!/bin/bash

# Aceternity UI Phase 3 - Manual Test Script
# Run this to verify all services are running

echo "==================================="
echo "Aceternity UI Phase 3 - Test Suite"
echo "==================================="
echo ""

# 1. Check Backend
echo "1. Checking Backend (port 8890)..."
if curl -s http://localhost:8890/api/health > /dev/null 2>&1; then
  echo "   ✅ Backend is running"
else
  echo "   ❌ Backend is NOT running"
fi
echo ""

# 2. Check Frontend
echo "2. Checking Frontend (port 3000)..."
if curl -s http://localhost:3000 > /dev/null 2>&1; then
  echo "   ✅ Frontend is running"
else
  echo "   ❌ Frontend is NOT running"
fi
echo ""

# 3. Check Production URL
echo "3. Checking Production (https://orgon.asystem.ai)..."
STATUS=$(curl -s -o /dev/null -w "%{http_code}" https://orgon.asystem.ai/)
if [ "$STATUS" -eq 200 ]; then
  echo "   ✅ Production is accessible (HTTP $STATUS)"
else
  echo "   ❌ Production returned HTTP $STATUS"
fi
echo ""

# 4. Check PM2 Status
echo "4. Checking PM2 Frontend Status..."
PM2_STATUS=$(pm2 jlist | jq -r '.[] | select(.name=="orgon-frontend") | .pm2_env.status')
if [ "$PM2_STATUS" = "online" ]; then
  PM2_PID=$(pm2 jlist | jq -r '.[] | select(.name=="orgon-frontend") | .pid')
  echo "   ✅ PM2 Frontend is online (PID $PM2_PID)"
else
  echo "   ❌ PM2 Frontend is $PM2_STATUS"
fi
echo ""

# 5. Check Cloudflare Tunnel
echo "5. Checking Cloudflare Tunnel..."
if pgrep -f "cloudflared tunnel" > /dev/null; then
  TUNNEL_PID=$(pgrep -f "cloudflared tunnel")
  echo "   ✅ Cloudflare Tunnel is running (PID $TUNNEL_PID)"
else
  echo "   ❌ Cloudflare Tunnel is NOT running"
fi
echo ""

# Manual Test Instructions
echo "==================================="
echo "Manual Testing Instructions:"
echo "==================================="
echo ""
echo "1. Dashboard (3D Stat Cards):"
echo "   - Navigate to https://orgon.asystem.ai/"
echo "   - Hover over stat cards"
echo "   - Verify 3D tilt effect (label/value lift at different depths)"
echo ""
echo "2. Analytics (Hover Border Charts):"
echo "   - Navigate to /analytics"
echo "   - Hover over charts"
echo "   - Verify animated gradient borders rotating around cards"
echo ""
echo "3. Login (Moving Border Buttons):"
echo "   - Navigate to /login"
echo "   - Observe Sign In button"
echo "   - Verify animated gradient border moving around button"
echo "   - Test 2FA step (if enabled)"
echo ""
echo "4. Contacts (Animated Modal + Inputs):"
echo "   - Navigate to /contacts"
echo "   - Click 'Add Contact' button"
echo "   - Test input focus animations:"
echo "     * Labels should float up smoothly"
echo "     * Blue glow should appear on focus"
echo "     * Icons should be visible on right side"
echo "   - Test favorite toggle (star animation)"
echo "   - Test submit button (moving border)"
echo "   - Test modal entrance (fade + scale)"
echo "   - Test Escape key to close"
echo "   - Test backdrop click to close"
echo ""
echo "5. Mobile Responsive:"
echo "   - Test on mobile device or browser dev tools"
echo "   - Verify all animations work on small screens"
echo "   - Check sidebar mobile overlay"
echo ""
echo "==================================="
echo "Test Credentials:"
echo "   Email: test@orgon.app"
echo "   Password: test1234"
echo "==================================="
