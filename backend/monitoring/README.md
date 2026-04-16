# ORGON Monitoring Stack

Production monitoring for ORGON B2B Platform using Prometheus, Grafana, and Alertmanager.

---

## Components

- **Prometheus** - Metrics collection and storage
- **Grafana** - Visualization and dashboards
- **Alertmanager** - Alert routing and notifications

---

## Quick Start

### 1. Start Monitoring Stack

```bash
cd backend/monitoring
docker-compose up -d
```

### 2. Access UIs

- **Grafana**: http://localhost:3001 (admin / admin)
- **Prometheus**: http://localhost:9090
- **Alertmanager**: http://localhost:9093

### 3. Verify Metrics

Backend exposes `/metrics` endpoint:

```bash
curl http://localhost:8890/metrics
```

---

## Dashboards

### ORGON B2B Platform Dashboard

**URL:** Grafana → Dashboards → ORGON B2B Platform

**Panels:**
1. **Total Requests** - Request rate (req/s)
2. **Error Rate** - 5xx errors as percentage
3. **P95 Response Time** - 95th percentile latency
4. **Active DB Connections** - Current database connections
5. **Request Rate by Endpoint** - Breakdown by API route
6. **Response Time Percentiles** - p50, p95, p99
7. **HTTP Status Codes** - 2xx, 4xx, 5xx distribution
8. **Webhook Queue Size** - Pending webhook deliveries

---

## Metrics Exposed

### HTTP Metrics

- `http_requests_total{method, endpoint, status}` - Total HTTP requests
- `http_request_duration_seconds{method, endpoint}` - Request latency histogram

### Database Metrics

- `db_connections_active` - Active database connections
- `db_query_duration_seconds{query_type}` - Query latency histogram

### Webhook Metrics

- `webhook_queue_size` - Webhooks pending delivery
- `webhook_delivery_attempts_total{partner_id, event_type, status}` - Delivery attempts
- `webhook_delivery_failures_total{partner_id, event_type}` - Failed deliveries

### Partner API Metrics

- `partner_api_requests_total{partner_id, endpoint, status}` - Partner API requests
- `partner_api_errors_total{partner_id, endpoint, error_type}` - Partner API errors
- `rate_limit_hits_total{partner_id, tier}` - Rate limit violations

### Business Metrics

- `wallets_created_total{partner_id, network_id}` - Total wallets created
- `transactions_processed_total{partner_id, network_id, status}` - Total transactions
- `active_wallets_total{partner_id}` - Active wallets per partner

---

## Alerts

### Critical Alerts (immediate notification)

- **HighErrorRate** - Error rate >5% for 5 minutes
- **DatabasePoolExhaustion** - Active connections >18/20
- **BackendDown** - Backend service unreachable >1 minute

### Warning Alerts (batched notification)

- **SlowAPIResponseTime** - P95 >500ms for 5 minutes
- **WebhookQueueBackup** - Queue size >100 for 10 minutes
- **RateLimitAbuse** - >10 rate limit hits/sec for 5 minutes

### Partner-Specific Alerts

- **PartnerAPIFailureRate** - >10% failure rate for 10 minutes
- **PartnerWebhookDeliveryFailure** - >5 failed webhooks in 30 minutes

---

## Alert Routing

Alerts are sent to Telegram via webhook:

1. **Alertmanager** fires alert
2. **Webhook** → `http://host.docker.internal:8891/alertmanager-webhook`
3. **Backend** forwards to Telegram (if configured)

**To enable Telegram alerts:**

1. Set `TELEGRAM_BOT_TOKEN` in backend `.env`
2. Set `TELEGRAM_CHAT_ID` in backend `.env`
3. Create webhook route in backend (optional, for custom formatting)

---

## Configuration

### Prometheus

**File:** `prometheus.yml`

- **Scrape interval:** 15s
- **Evaluation interval:** 15s
- **Scrape timeout:** 5s

**Targets:**
- Backend: `http://host.docker.internal:8890/metrics`

### Alertmanager

**File:** `alertmanager.yml`

- **Group wait:** 10s (critical), 30s (warning)
- **Repeat interval:** 1h (critical), 6h (warning)

### Grafana

**File:** `grafana-datasources/prometheus.yml`

- **Default datasource:** Prometheus
- **Refresh interval:** 10s

---

## Troubleshooting

### Prometheus can't scrape backend

**Symptom:** "Connection refused" in Prometheus Targets

**Fix:**
```bash
# Check backend is running
curl http://localhost:8890/health

# Check metrics endpoint
curl http://localhost:8890/metrics

# Verify Docker network
docker exec orgon-prometheus ping host.docker.internal
```

### Grafana dashboard not loading

**Symptom:** "No data" in panels

**Fix:**
1. Check Prometheus datasource: Grafana → Configuration → Data Sources
2. Test connection: Click "Save & Test"
3. Verify metrics exist: Prometheus → Graph → Execute `http_requests_total`

### Alerts not firing

**Symptom:** No Telegram notifications

**Fix:**
1. Check Alertmanager status: http://localhost:9093
2. Verify alert rules: Prometheus → Alerts
3. Check webhook URL in `alertmanager.yml`
4. Test webhook manually:
   ```bash
   curl -X POST http://localhost:8891/alertmanager-webhook \
     -H "Content-Type: application/json" \
     -d '{"alerts": [{"status": "firing", "labels": {"alertname": "Test"}}]}'
   ```

---

## Production Deployment

### Recommended Changes

1. **Persistent storage:**
   ```yaml
   volumes:
     prometheus_data:
       driver: local
       driver_opts:
         type: none
         o: bind
         device: /data/prometheus
   ```

2. **Authentication:**
   - Enable Grafana OAuth (Google, GitHub, etc.)
   - Set strong admin password
   - Restrict Prometheus access (nginx reverse proxy)

3. **Retention:**
   ```bash
   # Prometheus (default: 15 days)
   --storage.tsdb.retention.time=30d
   ```

4. **Alerting:**
   - Set up PagerDuty / OpsGenie for critical alerts
   - Configure multiple notification channels
   - Add escalation policies

---

## Monitoring Best Practices

### SLOs (Service Level Objectives)

- **Availability:** 99.9% uptime (43 min downtime/month)
- **Latency:** P95 <100ms, P99 <500ms
- **Error rate:** <0.1% (1 in 1000 requests)

### Alert Fatigue Prevention

- ✅ Only alert on actionable issues
- ✅ Use "for" duration to avoid flapping
- ✅ Group related alerts (e.g., by partner_id)
- ✅ Set appropriate thresholds (not too sensitive)
- ❌ Don't alert on warnings during deployments

### Dashboard Design

- ✅ Use RED method: Rate, Errors, Duration
- ✅ Show percentiles (p50, p95, p99) not averages
- ✅ Include business metrics (wallets, transactions)
- ✅ Add annotations for deployments
- ❌ Don't overcomplicate (8 panels max)

---

## Scaling

### High Traffic (>1000 req/s)

1. **Prometheus:**
   - Increase retention: `--storage.tsdb.retention.time=7d`
   - Reduce scrape interval: `30s`
   - Use remote storage (Thanos, Cortex)

2. **Grafana:**
   - Enable query caching
   - Use Grafana Loki for logs
   - Deploy multiple Grafana instances (load balancer)

3. **Alertmanager:**
   - Cluster mode (3+ instances)
   - Use external notification service (PagerDuty)

---

## Useful Queries

### Top 10 slowest endpoints

```promql
topk(10, 
  histogram_quantile(0.95, 
    rate(http_request_duration_seconds_bucket[5m])
  )
) by (endpoint)
```

### Error rate by partner

```promql
sum by (partner_id) (
  rate(partner_api_errors_total[5m])
) / sum by (partner_id) (
  rate(partner_api_requests_total[5m])
) * 100
```

### Webhook delivery success rate

```promql
(
  sum(rate(webhook_delivery_attempts_total{status="success"}[10m]))
  /
  sum(rate(webhook_delivery_attempts_total[10m]))
) * 100
```

---

## Support

For issues or questions:
- GitHub Issues: https://github.com/asystem/orgon
- Telegram: @urmatdigital
- Email: support@asystem.ai

---

**Last updated:** 2026-02-08  
**Version:** 1.0.0
