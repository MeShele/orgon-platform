# 🌐 DNS Setup Required for orgon.asystem.kg

## ⚠️ Важно: Настройте DNS перед запуском Docker

Туннель настроен, но для домена **orgon.asystem.kg** нужно добавить DNS запись в Cloudflare.

---

## Tunnel Information

**Tunnel ID:** `81d9f92a-e0c6-4d85-a98c-8dc47c55f243`  
**Tunnel Token:** ✅ Уже добавлен в `docker.env`  
**Target Domain:** `orgon.asystem.kg`

---

## 📋 Шаги настройки DNS

### Вариант 1: Cloudflare Dashboard (рекомендуется)

1. Перейдите в **Cloudflare Dashboard**: https://dash.cloudflare.com/
2. Выберите домен **asystem.kg**
3. Перейдите в раздел **DNS**
4. Нажмите **Add record**
5. Заполните:
   - **Type:** CNAME
   - **Name:** `orgon`
   - **Target:** `81d9f92a-e0c6-4d85-a98c-8dc47c55f243.cfargotunnel.com`
   - **Proxy status:** ✅ Proxied (оранжевое облако)
   - **TTL:** Auto
6. Нажмите **Save**

### Вариант 2: Cloudflare API (если есть полный доступ)

```bash
# Получите Zone ID для asystem.kg
ZONE_ID=$(curl -s -X GET "https://api.cloudflare.com/client/v4/zones?name=asystem.kg" \
  -H "Authorization: Bearer YOUR_API_TOKEN" | jq -r '.result[0].id')

# Добавьте CNAME запись
curl -X POST "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/dns_records" \
  -H "Authorization: Bearer YOUR_API_TOKEN" \
  -H "Content-Type: application/json" \
  --data '{
    "type": "CNAME",
    "name": "orgon",
    "content": "81d9f92a-e0c6-4d85-a98c-8dc47c55f243.cfargotunnel.com",
    "ttl": 1,
    "proxied": true
  }' | jq '.'
```

---

## ✅ Проверка DNS

После добавления DNS записи (подождите 1-2 минуты):

```bash
# Проверка CNAME
dig orgon.asystem.kg CNAME +short
# Ожидается: 81d9f92a-e0c6-4d85-a98c-8dc47c55f243.cfargotunnel.com

# Проверка A записи (через Cloudflare Proxy)
dig orgon.asystem.kg A +short
# Ожидаются Cloudflare IP адреса (104.x.x.x или 172.x.x.x)

# Проверка доступности
curl -I https://orgon.asystem.kg
# Ожидается: HTTP/2 200 (после запуска Docker контейнеров)
```

---

## 🐳 После настройки DNS

Когда DNS настроен, запустите Docker контейнеры:

```bash
cd /Users/urmatmyrzabekov/AGENT/ORGON

# Сборка образов
docker-compose build

# Запуск всех сервисов
docker-compose --env-file docker.env up -d

# Проверка статуса
docker-compose ps

# Проверка логов
docker-compose logs -f
```

Или используйте Makefile:

```bash
make -f Makefile.docker build
make -f Makefile.docker up
make -f Makefile.docker status
```

---

## 🔍 Проверка работы

```bash
# Статус контейнеров (должны быть healthy)
docker-compose ps

# Health checks
make -f Makefile.docker health

# Публичный доступ
curl https://orgon.asystem.kg

# API endpoint
curl https://orgon.asystem.kg/api/dashboard/stats
```

---

## 🐛 Troubleshooting

### DNS не резолвится

```bash
# Проверка
dig orgon.asystem.kg CNAME +short

# Если пусто - запись не добавлена или не пропагировалась
# Подождите 1-2 минуты и проверьте снова
```

### Tunnel показывает 530 error

Причины:
1. DNS не настроен (см. выше)
2. Docker контейнеры не запущены
3. Health checks не прошли

Решение:
```bash
# Проверьте контейнеры
docker-compose ps

# Все должны быть Up и healthy
# Если нет - проверьте логи
docker-compose logs backend
docker-compose logs frontend
```

---

## 📝 Альтернатива: Использовать orgon.asystem.ai

Если не хотите настраивать новый домен, можете использовать существующий **orgon.asystem.ai**:

1. Обновите `docker.env`:
   ```env
   PUBLIC_DOMAIN=orgon.asystem.ai
   CORS_ORIGINS=https://orgon.asystem.ai,http://localhost:3000
   ```

2. Обновите `frontend/next.config.ts`:
   ```typescript
   env: {
     NEXT_PUBLIC_API_URL: 'https://orgon.asystem.ai/api',
   },
   ```

3. Обновите `config/orgon.yaml`:
   ```yaml
   cors_origins:
     - "https://orgon.asystem.ai"
   ```

4. Обновите `cloudflare-tunnel-config.yaml`:
   ```yaml
   - hostname: orgon.asystem.ai
   ```

5. Пересоберите и перезапустите:
   ```bash
   docker-compose build --no-cache
   docker-compose up -d
   ```

---

## ✅ Готово к запуску?

Checklist:
- [ ] DNS CNAME настроен в Cloudflare
- [ ] DNS пропагировался (dig показывает cfargotunnel.com)
- [ ] Docker Desktop запущен
- [ ] `docker.env` заполнен (CLOUDFLARE_TUNNEL_TOKEN уже добавлен)
- [ ] PostgreSQL доступна (Neon.tech)

Если всё готово:
```bash
make -f Makefile.docker build
make -f Makefile.docker up
```

**Удачи! 🚀**
