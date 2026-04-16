# ORGON Platform — Deployment Guide

**Last Updated:** 2026-02-12 05:55 GMT+6  
**Version:** 1.0 (Production Ready)  
**Target:** Docker Compose (Single Server) or Kubernetes (Scalable)

---

## Prerequisites

### System Requirements
- **OS:** Ubuntu 22.04 LTS or macOS
- **CPU:** 4+ cores (8+ recommended)
- **RAM:** 8GB minimum (16GB+ recommended)
- **Disk:** 100GB SSD
- **Network:** Static IP, domain name configured

### Software
- Docker 24+ & Docker Compose 2+
- Node.js 20+ (для frontend build)
- Python 3.13+ (для backend)
- Git
- SSL certificate (Let's Encrypt)

---

## Architecture

```
┌─────────────────────────────────────────────┐
│              CloudFlare CDN                 │
│         (DDoS protection, SSL, Cache)       │
└─────────────────┬───────────────────────────┘
                  │
┌─────────────────▼───────────────────────────┐
│           Reverse Proxy (Caddy)             │
│         (SSL termination, routing)          │
└─────────────────┬───────────────────────────┘
                  │
      ┌───────────┼───────────┐
      │           │           │
┌─────▼─────┐ ┌──▼──────┐ ┌──▼──────┐
│  Frontend │ │ Backend │ │PostgreSQL│
│ (Next.js) │ │(FastAPI)│ │(Neon.tech│
│   :3000   │ │  :8000  │ │ managed) │
└───────────┘ └─────────┘ └──────────┘
```

---

## Deployment Options

### Option A: Docker Compose (Recommended for MVP)
**Best for:** Single server, < 10K users  
**Pros:** Simple, fast setup  
**Cons:** No auto-scaling

### Option B: Kubernetes (Enterprise)
**Best for:** Multi-server, > 10K users  
**Pros:** Auto-scaling, high availability  
**Cons:** Complex setup

**This guide covers Option A (Docker Compose).**

---

## Step 1: Server Setup

### 1.1 Provision Server
```bash
# DigitalOcean, Hetzner, or any VPS provider
# Recommended: 4 CPU, 8GB RAM, 100GB SSD
# Example: Hetzner CPX31 ($15/month)

# SSH into server
ssh root@your-server-ip
```

### 1.2 Update System
```bash
apt update && apt upgrade -y
apt install -y docker.io docker-compose git ufw
```

### 1.3 Configure Firewall
```bash
# Allow SSH, HTTP, HTTPS only
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw enable

# Deny all other ports (database, backend API not exposed)
```

### 1.4 Create Non-Root User
```bash
adduser orgon
usermod -aG sudo,docker orgon
su - orgon
```

---

## Step 2: Clone Repository

```bash
cd /home/orgon
git clone https://github.com/your-org/orgon-platform.git
cd orgon-platform
```

---

## Step 3: Environment Configuration

### 3.1 Backend (.env)
```bash
cd backend
cp .env.example .env
nano .env
```

```env
# Database (Neon.tech managed PostgreSQL)
DATABASE_URL=postgresql://user:password@neon-host/orgon_production

# JWT
JWT_SECRET_KEY=<generate-with-openssl-rand-hex-32>
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=60

# CORS
ALLOWED_ORIGINS=https://app.orgon.example.com

# Security
DEBUG=false
SECRET_KEY=<another-random-key>

# Email (SendGrid, Mailgun, or SMTP)
EMAIL_HOST=smtp.sendgrid.net
EMAIL_PORT=587
EMAIL_USER=apikey
EMAIL_PASSWORD=<sendgrid-api-key>
EMAIL_FROM=noreply@orgon.example.com

# Payment Gateway (Stripe)
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...

# Monitoring (Sentry)
SENTRY_DSN=https://...@sentry.io/...
```

### 3.2 Frontend (.env.local)
```bash
cd ../frontend
cp .env.example .env.local
nano .env.local
```

```env
NEXT_PUBLIC_API_URL=https://api.orgon.example.com
NEXT_PUBLIC_APP_URL=https://app.orgon.example.com
NEXT_PUBLIC_SENTRY_DSN=https://...@sentry.io/...
```

---

## Step 4: Build Images

### 4.1 Backend
```bash
cd backend
docker build -t orgon-backend:latest .
```

**Dockerfile:**
```dockerfile
FROM python:3.13-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy code
COPY . .

# Create non-root user
RUN useradd -m -u 1000 orgon && chown -R orgon:orgon /app
USER orgon

# Expose port
EXPOSE 8000

# Run migrations + start server
CMD ["sh", "-c", "python -m alembic upgrade head && uvicorn main:app --host 0.0.0.0 --port 8000"]
```

### 4.2 Frontend
```bash
cd ../frontend
docker build -t orgon-frontend:latest .
```

**Dockerfile:**
```dockerfile
FROM node:20-alpine AS builder

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm ci

# Build
COPY . .
RUN npm run build

# Production image
FROM node:20-alpine

WORKDIR /app

COPY --from=builder /app/next.config.js ./
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./package.json

RUN adduser -D -u 1000 orgon && chown -R orgon:orgon /app
USER orgon

EXPOSE 3000

CMD ["npm", "start"]
```

---

## Step 5: Docker Compose

### docker-compose.production.yml
```yaml
version: '3.8'

services:
  # Backend API
  backend:
    image: orgon-backend:latest
    restart: always
    env_file:
      - backend/.env
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
    ports:
      - "8000:8000"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    networks:
      - orgon-network
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  # Frontend
  frontend:
    image: orgon-frontend:latest
    restart: always
    env_file:
      - frontend/.env.local
    ports:
      - "3000:3000"
    depends_on:
      - backend
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000/api/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    networks:
      - orgon-network
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  # Reverse Proxy (Caddy)
  caddy:
    image: caddy:2-alpine
    restart: always
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile
      - caddy_data:/data
      - caddy_config:/config
    networks:
      - orgon-network
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

networks:
  orgon-network:
    driver: bridge

volumes:
  caddy_data:
  caddy_config:
```

### Caddyfile
```
# API
api.orgon.example.com {
    reverse_proxy backend:8000
    
    # Security headers (additional to backend middleware)
    header {
        Strict-Transport-Security "max-age=31536000; includeSubDomains; preload"
        X-Robots-Tag "noindex, nofollow"
    }
    
    # Rate limiting (CloudFlare handles this, but backup)
    rate_limit {
        zone api
        key {remote_host}
        window 1m
        events 100
    }
}

# Frontend
app.orgon.example.com {
    reverse_proxy frontend:3000
    
    # Security headers
    header {
        Strict-Transport-Security "max-age=31536000; includeSubDomains; preload"
        X-Content-Type-Options "nosniff"
        X-Frame-Options "DENY"
        Referrer-Policy "strict-origin-when-cross-origin"
    }
    
    # Cache static assets
    @static {
        path /_next/static/* /favicon.ico /robots.txt
    }
    header @static Cache-Control "public, max-age=31536000, immutable"
}
```

---

## Step 6: Database Migration

```bash
# Connect to Neon.tech production DB
psql $DATABASE_URL

# Run migrations
cd backend
python -m alembic upgrade head

# Verify migrations
psql $DATABASE_URL -c "\dt"

# Seed data (subscription plans, default settings)
python scripts/seed_production.py
```

---

## Step 7: Start Services

```bash
# Start all services
docker-compose -f docker-compose.production.yml up -d

# Check logs
docker-compose -f docker-compose.production.yml logs -f

# Verify health
curl https://api.orgon.example.com/health
curl https://app.orgon.example.com/
```

---

## Step 8: Post-Deployment

### 8.1 Monitoring Setup
```bash
# Sentry (error tracking)
# Already configured in .env

# Uptime monitoring (Pingdom, UptimeRobot)
# Add checks for:
# - https://api.orgon.example.com/health
# - https://app.orgon.example.com/

# Metrics (optional: Prometheus + Grafana)
# TODO: Add prometheus exporter to backend
```

### 8.2 Backup Strategy
```bash
# Database: Neon.tech handles automated backups (7 days retention)
# Verify backup schedule in Neon dashboard

# Application state (volumes):
docker run --rm -v orgon_caddy_data:/data -v $(pwd):/backup alpine tar czf /backup/caddy-backup.tar.gz /data

# Store backups in S3/R2 (automated via cron)
```

### 8.3 SSL Certificate Verification
```bash
# Check SSL grade
curl https://api.ssllabs.com/api/v3/analyze?host=api.orgon.example.com

# Target: A+ rating
```

### 8.4 Security Hardening
```bash
# Disable password SSH (use keys only)
sudo nano /etc/ssh/sshd_config
# Set: PasswordAuthentication no
sudo systemctl restart sshd

# Install fail2ban (brute force protection)
sudo apt install fail2ban
sudo systemctl enable fail2ban
```

---

## Rollback Procedure

If deployment fails:

```bash
# 1. Stop new containers
docker-compose -f docker-compose.production.yml down

# 2. Restore previous images
docker tag orgon-backend:previous orgon-backend:latest
docker tag orgon-frontend:previous orgon-frontend:latest

# 3. Rollback database (if migrations failed)
cd backend
python -m alembic downgrade -1

# 4. Restart with previous version
docker-compose -f docker-compose.production.yml up -d

# 5. Verify health
curl https://api.orgon.example.com/health
```

---

## Scaling Strategy

### Vertical Scaling (Easier)
- Upgrade server (more CPU/RAM)
- Tune connection pool size
- Add Redis cache

### Horizontal Scaling (Complex)
- Load balancer (HAProxy, NGINX)
- Multiple backend instances
- Separate database server
- Redis for session storage

**Recommendation:** Start with vertical scaling, move to horizontal when > 10K users.

---

## Maintenance

### Daily
- [ ] Check error logs (Sentry)
- [ ] Monitor uptime (Pingdom)
- [ ] Review security alerts

### Weekly
- [ ] Review performance metrics
- [ ] Database query optimization
- [ ] Disk usage check

### Monthly
- [ ] Security updates (`apt upgrade`)
- [ ] Dependency updates (`npm audit`, `pip-audit`)
- [ ] Backup verification (restore test)
- [ ] Review access logs (suspicious activity)

### Quarterly
- [ ] SSL certificate renewal (auto with Caddy)
- [ ] Penetration testing
- [ ] Disaster recovery drill
- [ ] Capacity planning review

---

## Troubleshooting

### Backend Not Starting
```bash
# Check logs
docker logs orgon-backend

# Common issues:
# - Database connection failed → Check DATABASE_URL
# - Migration error → Rollback and fix migration
# - Port conflict → Check if 8000 already in use
```

### Frontend Build Failure
```bash
# Check build logs
docker logs orgon-frontend

# Common issues:
# - Out of memory → Increase Docker memory limit
# - Missing env vars → Check .env.local
# - TypeScript errors → Fix before deploying
```

### High Memory Usage
```bash
# Check container stats
docker stats

# Restart leaky container
docker-compose restart backend

# Permanent fix: Investigate memory leak (profile with py-spy)
```

### Database Connection Pool Exhausted
```bash
# Check active connections
psql $DATABASE_URL -c "SELECT count(*) FROM pg_stat_activity;"

# Increase pool size in backend config
# or kill idle connections
```

---

## Go-Live Checklist

**Pre-Launch:**
- [ ] All HIGH security issues resolved
- [ ] SSL certificate installed (A+ rating)
- [ ] Database migrations applied
- [ ] Seed data loaded
- [ ] All services healthy
- [ ] Monitoring configured (Sentry, Pingdom)
- [ ] Backups tested (restore successful)
- [ ] Load testing passed (p95 < 500ms)
- [ ] Error tracking verified (test Sentry integration)
- [ ] Rate limiting active
- [ ] Firewall configured
- [ ] DNS configured (A records for api.*, app.*)

**Launch Day:**
- [ ] Final smoke test
- [ ] Announce downtime (if migrating from old system)
- [ ] Deploy production
- [ ] Verify health checks
- [ ] Monitor logs for 1 hour
- [ ] Test critical flows (login, subscription, payment)
- [ ] Announce launch 🎉

**Post-Launch:**
- [ ] Monitor for 24 hours (on-call)
- [ ] Review first day metrics
- [ ] Collect user feedback
- [ ] Fix critical bugs (hotfix deployment)

---

## Support

**Runbook:** `/docs/RUNBOOK.md` (create this)  
**On-Call:** Forge 🔥 (or your ops team)  
**Emergency Contact:** support@orgon.example.com

---

**Last Updated:** 2026-02-12 05:55 GMT+6  
**Next Review:** 2026-03-12 (or before major update)
