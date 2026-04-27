# CORS Fix - 2026-02-06

## Проблема

Frontend (https://orgon.asystem.ai) пытался обращаться к `http://localhost:8890/api` из браузера, что блокировалось CORS политикой:

```
Access to fetch at 'http://localhost:8890/api/dashboard/stats' 
from origin 'https://orgon.asystem.ai' has been blocked by CORS policy: 
Permission was denied for this request to access the loopback address space.
```

## Решение

### 1. Cloudflare Tunnel — Проксирование Backend

Обновил конфигурацию туннеля для проксирования `/api/*` на backend:

```json
{
  "ingress": [
    {
      "hostname": "orgon.asystem.ai",
      "path": "/api/*",
      "service": "http://localhost:8890"
    },
    {
      "hostname": "orgon.asystem.ai",
      "service": "http://localhost:3000"
    },
    {
      "service": "http_status:404"
    }
  ]
}
```

**Теперь:**
- `https://orgon.asystem.ai/api/*` → `localhost:8890`
- `https://orgon.asystem.ai/*` → `localhost:3000`

### 2. Frontend — Относительные пути API

Обновил `frontend/.env.local`:

```bash
# Было:
NEXT_PUBLIC_API_URL=http://localhost:8890

# Стало (пустая строка = relative paths):
NEXT_PUBLIC_API_URL=
```

Теперь `api.ts` использует относительные пути:
- `fetch('/api/dashboard/stats')` вместо `fetch('http://localhost:8890/api/dashboard/stats')`

### 3. Backend CORS — Добавил orgon.asystem.ai

Обновил `config/orgon.yaml`:

```yaml
server:
  cors_origins:
    - "http://localhost:3000"
    - "http://127.0.0.1:3000"
    - "https://orgon.asystem.ai"  # <-- добавлено
```

### 4. Перезапуск сервисов

```bash
# Backend
pkill -f "uvicorn backend.main"
cd /Users/urmatmyrzabekov/AGENT/ORGON
source venv/bin/activate
nohup uvicorn backend.main:app --host 0.0.0.0 --port 8890 > backend.log 2>&1 &

# Frontend
pkill -f "npm run dev"
cd /Users/urmatmyrzabekov/AGENT/ORGON/frontend
nohup npm run dev > frontend.log 2>&1 &
```

## Проверка

```bash
# CORS preflight
curl -X OPTIONS https://orgon.asystem.ai/api/dashboard/stats \
  -H "Origin: https://orgon.asystem.ai" \
  -H "Access-Control-Request-Method: GET" \
  -i

# Ответ:
HTTP/1.1 200 OK
access-control-allow-origin: https://orgon.asystem.ai
access-control-allow-methods: DELETE, GET, HEAD, OPTIONS, PATCH, POST, PUT
access-control-allow-credentials: true
```

## Результат

✅ Frontend теперь делает запросы к `/api/*` (relative paths)  
✅ Cloudflare tunnel проксирует `/api/*` на backend  
✅ Backend разрешает CORS для `https://orgon.asystem.ai`  
✅ Все API endpoints работают без ошибок CORS

## Тестирование

```bash
# Dashboard stats
curl -s 'https://orgon.asystem.ai/api/dashboard/stats' \
  -H 'Origin: https://orgon.asystem.ai'
# ✅ {"total_wallets":4,"total_balance_usd":"0.00",...}

# Dashboard overview
curl -s 'https://orgon.asystem.ai/api/dashboard/overview' \
  -H 'Origin: https://orgon.asystem.ai'
# ✅ {"wallet_count":1,"total_tokens":4,...}

# Health check
curl -s https://orgon.asystem.ai/api/health
# ✅ {"status":"ok","service":"orgon",...}
```

## PIDs после fix

- Backend: 5928
- Frontend: 5768
- Cloudflare Tunnel: 4741 (не перезапускали — конфиг обновился автоматически)

---

**Время исправления:** 6 минут  
**Статус:** ✅ Решено  
**Ответственный:** ASAGENT
