# 🚀 Docker Quick Start для ORGON

## Быстрый старт (5 минут)

### 1. Настройка Cloudflare Tunnel

#### Получите токен туннеля:

**Вариант A: Использовать существующий туннель**
```bash
# Если tunnel уже создан, получите токен из Cloudflare Dashboard:
# Zero Trust > Access > Tunnels > orgon > Configure > Copy token
```

**Вариант B: Создать новый туннель**
```bash
# Установите cloudflared (если ещё нет)
brew install cloudflare/cloudflare/cloudflared  # macOS
# или
wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64
sudo mv cloudflared-linux-amd64 /usr/local/bin/cloudflared
sudo chmod +x /usr/local/bin/cloudflared

# Авторизация
cloudflared tunnel login

# Создание туннеля
cloudflared tunnel create orgon

# Запишите tunnel ID и создайте токен:
cloudflared tunnel token orgon
```

### 2. Настройка DNS в Cloudflare

1. Перейдите в **Cloudflare Dashboard** → **DNS** для домена `asystem.kg`
2. Добавьте CNAME запись:
   - **Type:** CNAME
   - **Name:** orgon
   - **Target:** `<TUNNEL_ID>.cfargotunnel.com` (из вывода выше)
   - **Proxy status:** ✅ Proxied (оранжевое облако)
3. Нажмите **Save**

### 3. Обновите docker.env

```bash
cd /Users/urmatmyrzabekov/AGENT/ORGON
nano docker.env
```

Замените строку:
```env
CLOUDFLARE_TUNNEL_TOKEN=<YOUR_TUNNEL_TOKEN_HERE>
```

На реальный токен из шага 1.

### 4. Запустите Docker

```bash
# Сборка и запуск (впервые ~5-10 минут)
make -f Makefile.docker up

# Или напрямую через docker-compose:
docker-compose --env-file docker.env up -d
```

### 5. Проверьте работу

```bash
# Статус контейнеров
make -f Makefile.docker status

# Health checks
make -f Makefile.docker health

# Проверка публичного доступа
curl https://orgon.asystem.kg
```

**Ожидаемый результат:**
```
📊 Services Status:
NAME              STATUS              PORTS
orgon-backend     Up 2 minutes (healthy)
orgon-frontend    Up 2 minutes (healthy)
orgon-tunnel      Up 2 minutes

🔍 Backend health: ✅ OK
🔍 Frontend health: ✅ OK
🔍 Public access: ✅ OK
```

### 6. Откройте в браузере

Перейдите на: **https://orgon.asystem.kg**

---

## Управление

### Просмотр логов
```bash
# Все сервисы
make -f Makefile.docker logs

# Только backend
make -f Makefile.docker logs-backend

# Только frontend
make -f Makefile.docker logs-frontend
```

### Перезапуск
```bash
make -f Makefile.docker restart
```

### Остановка
```bash
make -f Makefile.docker down
```

### Обновление кода
```bash
# После изменений в коде:
make -f Makefile.docker rebuild
make -f Makefile.docker up
```

---

## Troubleshooting

### ❌ "Tunnel error 530"

**Причина:** Cloudflare Tunnel не может подключиться к сервисам.

**Решение:**
1. Проверьте токен в `docker.env`:
   ```bash
   grep CLOUDFLARE_TUNNEL_TOKEN docker.env
   ```
2. Проверьте health checks:
   ```bash
   docker-compose ps
   ```
   Все должны быть `healthy`.
3. Проверьте логи туннеля:
   ```bash
   docker-compose logs cloudflared
   ```

### ❌ "Backend not accessible"

**Причина:** Backend контейнер не запустился.

**Решение:**
```bash
# Проверьте логи
docker-compose logs backend

# Проверьте переменные окружения
docker exec orgon-backend env | grep DATABASE_URL

# Перезапустите
docker-compose restart backend
```

### ❌ "Frontend shows 500 error"

**Причина:** Frontend не может подключиться к backend.

**Решение:**
1. Проверьте сеть между контейнерами:
   ```bash
   docker exec orgon-frontend ping -c 3 backend
   ```
2. Проверьте переменные окружения:
   ```bash
   docker exec orgon-frontend env | grep NEXT_PUBLIC_API_URL
   ```
3. Пересоберите frontend:
   ```bash
   docker-compose build --no-cache frontend
   docker-compose up -d frontend
   ```

### ❌ "DNS не резолвится"

**Причина:** CNAME запись не настроена или не пропагировалась.

**Решение:**
```bash
# Проверьте DNS
dig orgon.asystem.kg CNAME +short

# Если пусто, добавьте CNAME в Cloudflare Dashboard
# Подождите 1-2 минуты для пропагации

# Проверьте снова
dig orgon.asystem.kg CNAME +short
# Должно показать: <TUNNEL_ID>.cfargotunnel.com
```

---

## Миграция с локального развертывания

Если у вас сейчас работают локальные сервисы:

```bash
# Остановите локальные сервисы
make -f Makefile.docker migrate

# Это остановит локальные процессы и запустит Docker
```

---

## Полезные команды

```bash
# Все доступные команды
make -f Makefile.docker help

# Статус ресурсов
make -f Makefile.docker stats

# Тест API
make -f Makefile.docker test-api

# Бэкап конфигурации
make -f Makefile.docker backup-config

# Shell в контейнер
make -f Makefile.docker shell-backend
make -f Makefile.docker shell-frontend
```

---

## Что дальше?

После успешного запуска:

1. ✅ Проверьте работу дашборда: https://orgon.asystem.kg
2. ✅ Проверьте API: https://orgon.asystem.kg/api/dashboard/stats
3. ✅ Настройте автозапуск (docker-compose уже использует `restart: unless-stopped`)
4. ✅ Настройте мониторинг (опционально)

Документация: `DOCKER_DEPLOYMENT.md`
