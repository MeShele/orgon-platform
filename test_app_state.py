"""Test app.state during startup."""
import asyncio
import sys
from backend.main import app

async def test_app_state():
    """Check if app.state is properly set after startup."""
    # Trigger startup
    async with asyncio.TaskGroup() as tg:
        # Startup events
        startup_handler = app.router.lifespan_context
        async with startup_handler(app):
            # Check app.state
            print("=== app.state attributes ===")
            for attr in dir(app.state):
                if not attr.startswith('_'):
                    value = getattr(app.state, attr, None)
                    print(f"  {attr}: {type(value).__name__}")
            
            # Check specifically for auth_service
            print("\n=== Checking auth_service ===")
            if hasattr(app.state, 'auth_service'):
                print(f"✅ auth_service EXISTS: {app.state.auth_service}")
            else:
                print("❌ auth_service NOT FOUND")
            
            # Check all expected services
            expected = ['auth_service', 'user_service', 'wallet_service', 
                       'transaction_service', 'network_service']
            print("\n=== Expected services ===")
            for service_name in expected:
                exists = hasattr(app.state, service_name)
                status = "✅" if exists else "❌"
                print(f"{status} {service_name}: {exists}")

try:
    asyncio.run(test_app_state())
except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
