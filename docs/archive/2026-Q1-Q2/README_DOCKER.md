# 🐳 ORGON Docker Deployment

**Wallet Management Dashboard** на Docker с Cloudflare Tunnel

## 🎯 Что внутри

- **Backend:** FastAPI + Python 3.14 + PostgreSQL (Neon.tech)
- **Frontend:** Next.js 15 + React 19 + TypeScript
- **Tunnel:** Cloudflare Tunnel для публичного доступа
- **Домен:** orgon.asystem.kg

## 📦 Структура

```
ORGON/
├── Dockerfile.backend           # Backend container
├── Dockerfile.frontend          # Frontend container
├── docker-compose.yml           # Orchestration
├── docker.env                   # Environment variables (не коммитится)
├── cloudflare-tunnel-config.yaml # Tunnel routing
├── Makefile.docker              # Management commands
├── DOCKER_QUICKSTART.md         # Quick start guide
└── DOCKER_DEPLOYMENT.md         # Full documentation
```

## 🚀 Quick Start

### 1. Установите Docker

```bash
# macOS
brew install docker docker-compose

# Linux
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
```

### 2. Настройте Cloudflare Tunnel

```bash
# Создайте tunnel (если ещё нет)
cloudflared tunnel create orgon

# Получите токен
cloudflared tunnel token orgon

# Настройте DNS CNAME в Cloudflare:
# orgon.asystem.kg → <TUNNEL_ID>.cfargotunnel.com
```

### 3. Обновите docker.env

```bash
nano docker.env
# Замените CLOUDFLARE_TUNNEL_TOKEN на реальный токен
```

### 4. Запустите

```bash
# Сборка и запуск
make -f Makefile.docker up

# Или
docker-compose --env-file docker.env up -d
```

### 5. Проверьте

```bash
# Статус
make -f Makefile.docker status

# Health checks
make -f Makefile.docker health

# Откройте в браузере
open https://orgon.asystem.kg
```

## 📚 Документация

- **Quick Start:** `DOCKER_QUICKSTART.md` - начните здесь!
- **Full Guide:** `DOCKER_DEPLOYMENT.md` - подробная документация
- **Troubleshooting:** см. `DOCKER_QUICKSTART.md` или `DOCKER_DEPLOYMENT.md`

## 🛠 Управление

```bash
# Все команды
make -f Makefile.docker help

# Основные:
make -f Makefile.docker up        # Запустить
make -f Makefile.docker down      # Остановить
make -f Makefile.docker restart   # Перезапустить
make -f Makefile.docker logs      # Логи
make -f Makefile.docker status    # Статус
make -f Makefile.docker health    # Health checks
```

## 🔒 Безопасность

- ❗ Не коммитьте `docker.env` (уже в `.gitignore`)
- ❗ Храните `CLOUDFLARE_TUNNEL_TOKEN` в секрете
- ✅ Используйте переменные окружения для всех секретов
- ✅ Регулярно обновляйте образы: `make -f Makefile.docker update`

## 📊 Архитектура

```
Internet → Cloudflare → Tunnel → Docker Network
                                      ├── Backend:8890
                                      ├── Frontend:3000
                                      └── Tunnel
```

### Routing

- `orgon.asystem.kg/` → Frontend (Next.js)
- `orgon.asystem.kg/api/*` → Backend (FastAPI)
- `orgon.asystem.kg/ws/*` → Backend WebSocket

## 🐛 Troubleshooting

### "Tunnel error 530"
- Проверьте токен в `docker.env`
- Проверьте DNS CNAME в Cloudflare
- Проверьте health checks: `docker-compose ps`

### "Backend not accessible"
- Логи: `docker-compose logs backend`
- Переменные: `docker exec orgon-backend env`
- Перезапуск: `docker-compose restart backend`

### "Frontend shows 500"
- Сеть: `docker exec orgon-frontend ping backend`
- Пересборка: `docker-compose build --no-cache frontend`

Полный troubleshooting: `DOCKER_DEPLOYMENT.md`

## 🔄 Миграция с локального

```bash
make -f Makefile.docker migrate
# Остановит локальные процессы и запустит Docker
```

## 📞 Support

- Issues: создайте issue в репозитории
- Docs: `DOCKER_DEPLOYMENT.md`
- Cloudflare: https://developers.cloudflare.com/cloudflare-one/

## 📝 License

Проприетарный - только для внутреннего использования
