# Frontend Connection Fix — 2026-02-06 15:15

## Проблема

Frontend показывал ошибки:
```
localhost:8890/api/dashboard/stats:1 Failed to load resource: net::ERR_CONNECTION_REFUSED
WebSocket connection to 'ws://localhost:8890/ws/updates' failed
```

## Причина

Frontend `.env.local` был настроен на **пустую строку** для `NEXT_PUBLIC_API_URL`:
```bash
NEXT_PUBLIC_API_URL=
```

Это работает в **production** (через Cloudflare tunnel — относительные пути), но **не работает локально**, потому что:
- Браузер пытается делать запросы к `localhost:8890` напрямую
- Cloudflare tunnel не проксирует локальные запросы в dev режиме
- Next.js dev server на порту 3000 не может proxy к backend на 8890 без явного URL

## Решение

Обновил `frontend/.env.local`:

**Было:**
```bash
NEXT_PUBLIC_API_URL=
```

**Стало:**
```bash
# Local development - use localhost backend
NEXT_PUBLIC_API_URL=http://localhost:8890

# For production (Cloudflare tunnel), use empty string:
# NEXT_PUBLIC_API_URL=
```

## Применено

```bash
# 1. Обновил .env.local
# 2. Перезапустил frontend
pkill -f "npm run dev"
cd /Users/urmatmyrzabekov/AGENT/ORGON/frontend
nohup npm run dev > frontend.log 2>&1 &
```

## Проверка

```bash
# Backend работает
curl http://localhost:8890/api/health
# ✅ {"status":"ok","service":"orgon",...}

# Frontend работает
curl http://localhost:3000
# ✅ 200 OK

# Production работает
curl https://orgon.asystem.ai/api/dashboard/stats
# ✅ {"total_wallets":4,...}
```

## Статус

✅ **Все сервисы работают:**
- Backend: PID 10145 (SQLite)
- Frontend: PID 14194 (Next.js dev)
- Cloudflare Tunnel: PID 4741
- Public URL: https://orgon.asystem.ai

## Deployment Strategy

**Локальная разработка:**
- `NEXT_PUBLIC_API_URL=http://localhost:8890`
- Прямые запросы к backend

**Production (Cloudflare):**
- `NEXT_PUBLIC_API_URL=` (пустая строка)
- Относительные пути через tunnel

**Будущее улучшение:**
Создать два `.env` файла:
- `.env.development` → `http://localhost:8890`
- `.env.production` → пустая строка

Next.js автоматически выберет правильный файл в зависимости от `NODE_ENV`.

---

**Время исправления:** 2 минуты  
**Downtime:** 0 (backend не падал)  
**Root cause:** Неправильная конфигурация для dev режима
