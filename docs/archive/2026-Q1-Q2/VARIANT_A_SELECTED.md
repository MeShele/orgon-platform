# ✅ Вариант A выбран: orgon.asystem.ai

## 🎯 Текущий статус

### ✅ Что сделано:

1. ✅ Конфигурация переключена на **orgon.asystem.ai**
2. ✅ DNS уже настроен (Cloudflare)
3. ✅ Cloudflare Tunnel Token добавлен
4. ✅ Docker Desktop запущен
5. 🔨 **Сборка Docker образов в процессе**

### Изменённые файлы:

- ✅ `docker.env` - orgon.asystem.ai
- ✅ `config/orgon.yaml` - orgon.asystem.ai
- ✅ `frontend/next.config.ts` - orgon.asystem.ai
- ✅ `cloudflare-tunnel-config.yaml` - orgon.asystem.ai

---

## ⏳ Сейчас: Сборка Docker образов

**Процесс:**
1. Загрузка Python 3.14 (backend)
2. Загрузка Node 20 (frontend)
3. Установка зависимостей
4. Сборка Next.js приложения
5. Создание production образов

**Время:** ~5-10 минут (в зависимости от скорости интернета)

**Прогресс:** Можно проверить командой:
```bash
tail -f build.log
```

---

## 🚀 После завершения сборки

### Шаг 1: Проверьте, что образы собраны

```bash
cd /Users/urmatmyrzabekov/AGENT/ORGON
docker images | grep orgon
```

**Ожидается:**
```
orgon-backend     latest   <image_id>   X minutes ago   XXX MB
orgon-frontend    latest   <image_id>   X minutes ago   XXX MB
```

---

### Шаг 2: Запустите контейнеры

#### Вариант 1: Автоматический запуск (рекомендуется)

```bash
./quick-start.sh
```

Этот скрипт:
- Проверит Docker
- Остановит старые контейнеры (если есть)
- Запустит новые контейнеры
- Покажет статус

#### Вариант 2: Вручную через docker-compose

```bash
docker-compose --env-file docker.env up -d
```

#### Вариант 3: Через Makefile

```bash
make -f Makefile.docker up
```

---

### Шаг 3: Проверьте статус контейнеров

```bash
docker-compose ps
```

**Ожидается:**
```
NAME              STATUS
orgon-backend     Up X seconds (healthy) ✅
orgon-frontend    Up X seconds (healthy) ✅
orgon-tunnel      Up X seconds ✅
```

**Важно:** Подождите ~30 секунд для прохождения health checks!

---

### Шаг 4: Проверьте логи (если нужно)

```bash
# Все сервисы (live)
docker-compose logs -f

# Только backend
docker-compose logs -f backend

# Только frontend
docker-compose logs -f frontend

# Только tunnel
docker-compose logs -f cloudflared
```

---

### Шаг 5: Откройте в браузере

**Публичный доступ:**
```
https://orgon.asystem.ai
```

**API endpoint:**
```
https://orgon.asystem.ai/api/dashboard/stats
```

**Локальный доступ (для проверки):**
- Backend: http://localhost:8890
- Frontend: http://localhost:3000

---

## ✅ Проверка работоспособности

### Быстрая проверка:

```bash
# Health checks
make -f Makefile.docker health
```

### Детальная проверка:

```bash
# 1. Backend локально
curl http://localhost:8890/api/dashboard/stats

# Ожидается: JSON с данными кошельков

# 2. Frontend локально
curl http://localhost:3000

# Ожидается: HTML страница

# 3. Публичный доступ
curl https://orgon.asystem.ai

# Ожидается: HTML страница (не 530 error!)

# 4. API через публичный домен
curl https://orgon.asystem.ai/api/dashboard/stats

# Ожидается: JSON с данными
```

---

## 🐛 Troubleshooting

### Контейнеры не запускаются

```bash
# Проверьте логи
docker-compose logs backend
docker-compose logs frontend

# Проверьте переменные окружения
grep CLOUDFLARE_TUNNEL_TOKEN docker.env
grep DATABASE_URL docker.env

# Перезапустите
docker-compose restart
```

### Tunnel показывает 530 error

**Причины:**
1. Контейнеры не healthy (подождите 30 секунд)
2. Health checks не прошли
3. Сеть между контейнерами не работает

**Решение:**
```bash
# Проверьте health checks
docker-compose ps

# Все должны быть "healthy"
# Если нет - проверьте логи
docker-compose logs backend
docker-compose logs frontend

# Проверьте сеть
docker exec orgon-frontend ping -c 3 backend
```

### Backend/Frontend не отвечают

```bash
# Перезапустите контейнеры
docker-compose restart

# Проверьте логи
docker-compose logs -f

# Проверьте, что БД доступна
docker exec orgon-backend python -c "import asyncpg; print('OK')"
```

---

## 📊 Архитектура

```
Internet
    ↓
Cloudflare CDN
    ↓
Cloudflare Tunnel (81d9f92a-e0c6-4d85-a98c-8dc47c55f243)
    ↓
Docker Network (orgon-network)
    ├── Backend:8890 → PostgreSQL (Neon.tech)
    ├── Frontend:3000 → Backend:8890
    └── Tunnel → routes to backend/frontend

Routing:
https://orgon.asystem.ai/      → Frontend
https://orgon.asystem.ai/api/* → Backend
https://orgon.asystem.ai/ws/*  → Backend WebSocket
```

---

## 📝 Полезные команды

```bash
# Статус
docker-compose ps

# Логи
docker-compose logs -f

# Перезапуск
docker-compose restart

# Остановка
docker-compose stop

# Полная остановка и удаление
docker-compose down

# Health checks
make -f Makefile.docker health

# Статистика ресурсов
docker stats orgon-backend orgon-frontend orgon-tunnel

# Shell в контейнер
docker exec -it orgon-backend bash
docker exec -it orgon-frontend sh
```

---

## 🎉 Ожидаемый результат

После успешного запуска:

```bash
$ docker-compose ps

NAME              STATUS
orgon-backend     Up 2 minutes (healthy)
orgon-frontend    Up 2 minutes (healthy)
orgon-tunnel      Up 2 minutes

$ curl -s https://orgon.asystem.ai/api/dashboard/stats | jq '.total_wallets'
4

$ open https://orgon.asystem.ai
# Открывается ORGON Dashboard ✅
```

---

## 📞 Поддержка

Если что-то не работает:
1. Проверьте этот документ (раздел Troubleshooting)
2. Проверьте `START_HERE.md`
3. Проверьте `DOCKER_DEPLOYMENT.md` → Troubleshooting
4. Проверьте логи: `docker-compose logs -f`

---

## ✅ Checklist

- [x] Вариант A выбран (orgon.asystem.ai)
- [x] Конфигурация обновлена
- [x] Docker Desktop запущен
- [ ] Сборка образов завершена ⏳ **Ожидается**
- [ ] Контейнеры запущены (`./quick-start.sh`)
- [ ] Все контейнеры healthy (`docker-compose ps`)
- [ ] Сайт открывается (https://orgon.asystem.ai)
- [ ] API работает

---

**Следующий шаг:** Дождитесь завершения сборки и запустите `./quick-start.sh`

**Удачи! 🚀**
