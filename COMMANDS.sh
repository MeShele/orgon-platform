#!/bin/bash
# ORGON Docker - Quick Commands
# Используйте эти команды для управления Docker контейнерами

# ============================================
# SETUP (Первый раз)
# ============================================

# 1. Получите Cloudflare Tunnel Token
# Вариант A: Cloudflare Dashboard
# Zero Trust > Access > Tunnels > orgon > Configure > Copy token

# Вариант B: CLI
# cloudflared tunnel login
# cloudflared tunnel create orgon
# cloudflared tunnel token orgon

# 2. Обновите docker.env
# nano docker.env
# Замените: CLOUDFLARE_TUNNEL_TOKEN=<YOUR_TUNNEL_TOKEN_HERE>

# 3. Настройте DNS в Cloudflare
# DNS > Add record:
# Type: CNAME
# Name: orgon
# Target: <TUNNEL_ID>.cfargotunnel.com
# Proxy: Enabled (оранжевое облако)

# ============================================
# BUILD & RUN
# ============================================

# Сборка образов (первый раз)
docker-compose build

# Запуск всех сервисов
docker-compose --env-file docker.env up -d

# Сборка + запуск одной командой
docker-compose build && docker-compose --env-file docker.env up -d

# ============================================
# MONITORING
# ============================================

# Статус контейнеров
docker-compose ps

# Логи (все сервисы, live)
docker-compose logs -f

# Логи (только backend)
docker-compose logs -f backend

# Логи (только frontend)
docker-compose logs -f frontend

# Логи (только tunnel)
docker-compose logs -f cloudflared

# Последние 100 строк логов
docker-compose logs --tail=100

# ============================================
# HEALTH CHECKS
# ============================================

# Backend
curl http://localhost:8890/api/dashboard/stats | jq '.'

# Frontend
curl -I http://localhost:3000

# Public access
curl https://orgon.asystem.kg | head -20

# API через публичный домен
curl https://orgon.asystem.kg/api/dashboard/stats | jq '.'

# ============================================
# MANAGEMENT
# ============================================

# Перезапуск всех сервисов
docker-compose restart

# Перезапуск только backend
docker-compose restart backend

# Перезапуск только frontend
docker-compose restart frontend

# Остановка всех сервисов
docker-compose stop

# Остановка и удаление контейнеров
docker-compose down

# Остановка и удаление контейнеров + volumes
docker-compose down -v

# ============================================
# DEBUGGING
# ============================================

# Shell в backend контейнер
docker exec -it orgon-backend bash

# Shell в frontend контейнер
docker exec -it orgon-frontend sh

# Проверка переменных окружения
docker exec orgon-backend env
docker exec orgon-frontend env

# Проверка сети между контейнерами
docker exec orgon-frontend ping -c 3 backend
docker exec orgon-backend ping -c 3 frontend

# Статистика ресурсов
docker stats orgon-backend orgon-frontend orgon-tunnel

# ============================================
# REBUILD & UPDATE
# ============================================

# Пересборка без кэша
docker-compose build --no-cache

# Пересборка только backend
docker-compose build --no-cache backend

# Пересборка только frontend
docker-compose build --no-cache frontend

# Обновление и перезапуск
docker-compose pull
docker-compose up -d

# ============================================
# CLEANUP
# ============================================

# Удалить все контейнеры и сети
docker-compose down

# Удалить всё включая volumes
docker-compose down -v

# Удалить неиспользуемые Docker ресурсы
docker system prune -f

# Удалить всё (включая образы)
docker system prune -a -f

# ============================================
# MAKEFILE COMMANDS (рекомендуется)
# ============================================

# Показать все команды
make -f Makefile.docker help

# Запустить
make -f Makefile.docker up

# Остановить
make -f Makefile.docker down

# Перезапустить
make -f Makefile.docker restart

# Логи
make -f Makefile.docker logs

# Статус
make -f Makefile.docker status

# Health checks
make -f Makefile.docker health

# Пересборка
make -f Makefile.docker rebuild

# Миграция с локального развертывания
make -f Makefile.docker migrate

# Бэкап конфигурации
make -f Makefile.docker backup-config
