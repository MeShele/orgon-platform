# 🔄 Альтернатива: Использовать существующий домен orgon.asystem.ai

Если не хотите настраивать DNS для **orgon.asystem.kg**, можете использовать существующий домен **orgon.asystem.ai**.

---

## ✅ Преимущества

- DNS уже настроен
- Работает с текущим Cloudflare Tunnel
- Не требуется дополнительная настройка DNS
- Быстрый запуск (5 минут)

---

## 📝 Шаги переключения

### 1. Обновите docker.env

```bash
cd /Users/urmatmyrzabekov/AGENT/ORGON
nano docker.env
```

Измените:
```env
# Domain Configuration
PUBLIC_DOMAIN=orgon.asystem.ai
CORS_ORIGINS=https://orgon.asystem.ai,http://localhost:3000
```

### 2. Обновите config/orgon.yaml

```bash
nano config/orgon.yaml
```

Измените `cors_origins`:
```yaml
server:
  host: "0.0.0.0"
  port: 8890
  debug: false
  cors_origins:
    - "http://localhost:3000"
    - "http://127.0.0.1:3000"
    - "https://orgon.asystem.ai"  # Основной домен
    - "http://frontend:3000"      # Docker internal
```

### 3. Обновите frontend/next.config.ts

```bash
nano frontend/next.config.ts
```

Измените:
```typescript
  // Environment variables
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'https://orgon.asystem.ai/api',
  },
```

### 4. Обновите cloudflare-tunnel-config.yaml

```bash
nano cloudflare-tunnel-config.yaml
```

Измените все `hostname: orgon.asystem.kg` на `hostname: orgon.asystem.ai`:
```yaml
ingress:
  # API endpoints to backend
  - hostname: orgon.asystem.ai
    path: /api/*
    service: http://backend:8890
    
  # WebSocket endpoints
  - hostname: orgon.asystem.ai
    path: /ws/*
    service: http://backend:8890
      
  # Frontend (Next.js)
  - hostname: orgon.asystem.ai
    service: http://frontend:3000
      
  # Catch-all (404)
  - service: http_status:404
```

### 5. Пересоберите и запустите

```bash
# Остановите текущие контейнеры (если запущены)
docker-compose down

# Пересоберите образы
docker-compose build --no-cache

# Запустите с новой конфигурацией
docker-compose --env-file docker.env up -d

# Проверьте статус
docker-compose ps
```

### 6. Проверьте работу

```bash
# Проверка DNS (уже настроен)
dig orgon.asystem.ai A +short

# Проверка доступности
curl https://orgon.asystem.ai

# Проверка API
curl https://orgon.asystem.ai/api/dashboard/stats
```

---

## 🎯 Полная команда для переключения

```bash
cd /Users/urmatmyrzabekov/AGENT/ORGON

# 1. Обновите docker.env
sed -i '' 's/orgon.asystem.kg/orgon.asystem.ai/g' docker.env

# 2. Обновите config/orgon.yaml
sed -i '' 's/orgon.asystem.kg/orgon.asystem.ai/g' config/orgon.yaml

# 3. Обновите frontend/next.config.ts
sed -i '' 's/orgon.asystem.kg/orgon.asystem.ai/g' frontend/next.config.ts

# 4. Обновите cloudflare-tunnel-config.yaml
sed -i '' 's/orgon.asystem.kg/orgon.asystem.ai/g' cloudflare-tunnel-config.yaml

# 5. Пересоберите и запустите
docker-compose down
docker-compose build --no-cache
docker-compose --env-file docker.env up -d

# 6. Проверьте статус
docker-compose ps
make -f Makefile.docker health
```

---

## ✅ Checklist

После переключения:
- [ ] Все файлы обновлены (4 файла)
- [ ] Docker образы пересобраны
- [ ] Контейнеры запущены и healthy
- [ ] https://orgon.asystem.ai открывается
- [ ] https://orgon.asystem.ai/api/dashboard/stats возвращает JSON

---

## 🔄 Возврат к orgon.asystem.kg

Если позже захотите вернуться к **orgon.asystem.kg**:

```bash
cd /Users/urmatmyrzabekov/AGENT/ORGON

# Замените обратно
sed -i '' 's/orgon.asystem.ai/orgon.asystem.kg/g' docker.env
sed -i '' 's/orgon.asystem.ai/orgon.asystem.kg/g' config/orgon.yaml
sed -i '' 's/orgon.asystem.ai/orgon.asystem.kg/g' frontend/next.config.ts
sed -i '' 's/orgon.asystem.ai/orgon.asystem.kg/g' cloudflare-tunnel-config.yaml

# Не забудьте настроить DNS для orgon.asystem.kg!
# См. DNS_SETUP_REQUIRED.md

# Пересоберите
docker-compose build --no-cache
docker-compose --env-file docker.env up -d
```

---

## 🎯 Рекомендация

**Для быстрого старта:** Используйте **orgon.asystem.ai** (DNS уже настроен)

**Для production:** Настройте DNS для **orgon.asystem.kg** (см. `DNS_SETUP_REQUIRED.md`)

Оба варианта работают идентично, разница только в домене.

---

## 📞 Поддержка

Если используете orgon.asystem.ai и возникли проблемы:
1. Проверьте, что DNS резолвится: `dig orgon.asystem.ai A +short`
2. Проверьте контейнеры: `docker-compose ps`
3. Проверьте логи: `docker-compose logs -f`

**Домен работает:** https://orgon.asystem.ai ✅
