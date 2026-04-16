"""ORGON Backend - FastAPI Application Entry Point."""

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from typing import Set

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from backend.config import get_config
from backend.database.db import init_db, get_db
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
from backend.integrations.telegram_notifier import TelegramNotifier
from backend.integrations.asagent_bridge import ASAGENTBridge
from backend.tasks.scheduler import setup_scheduler, get_scheduler
from backend.api.middleware import setup_middleware

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("orgon")

# --- Global service instances ---
_signer: SafinaSigner | None = None
_safina_client: SafinaPayClient | None = None
_wallet_service: WalletService | None = None
_transaction_service: TransactionService | None = None
_sync_service: SyncService | None = None
_balance_service: BalanceService | None = None
_network_service: NetworkService | None = None
_signature_service: SignatureService | None = None
_dashboard_service: DashboardService | None = None
_telegram_notifier: TelegramNotifier | None = None
_asagent_bridge: ASAGENTBridge | None = None

# WebSocket connections
_ws_connections: Set[WebSocket] = set()


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
    """Application lifecycle manager."""
    global _signer, _safina_client
    global _wallet_service, _transaction_service, _sync_service, _balance_service, _network_service, _signature_service, _dashboard_service, _telegram_notifier, _asagent_bridge

    config = get_config()
    logger.info("Starting ORGON backend...")

    # Initialize database
    db = init_db(config["database"]["path"])
    run_migrations(db)
    logger.info("Database initialized")

    # Initialize Safina signer + client
    ec_key = config["safina"].get("ec_private_key", "")
    if ec_key:
        _signer = SafinaSigner(ec_key)
        _safina_client = SafinaPayClient(
            signer=_signer,
            base_url=config["safina"]["base_url"],
            timeout=config["safina"]["timeout"],
            max_retries=config["safina"]["max_retries"],
            retry_backoff=config["safina"]["retry_backoff"],
        )
        logger.info("Safina client initialized for address %s", _signer.address)

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
        )

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
            _sync_service, _balance_service, _transaction_service, _network_service, _signature_service
        )
        scheduler.start()
        logger.info("Scheduler started")
    else:
        logger.warning(
            "No SAFINA_EC_PRIVATE_KEY configured. API routes will return errors. "
            "Set the key in .env to enable Safina integration."
        )

    logger.info("ORGON backend ready on port %d", config["server"]["port"])

    yield

    # Shutdown
    logger.info("Shutting down ORGON backend...")
    scheduler = get_scheduler()
    if scheduler.running:
        scheduler.shutdown(wait=False)
    if _safina_client:
        await _safina_client.close()
    db.close()
    logger.info("Shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="ORGON - Wallet Management Dashboard",
    description="Crypto wallet management via Safina Pay API",
    version="1.0.0",
    lifespan=lifespan,
)

# Setup middleware
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

app.include_router(health_router)
app.include_router(wallets_router)
app.include_router(transactions_router)
app.include_router(networks_router)
app.include_router(signatures_router)
app.include_router(dashboard_router)
app.include_router(webhooks_router)
app.include_router(export_router)


@app.websocket("/ws/updates")
async def websocket_updates(websocket: WebSocket):
    """Real-time updates via WebSocket."""
    await websocket.accept()
    _ws_connections.add(websocket)
    logger.info("WebSocket client connected (%d total)", len(_ws_connections))

    try:
        while True:
            # Keep connection alive, handle incoming messages
            data = await websocket.receive_text()
            # Client can send ping/subscribe messages
            if data == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
    except WebSocketDisconnect:
        _ws_connections.discard(websocket)
        logger.info("WebSocket client disconnected (%d remaining)", len(_ws_connections))
