# 🚀 START HERE - ORGON Docker Deployment

## ✅ Текущий статус

- ✅ Docker файлы созданы
- ✅ Cloudflare Tunnel Token добавлен в `docker.env`
- ✅ Конфигурация обновлена
- ✅ Локальные сервисы остановлены
- ✅ Docker Desktop запущен
- 🔨 Сборка Docker образов в процессе

---

## 🎯 Выберите вариант развертывания

### Вариант A: Быстрый старт (orgon.asystem.ai) - РЕКОМЕНДУЕТСЯ

✅ DNS уже настроен  
✅ Запуск за 5 минут  
✅ Работает сразу

```bash
cd /Users/urmatmyrzabekov/AGENT/ORGON

# 1. Переключитесь на orgon.asystem.ai
sed -i '' 's/orgon.asystem.kg/orgon.asystem.ai/g' docker.env
sed -i '' 's/orgon.asystem.kg/orgon.asystem.ai/g' config/orgon.yaml
sed -i '' 's/orgon.asystem.kg/orgon.asystem.ai/g' frontend/next.config.ts
sed -i '' 's/orgon.asystem.kg/orgon.asystem.ai/g' cloudflare-tunnel-config.yaml

# 2. Дождитесь завершения сборки (проверьте терминал)
# Или запустите сборку заново:
docker-compose build

# 3. Запустите контейнеры
docker-compose --env-file docker.env up -d

# 4. Проверьте статус
docker-compose ps

# 5. Откройте в браузере
open https://orgon.asystem.ai
```

---

### Вариант B: Новый домен (orgon.asystem.kg) - Требует настройки DNS

⚠️ Сначала настройте DNS в Cloudflare Dashboard

**1. Настройка DNS:**
1. Перейдите: https://dash.cloudflare.com/
2. Выберите домен: **asystem.kg**
3. DNS → Add record:
   - **Type:** CNAME
   - **Name:** `orgon`
   - **Target:** `81d9f92a-e0c6-4d85-a98c-8dc47c55f243.cfargotunnel.com`
   - **Proxy:** ✅ Enabled (оранжевое облако)
4. Save

**2. Проверьте DNS (подождите 1-2 минуты):**
```bash
dig orgon.asystem.kg CNAME +short
# Ожидается: 81d9f92a-e0c6-4d85-a98c-8dc47c55f243.cfargotunnel.com
```

**3. Запустите контейнеры:**
```bash
cd /Users/urmatmyrzabekov/AGENT/ORGON

# Дождитесь завершения сборки (проверьте терминал)
# Или запустите сборку заново:
docker-compose build

# Запустите
docker-compose --env-file docker.env up -d

# Проверьте статус
docker-compose ps

# Откройте в браузере
open https://orgon.asystem.kg
```

---

## 📊 Проверка статуса

### 1. Статус контейнеров

```bash
docker-compose ps
```

**Ожидается:**
```
NAME              STATUS
orgon-backend     Up X seconds (healthy)
orgon-frontend    Up X seconds (healthy)
orgon-tunnel      Up X seconds
```

### 2. Логи (если что-то не работает)

```bash
# Все сервисы
docker-compose logs -f

# Только backend
docker-compose logs -f backend

# Только frontend
docker-compose logs -f frontend

# Только tunnel
docker-compose logs -f cloudflared
```

### 3. Health checks

```bash
# Backend
curl http://localhost:8890/api/dashboard/stats

# Frontend
curl http://localhost:3000

# Публичный доступ (.ai или .kg в зависимости от выбранного варианта)
curl https://orgon.asystem.ai
curl https://orgon.asystem.ai/api/dashboard/stats
```

---

## 🐛 Troubleshooting

### "Сборка ещё не завершилась"

```bash
# Проверьте процесс
ps aux | grep "docker-compose build"

# Дождитесь завершения или запустите заново
docker-compose build
```

### "Контейнеры не запускаются"

```bash
# Проверьте логи
docker-compose logs backend
docker-compose logs frontend

# Проверьте переменные окружения
grep CLOUDFLARE_TUNNEL_TOKEN docker.env
grep DATABASE_URL docker.env
```

### "Tunnel error 530"

Причины:
1. DNS не настроен (для .kg)
2. Контейнеры не healthy
3. Неправильный токен

Решение:
```bash
# Проверьте DNS (для .kg)
dig orgon.asystem.kg CNAME +short

# Проверьте health checks
docker-compose ps

# Проверьте логи tunnel
docker-compose logs cloudflared
```

### "Cannot connect to Docker daemon"

```bash
# Запустите Docker Desktop
open -a Docker

# Подождите 30 секунд и попробуйте снова
sleep 30
docker ps
```

---

## 🎯 Что должно работать после запуска

### Локально:
- ✅ Backend: http://localhost:8890/api/dashboard/stats
- ✅ Frontend: http://localhost:3000

### Публично (после настройки DNS):
- ✅ Сайт: https://orgon.asystem.ai (или .kg)
- ✅ API: https://orgon.asystem.ai/api/dashboard/stats

---

## 📚 Дополнительная документация

- **Полное руководство:** `DOCKER_DEPLOYMENT.md`
- **DNS настройка:** `DNS_SETUP_REQUIRED.md`
- **Использовать .ai:** `USE_EXISTING_DOMAIN.md`
- **Команды:** `COMMANDS.sh`
- **Статус:** `DEPLOYMENT_STATUS.md`

---

## ✅ Быстрый checklist

- [ ] Docker Desktop запущен
- [ ] Сборка образов завершена (`docker-compose build`)
- [ ] Домен выбран (.ai рекомендуется для быстрого старта)
- [ ] DNS настроен (если используете .kg)
- [ ] Контейнеры запущены (`docker-compose --env-file docker.env up -d`)
- [ ] Все контейнеры healthy (`docker-compose ps`)
- [ ] Сайт открывается (https://orgon.asystem.ai или .kg)

---

## 🚀 Рекомендуемая последовательность

```bash
# 1. Перейдите в директорию проекта
cd /Users/urmatmyrzabekov/AGENT/ORGON

# 2. Переключитесь на .ai (быстрый старт)
sed -i '' 's/orgon.asystem.kg/orgon.asystem.ai/g' docker.env config/orgon.yaml frontend/next.config.ts cloudflare-tunnel-config.yaml

# 3. Соберите образы (если ещё не собраны)
docker-compose build

# 4. Запустите контейнеры
docker-compose --env-file docker.env up -d

# 5. Проверьте статус
docker-compose ps

# 6. Откройте сайт
open https://orgon.asystem.ai
```

**Готово! 🎉**

---

## 📞 Поддержка

Если что-то не работает:
1. Проверьте логи: `docker-compose logs -f`
2. Проверьте статус: `docker-compose ps`
3. См. раздел Troubleshooting выше
4. См. полную документацию в `DOCKER_DEPLOYMENT.md`

**Удачи! 🚀**
