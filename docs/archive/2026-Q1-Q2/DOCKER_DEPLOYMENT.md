# 🐳 Docker Deployment для ORGON

## Структура

```
ORGON/
├── Dockerfile.backend           # Backend (Python/FastAPI)
├── Dockerfile.frontend          # Frontend (Next.js)
├── docker-compose.yml           # Оркестрация всех сервисов
├── docker.env                   # Переменные окружения
├── cloudflare-tunnel-config.yaml # Конфигурация туннеля
└── config/orgon.yaml            # Конфигурация backend
```

## Предварительная настройка

### 1. Cloudflare Tunnel

#### Создание туннеля (если ещё нет)
```bash
# Авторизация
cloudflared tunnel login

# Создание туннеля
cloudflared tunnel create orgon

# Получите tunnel ID и token из вывода
```

#### Настройка DNS
В Cloudflare Dashboard:
1. Перейдите в **DNS** для домена `asystem.kg`
2. Добавьте CNAME запись:
   - **Type:** CNAME
   - **Name:** orgon
   - **Target:** <TUNNEL_ID>.cfargotunnel.com
   - **Proxy status:** Proxied (оранжевое облако)

#### Получение токена туннеля
```bash
# Вариант 1: Cloudflare Dashboard
# Zero Trust > Access > Tunnels > orgon > Configure > Copy token

# Вариант 2: CLI (если есть credentials.json)
cat ~/.cloudflared/<TUNNEL_ID>.json
```

### 2. Обновите docker.env

```bash
cd /Users/urmatmyrzabekov/AGENT/ORGON
nano docker.env
```

Замените:
```env
CLOUDFLARE_TUNNEL_TOKEN=<YOUR_TUNNEL_TOKEN_HERE>
```

На реальный токен из Cloudflare.

### 3. Обновите cloudflare-tunnel-config.yaml (опционально)

Если используете config-based tunnel (не token):
```bash
nano cloudflare-tunnel-config.yaml
```

Замените `<TUNNEL_ID>` на реальный ID туннеля.

## Сборка и запуск

### Вариант 1: С token (рекомендуется)

```bash
cd /Users/urmatmyrzabekov/AGENT/ORGON

# Сборка образов
docker-compose build

# Запуск всех сервисов
docker-compose --env-file docker.env up -d

# Проверка логов
docker-compose logs -f
```

### Вариант 2: С config file

Обновите `docker-compose.yml`:
```yaml
cloudflared:
  image: cloudflare/cloudflared:latest
  container_name: orgon-tunnel
  restart: unless-stopped
  command: tunnel --config /etc/cloudflared/config.yaml run
  volumes:
    - ./cloudflare-tunnel-config.yaml:/etc/cloudflared/config.yaml:ro
    - ./cloudflared-credentials.json:/etc/cloudflared/credentials.json:ro
  networks:
    - orgon-network
```

## Проверка работы

### 1. Статус контейнеров
```bash
docker-compose ps
```

Все 3 сервиса должны быть `Up` и `healthy`:
```
NAME                STATUS              PORTS
orgon-backend       Up 2 minutes (healthy)
orgon-frontend      Up 2 minutes (healthy)
orgon-tunnel        Up 2 minutes
```

### 2. Логи
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

### 3. Проверка API
```bash
# Backend напрямую (внутри Docker)
docker exec orgon-backend curl http://localhost:8890/api/dashboard/stats

# Frontend напрямую
docker exec orgon-frontend wget -qO- http://localhost:3000

# Через tunnel (публичный доступ)
curl https://orgon.asystem.kg/api/dashboard/stats
```

### 4. Проверка DNS
```bash
# Проверка CNAME
dig orgon.asystem.kg CNAME +short

# Проверка доступности
curl -I https://orgon.asystem.kg
```

## Управление

### Перезапуск сервисов
```bash
# Все сервисы
docker-compose restart

# Только backend
docker-compose restart backend

# Только frontend
docker-compose restart frontend
```

### Остановка
```bash
# Остановка
docker-compose stop

# Остановка и удаление контейнеров
docker-compose down

# Остановка и удаление контейнеров + volumes
docker-compose down -v
```

### Обновление образов
```bash
# Пересборка после изменений
docker-compose build --no-cache

# Перезапуск с новыми образами
docker-compose up -d
```

### Логи
```bash
# Последние 100 строк
docker-compose logs --tail=100

# Live streaming
docker-compose logs -f

# Экспорт логов
docker-compose logs > orgon-logs.txt
```

## Мониторинг

### Health checks
```bash
# Backend
curl http://localhost:8890/api/dashboard/stats

# Frontend
curl http://localhost:3000

# Tunnel metrics (если включен в config)
curl http://localhost:2000/metrics
```

### Статистика ресурсов
```bash
# CPU/RAM usage
docker stats orgon-backend orgon-frontend orgon-tunnel

# Disk usage
docker system df
```

## Troubleshooting

### Backend не запускается
```bash
# Проверка логов
docker-compose logs backend

# Подключение к контейнеру
docker exec -it orgon-backend bash

# Проверка БД
docker exec -it orgon-backend python -c "import asyncpg; print('OK')"
```

### Frontend ошибка 500
```bash
# Проверка логов
docker-compose logs frontend

# Проверка переменных окружения
docker exec orgon-frontend env | grep NEXT_PUBLIC

# Пересборка без кэша
docker-compose build --no-cache frontend
docker-compose up -d frontend
```

### Tunnel ошибка 530
Причины:
1. **Неправильный токен** - проверьте CLOUDFLARE_TUNNEL_TOKEN в docker.env
2. **DNS не настроен** - добавьте CNAME в Cloudflare DNS
3. **Сервисы не готовы** - дождитесь health check:
   ```bash
   docker-compose ps
   # Все должны быть "healthy"
   ```

### Сеть
```bash
# Проверка сети
docker network inspect orgon_orgon-network

# Проверка связности между контейнерами
docker exec orgon-frontend ping -c 3 backend
docker exec orgon-tunnel ping -c 3 frontend
```

## Production Checklist

- [ ] Cloudflare Tunnel создан и активен
- [ ] DNS CNAME запись настроена (orgon.asystem.kg)
- [ ] docker.env заполнен реальными значениями
- [ ] PostgreSQL доступна (Neon.tech)
- [ ] Safina API ключ валиден
- [ ] CORS настроен для orgon.asystem.kg
- [ ] Health checks проходят успешно
- [ ] Логи не содержат ошибок
- [ ] https://orgon.asystem.kg открывается
- [ ] https://orgon.asystem.kg/api/dashboard/stats возвращает JSON

## Миграция с локального развертывания

### 1. Остановите локальные сервисы
```bash
cd /Users/urmatmyrzabekov/AGENT/ORGON
./restart-all.sh stop  # Если есть такой скрипт
# Или вручную:
pkill -f "uvicorn backend.main"
pkill -f "node.*next"
pkill -f cloudflared
```

### 2. Запустите Docker
```bash
docker-compose --env-file docker.env up -d
```

### 3. Проверьте работу
```bash
# Статус
docker-compose ps

# Логи (30 секунд)
timeout 30 docker-compose logs -f

# Доступность
curl https://orgon.asystem.kg
```

### 4. Настройте автозапуск (опционально)
```bash
# Создайте systemd service (Linux) или launchd (macOS)
# Или используйте restart: unless-stopped в docker-compose.yml (уже настроено)
```

## Бэкап и восстановление

### База данных (PostgreSQL на Neon.tech)
Нет необходимости - Neon.tech делает автоматические бэкапы.

### Конфигурация
```bash
# Бэкап
tar -czf orgon-config-backup-$(date +%Y%m%d).tar.gz \
  docker-compose.yml \
  docker.env \
  Dockerfile.* \
  config/ \
  cloudflare-tunnel-config.yaml

# Восстановление
tar -xzf orgon-config-backup-YYYYMMDD.tar.gz
```

## Безопасность

1. **Не коммитьте docker.env** в Git (уже в .gitignore)
2. **Храните CLOUDFLARE_TUNNEL_TOKEN в секрете**
3. **Используйте переменные окружения** для всех секретов
4. **Регулярно обновляйте образы**:
   ```bash
   docker-compose pull
   docker-compose up -d
   ```

## Дополнительные ресурсы

- [Cloudflare Tunnel Docs](https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/)
- [Next.js Docker Docs](https://nextjs.org/docs/deployment#docker-image)
- [FastAPI Docker Docs](https://fastapi.tiangolo.com/deployment/docker/)
