"""ORGON Backend - FastAPI Application (PostgreSQL version)."""

import asyncio
import bcrypt
import json
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Set

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import RedirectResponse, HTMLResponse

from backend.config import get_config

# Database imports
from backend.database.db import init_db as init_sqlite_db, get_db as get_sqlite_db
from backend.database.db_postgres import AsyncDatabase, init_db as init_postgres_db
from backend.database.migrations import run_migrations

from backend.safina.signer import SafinaSigner
from backend.safina.client import SafinaPayClient
from backend.services.wallet_service import WalletService
from backend.services.transaction_service import TransactionService
from backend.services.sync_service import SyncService
from backend.services.balance_service import BalanceService
from backend.services.network_service import NetworkService
from backend.services.signature_service import SignatureService
from backend.services.dashboard_service import DashboardService
from backend.services.scheduled_transaction_service import ScheduledTransactionService
from backend.services.address_book_service import AddressBookService
from backend.services.analytics_service import AnalyticsService
from backend.services.audit_service import AuditService
from backend.services.user_service import UserService
from backend.services.auth_service import AuthService
from backend.services.partner_service import PartnerService
from backend.services.organization_service import OrganizationService
from backend.integrations.telegram_notifier import TelegramNotifier
from backend.integrations.asagent_bridge import ASAGENTBridge
from backend.tasks.scheduler import setup_scheduler, get_scheduler
from backend.api.middleware import setup_middleware
from backend.events.manager import init_event_manager, get_event_manager
from backend.websocket_manager import ws_manager
from backend.email_service import email_service
from backend.services.notification_service import init_notification_service, get_notification_service
from backend.api.middleware_b2b import (
    APIKeyAuthMiddleware,
    RateLimitMiddleware as PartnerRateLimitMiddleware,
    AuditLoggingMiddleware,
)
from backend.middleware.security import LoginRateLimitMiddleware

# Configure logging — plain by default, JSON when ORGON_JSON_LOGS=1.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("orgon")

# Apply JSON formatter / Sentry init if enabled via env.
from backend.observability import configure_observability
configure_observability()

# --- Global service instances ---
_async_db: AsyncDatabase | None = None
_signer: SafinaSigner | None = None
_safina_client: SafinaPayClient | None = None
_wallet_service: WalletService | None = None
_transaction_service: TransactionService | None = None
_sync_service: SyncService | None = None
_balance_service: BalanceService | None = None
_address_book_service: AddressBookService | None = None
_analytics_service: AnalyticsService | None = None
_audit_service: AuditService | None = None
_user_service: UserService | None = None
_auth_service: AuthService | None = None
_network_service: NetworkService | None = None
_signature_service: SignatureService | None = None
_dashboard_service: DashboardService | None = None
_scheduled_transaction_service: ScheduledTransactionService | None = None
_telegram_notifier: TelegramNotifier | None = None
_asagent_bridge: ASAGENTBridge | None = None
_organization_service: OrganizationService | None = None

# B2B Platform services
_partner_service: PartnerService | None = None
_audit_service_b2b: AuditService | None = None  # B2B audit service (separate from internal audit)
_webhook_service = None  # WebhookService (imported conditionally)

# WebSocket connections
_ws_connections: Set[WebSocket] = set()


def get_database() -> AsyncDatabase:
    """Return the global async database. RLSMiddleware imports this via
    `from backend.main import get_database` — without the export the
    middleware logged "cannot import name 'get_database'" on every
    request and tenant RLS context never got set."""
    return _async_db


def get_safina_client() -> SafinaPayClient:
    return _safina_client

def get_wallet_service() -> WalletService:
    return _wallet_service

def get_transaction_service() -> TransactionService:
    return _transaction_service

def get_sync_service() -> SyncService:
    return _sync_service

def get_balance_service() -> BalanceService:
    return _balance_service

def get_network_service() -> NetworkService:
    return _network_service

def get_signature_service() -> SignatureService:
    return _signature_service

def get_dashboard_service() -> DashboardService:
    return _dashboard_service

def get_asagent_bridge() -> ASAGENTBridge:
    return _asagent_bridge

def get_scheduled_transaction_service() -> ScheduledTransactionService:
    return _scheduled_transaction_service

def get_address_book_service() -> AddressBookService:
    return _address_book_service

def get_analytics_service() -> AnalyticsService:
    return _analytics_service

def get_audit_service() -> AuditService:
    return _audit_service

def get_user_service() -> UserService:
    return _user_service

def get_auth_service() -> AuthService:
    return _auth_service

def get_partner_service() -> PartnerService:
    return _partner_service

def get_organization_service() -> OrganizationService:
    return _organization_service

def get_audit_service_b2b() -> AuditService:
    return _audit_service_b2b


async def broadcast_ws(event_type: str, data: dict):
    """Broadcast event to all connected WebSocket clients."""
    message = json.dumps({"type": event_type, "data": data})
    disconnected = set()
    for ws in _ws_connections:
        try:
            await ws.send_text(message)
        except Exception:
            disconnected.add(ws)
    _ws_connections -= disconnected


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle manager (PostgreSQL-enabled)."""
    global _async_db, _signer, _safina_client
    global _wallet_service, _transaction_service, _sync_service, _balance_service, _network_service, _signature_service, _dashboard_service, _scheduled_transaction_service, _address_book_service, _analytics_service, _audit_service, _user_service, _auth_service, _telegram_notifier, _asagent_bridge, _organization_service
    global _partner_service, _audit_service_b2b, _webhook_service

    config = get_config()
    logger.info("Starting ORGON backend...")
    app.state.lifespan_started = True
    app.state.lifespan_error = None

    # Initialize event manager
    event_manager = init_event_manager(history_size=200)
    logger.info("Event manager initialized")

    # Initialize database (PostgreSQL or SQLite fallback)
    db_url = os.getenv("DATABASE_URL") or config.get("database", {}).get("postgresql_url")
    
    if db_url:
        logger.info("🐘 Using PostgreSQL database")
        _async_db = AsyncDatabase(db_url)
        await _async_db.connect()
        db = _async_db  # Use async database directly
        logger.info("PostgreSQL connection pool created")

        # PostgreSQL migrations are applied via POST /api/health/run-migrations

        # Seed default admin user if no users exist
        try:
            async with _async_db.get_connection() as conn:
                user_count = await conn.fetchval("SELECT COUNT(*) FROM users")
                if user_count == 0:
                    password_hash = bcrypt.hashpw("demo2026".encode(), bcrypt.gensalt()).decode()
                    for email, name, role in [
                        ("demo-admin@orgon.io", "Demo Admin", "admin"),
                        ("demo-signer@orgon.io", "Demo Signer", "signer"),
                        ("demo-viewer@orgon.io", "Demo Viewer", "viewer"),
                    ]:
                        await conn.execute(
                            "INSERT INTO users (email, full_name, password_hash, role, is_active) VALUES ($1, $2, $3, $4, $5)",
                            email, name, password_hash, role, True
                        )
                    logger.info("Seeded 3 demo users (admin/signer/viewer)")
                else:
                    logger.info("Users table has %d users, skipping seed", user_count)
        except Exception as e:
            logger.warning("User seeding skipped: %s", e)
    else:
        logger.info("📂 Using SQLite database (fallback)")
        db = init_sqlite_db(config["database"]["path"])
        run_migrations(db)
    
    logger.info("Database initialized")

    # Force eager pool creation (lazy pool starts as None)
    if _async_db and _async_db._pool is None:
        await _async_db.connect()
        logger.info("PostgreSQL pool eagerly connected: %s", _async_db._pool)

    # Initialize Safina signer + client. Three modes:
    #   1. Real: SAFINA_EC_PRIVATE_KEY is set → live Safina API.
    #   2. Stub: SAFINA_STUB=1 OR no EC key → SafinaStubClient with canned data.
    #      Lets the demo render and walk through multi-sig without a live integration.
    #      Never enable this on the prod Coolify app.
    #   3. None: legacy behaviour (wallet/tx endpoints raise 500).
    ec_key = config["safina"].get("ec_private_key", "")
    safina_stub = os.getenv("SAFINA_STUB", "").lower() in {"1", "true", "yes"}
    try:
        if ec_key and not safina_stub:
            _signer = SafinaSigner(ec_key)
            _safina_client = SafinaPayClient(
                signer=_signer,
                base_url=config["safina"]["base_url"],
                timeout=config["safina"]["timeout"],
                max_retries=config["safina"]["max_retries"],
                retry_backoff=config["safina"]["retry_backoff"],
            )
            logger.info("Safina client initialized for address %s", _signer.address)
        elif safina_stub or not ec_key:
            from backend.safina.stub_client import SafinaStubClient
            _safina_client = SafinaStubClient()
            reason = "SAFINA_STUB=1" if safina_stub else "no SAFINA_EC_PRIVATE_KEY"
            logger.warning("Safina stub client active (%s) — demo mode, no real blockchain calls.", reason)
        else:
            _safina_client = None

        # Initialize services
        _wallet_service = WalletService(_safina_client, db)
        _transaction_service = TransactionService(_safina_client, db)
        _sync_service = SyncService(_safina_client, db)
        _balance_service = BalanceService(_safina_client, db)
        _network_service = NetworkService(_safina_client, db)

        # Initialize Telegram notifier (if enabled)
        if config.get("telegram", {}).get("enabled") and config["telegram"].get("bot_token"):
            try:
                _telegram_notifier = TelegramNotifier(
                    bot_token=config["telegram"]["bot_token"],
                    default_chat_id=config["telegram"].get("chat_id"),
                    max_retries=config["telegram"].get("max_retries", 3),
                    timeout=config["telegram"].get("timeout", 10),
                )
                # Test connection
                if await _telegram_notifier.test_connection():
                    logger.info("Telegram notifier initialized and connected")
                else:
                    logger.warning("Telegram notifier failed connection test")
                    _telegram_notifier = None
            except Exception as e:
                logger.error(f"Failed to initialize Telegram notifier: {e}")
                _telegram_notifier = None
        else:
            logger.info("Telegram notifier disabled (not configured)")

        # Signature service (with optional Telegram notifier)
        _signature_service = SignatureService(_safina_client, db, telegram_notifier=_telegram_notifier)

        # Dashboard service (aggregates data from all services)
        _dashboard_service = DashboardService(
            wallet_service=_wallet_service,
            transaction_service=_transaction_service,
            balance_service=_balance_service,
            signature_service=_signature_service,
            network_service=_network_service,
            db=db,
        )
        
        # Initialize Scheduled Transaction Service
        _scheduled_transaction_service = ScheduledTransactionService(
            transaction_service=_transaction_service,
            db=db
        )
        
        # Initialize Address Book Service
        _address_book_service = AddressBookService(db=db)
        
        # Initialize Analytics Service
        _analytics_service = AnalyticsService(db=db)
        
        # Initialize Audit Service (use pool if available)
        if _async_db and _async_db._pool:
            _audit_service = AuditService(db_pool=_async_db._pool)
        else:
            _audit_service = AuditService(db=db)
        
        # Initialize User Service
        _user_service = UserService(db=db)
        
        # Initialize Organization Service (multi-tenancy)
        _organization_service = OrganizationService(db=db)
        
        # Initialize Auth Service (requires pool)
        import sys
        print(f"[DEBUG] Checking PostgreSQL pool: _async_db={_async_db is not None}", file=sys.stderr, flush=True)
        if _async_db:
            print(f"[DEBUG] _async_db._pool = {_async_db._pool}", file=sys.stderr, flush=True)
        
        logger.info(f"Checking PostgreSQL pool: _async_db={_async_db is not None}, _pool={_async_db._pool if _async_db else None}")
        if _async_db and _async_db._pool:
            _auth_service = AuthService(pool=_async_db._pool)
            logger.info("Auth service initialized")
            print("[DEBUG] ✅ Auth service initialized", file=sys.stderr, flush=True)
        else:
            logger.error("❌ Auth service CANNOT be initialized - PostgreSQL pool not available!")
            logger.error(f"   _async_db={_async_db}, _pool={_async_db._pool if _async_db else 'N/A'}")
            print(f"[DEBUG] ❌ Auth service NOT initialized! _async_db={_async_db}, _pool={_async_db._pool if _async_db else 'N/A'}", file=sys.stderr, flush=True)
            raise RuntimeError("Auth service requires PostgreSQL pool")
        
        # Initialize B2B Platform Services (requires PostgreSQL)
        if _async_db and _async_db._pool:
            from backend.services.webhook_service import WebhookService
            
            _partner_service = PartnerService(db_pool=_async_db._pool)
            _audit_service_b2b = AuditService(db_pool=_async_db._pool)
            _webhook_service = WebhookService(db_pool=_async_db._pool)
            
            logger.info("Setting app.state services...")
            # Store services in app state for dependency injection
            app.state.db_pool = _async_db._pool
            app.state.partner_service = _partner_service
            app.state.audit_service_b2b = _audit_service_b2b
            app.state.webhook_service = _webhook_service
            
            # Store core services for Partner API
            app.state.wallet_service = _wallet_service
            app.state.transaction_service = _transaction_service
            app.state.signature_service = _signature_service
            app.state.network_service = _network_service
            app.state.audit_service = _audit_service
            app.state.analytics_service = _analytics_service
            app.state.scheduled_transaction_service = _scheduled_transaction_service
            app.state.address_book_service = _address_book_service
            app.state.auth_service = _auth_service
            app.state.user_service = _user_service
            app.state.organization_service = _organization_service
            
            logger.info("✅ app.state services set successfully")
            logger.info(f"   auth_service: {hasattr(app.state, 'auth_service')}")
            logger.info("B2B Platform services initialized (PartnerService, AuditService, WebhookService)")


            # Initialize Notification Service
            _notification_service = init_notification_service(
                db_pool=_async_db._pool,
                ws_manager=ws_manager,
                email_service=email_service,
                event_manager=event_manager,
                telegram_notifier=_telegram_notifier
            )
            app.state.notification_service = _notification_service
            logger.info("Notification service initialized (WS + Email + Telegram)")
        else:
            logger.error("❌ B2B Platform CANNOT be initialized - PostgreSQL not available!")
            raise RuntimeError("B2B Platform requires PostgreSQL")

        # Initialize ASAGENT Bridge (if enabled)
        if config.get("asagent", {}).get("enable_bridge", False):
            try:
                gateway_ws = config["asagent"].get("gateway_ws", "ws://127.0.0.1:18789")
                # Convert ws:// to http:// for REST API
                gateway_url = gateway_ws.replace("ws://", "http://").replace("wss://", "https://")

                _asagent_bridge = ASAGENTBridge(gateway_url=gateway_url)

                # Try to register skills
                try:
                    await _asagent_bridge.register_orgon_skills()
                    logger.info("ASAGENT Bridge initialized and skills registered")
                except Exception as e:
                    logger.warning(f"Could not register ASAGENT skills (gateway may be offline): {e}")
            except Exception as e:
                logger.error(f"Failed to initialize ASAGENT Bridge: {e}")
                _asagent_bridge = None
        else:
            logger.info("ASAGENT Bridge disabled")

        # Initial sync
        try:
            await _sync_service.sync_all()
            await _wallet_service.sync_wallets()
            await _transaction_service.sync_transactions()
            logger.info("Initial sync complete")
        except Exception as e:
            logger.warning("Initial sync failed (API may be unreachable): %s", e)

        # Start scheduler
        scheduler = setup_scheduler(
            _sync_service, 
            _balance_service, 
            _transaction_service, 
            _network_service, 
            _signature_service, 
            _scheduled_transaction_service,
            _webhook_service
        )
        scheduler.start()
        logger.info("Scheduler started")
    except Exception as e:
        logger.error("❌ Service initialization FAILED: %s", e, exc_info=True)
        app.state.lifespan_error = str(e)

    logger.info("ORGON backend ready on port %d", config["server"]["port"])

    yield

    # Shutdown
    logger.info("Shutting down ORGON backend...")
    scheduler = get_scheduler()
    if scheduler.running:
        scheduler.shutdown(wait=False)
    if _safina_client:
        await _safina_client.close()
    if _webhook_service:
        await _webhook_service.close()
        logger.info("WebhookService HTTP client closed")
    
    # Close price feed service
    from backend.services.price_feed_service import close_price_feed_service
    await close_price_feed_service()
    logger.info("PriceFeedService HTTP client closed")
    
    # Close database
    if _async_db:
        await _async_db.close()
        logger.info("PostgreSQL connection pool closed")
    else:
        db.close()
    
    logger.info("Shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="ORGON API",
    description="Multi-tenant cryptocurrency exchange platform with billing, compliance, and wallet management",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# Setup middleware (includes exception handler)
setup_middleware(app)

# Register routes
from backend.api.routes_health import router as health_router
from backend.api.routes_wallets import router as wallets_router
from backend.api.routes_transactions import router as transactions_router
from backend.api.routes_networks import router as networks_router
from backend.api.routes_signatures import router as signatures_router
from backend.api.routes_dashboard import router as dashboard_router
from backend.api.routes_webhooks import router as webhooks_router
from backend.api.routes_export import router as export_router
from backend.api.routes_scheduled import router as scheduled_router
from backend.api.routes_contacts import router as contacts_router
from backend.api.routes_analytics import router as analytics_router
from backend.api.routes_audit import router as audit_router
from backend.api.routes_auth import router as auth_router
from backend.api.routes_users import router as users_router
from backend.api.routes_twofa import router as twofa_router
from backend.api.test_events import router as test_events_router
from backend.api.routes_debug import router as debug_router
from backend.api.routes_organizations import router as organizations_router  # Multi-tenancy
from backend.api.routes_billing import router as billing_router
from backend.api.routes_compliance import router as compliance_router
from backend.api.routes_whitelabel import router as whitelabel_router
from backend.api.routes_kyc_kyb import router as kyc_kyb_router
from backend.api.routes_fiat import router as fiat_router
from backend.api.routes_monitoring import router as monitoring_router
from backend.api.routes_documents import router as documents_router
from backend.api.routes_reports import router as reports_router
from backend.api.routes_support import router as support_router
# compat routers removed in sprint 2 — they served hardcoded mock data

# B2B Platform routes
from backend.api.routes_partner import router as partner_router
from backend.api.routes_webhooks import router as partner_webhooks_router
from backend.api.routes_partner_analytics import router as partner_analytics_router
from backend.api.routes_safina_integration import router as safina_integration_router
from backend.api.routes_partner_scheduled import router as partner_scheduled_router
# routes_partner_addresses is broken-on-arrival: it calls
# AddressBookService.list_addresses / create_address / etc., which don't
# exist (the service only has get_contacts/create_contact). Disabled until
# the address_book_b2b model is properly wired. See CHANGELOG.md backlog.
# from backend.api.routes_partner_addresses import router as partner_addresses_router

app.include_router(health_router)
app.include_router(wallets_router)
app.include_router(transactions_router)
app.include_router(networks_router)
app.include_router(signatures_router)
app.include_router(dashboard_router)
app.include_router(webhooks_router)
app.include_router(export_router)
app.include_router(scheduled_router)
app.include_router(contacts_router)
app.include_router(analytics_router)
app.include_router(audit_router)
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(twofa_router)
app.include_router(organizations_router)  # Multi-tenancy
app.include_router(billing_router)  # Billing & Subscriptions
app.include_router(compliance_router)  # Compliance & Regulatory
app.include_router(whitelabel_router)  # White Label
app.include_router(kyc_kyb_router)  # KYC/KYB Verification Flow
app.include_router(fiat_router)  # Fiat On-ramp/Off-ramp
# app.include_router(test_events_router)  # Development only — disabled in prod (anonymous WS event injection)
# app.include_router(debug_router)  # Debug endpoints — disabled in prod (dumps app.state)
app.include_router(monitoring_router)  # Monitoring & Prometheus metrics
app.include_router(documents_router)  # OnlyOffice document tokens
app.include_router(reports_router)  # Reports
app.include_router(support_router)  # Support tickets

# B2B Platform routes
app.include_router(partner_router)
app.include_router(partner_webhooks_router)
app.include_router(partner_analytics_router)
app.include_router(partner_scheduled_router)
# app.include_router(partner_addresses_router)  # disabled — see import comment
app.include_router(safina_integration_router)  # Safina API gap closure

# B2B Partner-API middleware stack (tier-based rate limit + API-key auth)
app.add_middleware(AuditLoggingMiddleware)
app.add_middleware(PartnerRateLimitMiddleware)
app.add_middleware(APIKeyAuthMiddleware)

# General-API rate limit (login brute-force, 100 req/min/IP). Last-added so
# Starlette runs it outermost — bouncers hit before partner-tier check.
app.add_middleware(LoginRateLimitMiddleware)


# Swagger UI at /api/docs for Cloudflare Tunnel compatibility
@app.get("/api/docs", include_in_schema=False)
async def api_docs():
    """Serve Swagger UI at /api/docs (Cloudflare Tunnel compatible)."""
    from fastapi.openapi.docs import get_swagger_ui_html
    return get_swagger_ui_html(
        openapi_url="/api/openapi.json",
        title=app.title + " - Swagger UI"
    )


@app.get("/api/openapi.json", include_in_schema=False)
async def api_openapi():
    """Serve OpenAPI schema at /api/openapi.json."""
    return app.openapi()


@app.get("/api/redoc", include_in_schema=False)
async def api_redoc():
    """Serve ReDoc at /api/redoc."""
    from fastapi.openapi.docs import get_redoc_html
    return get_redoc_html(
        openapi_url="/api/openapi.json",
        title=app.title + " - ReDoc"
    )



@app.websocket("/ws/auth/{token}")
async def websocket_authenticated(websocket: WebSocket, token: str):
    """Authenticated WebSocket endpoint for per-user notifications."""
    from backend.services.auth_service import AuthService
    auth = getattr(app.state, 'auth_service', None)
    if not auth:
        await websocket.close(code=1011)
        return
    payload = auth.decode_token(token)
    if not payload:
        await websocket.close(code=1008)
        return
    user_id = payload.get("sub")
    if not user_id:
        await websocket.close(code=1008)
        return
    await ws_manager.connect(websocket, user_id)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket, user_id)

@app.websocket("/ws/updates")
async def websocket_updates(websocket: WebSocket):
    """
    Real-time updates via WebSocket.
    
    Events:
    - balance.updated
    - transaction.created/sent/confirmed/failed
    - signature.pending/approved/rejected
    - wallet.created/updated
    - sync.completed
    """
    await websocket.accept()
    
    event_manager = get_event_manager()
    event_manager.add_connection(websocket)
    
    # Send connection success message
    await websocket.send_text(json.dumps({
        "type": "connected",
        "message": "WebSocket connected",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }))

    try:
        while True:
            # Keep connection alive, handle incoming messages
            data = await websocket.receive_text()
            
            # Handle client messages
            if data == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
            elif data == "history":
                # Send recent event history
                history = event_manager.get_history(limit=20)
                await websocket.send_text(json.dumps({
                    "type": "history",
                    "events": [{"type": e.type.value, "data": e.data, "timestamp": e.timestamp} for e in history]
                }))
                
    except WebSocketDisconnect:
        event_manager.remove_connection(websocket)
