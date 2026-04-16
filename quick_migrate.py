#!/usr/bin/env python3
"""Quick migration: Replace Database with AsyncDatabase, keep sync interface."""

import re
from pathlib import Path

services = [
    "backend/services/wallet_service.py",
    "backend/services/network_service.py",
    "backend/services/balance_service.py",
    "backend/services/sync_service.py",
]

for service_path in services:
    path = Path(service_path)
    if not path.exists():
        continue
    
    content = path.read_text()
    original = content
    
    # Simple replacements
    content = content.replace(
        "from backend.database.db import Database",
        "from backend.database.db_postgres import AsyncDatabase"
    )
    content = content.replace(
        "db: Database",
        "db: AsyncDatabase"
    )
    
    if content != original:
        print(f"✅ {path.name}")
        path.write_text(content)

print("\n✅ Quick migration done")
print("⚠️  Services still use sync interface via HybridDatabase wrapper")
