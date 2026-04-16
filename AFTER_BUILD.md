# ⏳ Сборка Docker образов в процессе

## Текущий статус:

🔨 **Сборка запущена** - загрузка базовых образов Python 3.14 и Node 20

⏱️ **Ожидаемое время:** 5-10 минут (в зависимости от скорости интернета)

---

## После завершения сборки:

### 1. Проверьте, что образы собраны:

```bash
docker images | grep orgon
```

**Ожидается:**
```
orgon-backend     latest   <image_id>   X minutes ago   XXX MB
orgon-frontend    latest   <image_id>   X minutes ago   XXX MB
```

---

### 2. Запустите контейнеры:

#### Вариант A: Используйте quick-start.sh (рекомендуется)

```bash
cd /Users/urmatmyrzabekov/AGENT/ORGON
./quick-start.sh
```

#### Вариант B: Вручную через docker-compose

```bash
cd /Users/urmatmyrzabekov/AGENT/ORGON
docker-compose --env-file docker.env up -d
```

#### Вариант C: Через Makefile

```bash
cd /Users/urmatmyrzabekov/AGENT/ORGON
make -f Makefile.docker up
```

---

### 3. Проверьте статус контейнеров:

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

---

### 4. Проверьте логи:

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

### 5. Проверьте доступность:

#### Локально:

```bash
# Backend
curl http://localhost:8890/api/dashboard/stats

# Frontend
curl http://localhost:3000
```

#### Публично:

```bash
# Сайт
curl https://orgon.asystem.ai

# API
curl https://orgon.asystem.ai/api/dashboard/stats
```

**Или откройте в браузере:** https://orgon.asystem.ai

---

## 🐛 Если что-то не работает:

### Сборка завершилась с ошибкой:

```bash
# Проверьте логи
cat build.log

# Пересоберите
docker-compose build --no-cache
```

### Контейнеры не запускаются:

```bash
# Проверьте логи
docker-compose logs backend
docker-compose logs frontend

# Проверьте переменные окружения
grep CLOUDFLARE_TUNNEL_TOKEN docker.env
grep DATABASE_URL docker.env
```

### Tunnel показывает 530 error:

```bash
# Проверьте health checks (должны быть "healthy")
docker-compose ps

# Проверьте логи tunnel
docker-compose logs cloudflared

# Проверьте сеть между контейнерами
docker exec orgon-frontend ping -c 3 backend
```

### Backend/Frontend не отвечают:

```bash
# Проверьте, что контейнеры работают
docker-compose ps

# Перезапустите
docker-compose restart

# Проверьте логи
docker-compose logs -f
```

---

## ✅ Что должно работать после запуска:

- ✅ Backend: http://localhost:8890/api/dashboard/stats
- ✅ Frontend: http://localhost:3000
- ✅ Публичный доступ: https://orgon.asystem.ai
- ✅ API: https://orgon.asystem.ai/api/dashboard/stats

---

## 📊 Полезные команды:

```bash
# Статус контейнеров
docker-compose ps

# Логи (live)
docker-compose logs -f

# Перезапуск
docker-compose restart

# Остановка
docker-compose stop

# Остановка и удаление
docker-compose down

# Health checks
make -f Makefile.docker health

# Статистика ресурсов
docker stats orgon-backend orgon-frontend orgon-tunnel
```

---

## 📚 Документация:

- **START_HERE.md** - Начните здесь
- **DOCKER_QUICKSTART.md** - Quick start
- **DOCKER_DEPLOYMENT.md** - Полное руководство
- **COMMANDS.sh** - Справочник команд

---

## 🎯 Следующие шаги:

1. ✅ Дождитесь завершения сборки
2. ✅ Запустите контейнеры (./quick-start.sh)
3. ✅ Проверьте статус (docker-compose ps)
4. ✅ Откройте в браузере (https://orgon.asystem.ai)

**Готово! 🚀**
