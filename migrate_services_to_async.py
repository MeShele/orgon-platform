#!/usr/bin/env python3
"""
Auto-migrate ORGON services from sync SQLite to async PostgreSQL.
Converts database calls to async patterns.
"""

import re
from pathlib import Path

SERVICES_DIR = Path("backend/services")
BACKUP_DIR = Path("backend/services/.backup_sync")

# Conversion patterns
CONVERSIONS = [
    # Import changes
    (r"from backend\.database\.db import Database",
     "from backend.database.db_postgres import AsyncDatabase"),
    
    # Type hints
    (r"def __init__\(self, .*, db: Database\)",
     lambda m: m.group(0).replace("Database", "AsyncDatabase")),
    
    # fetchall → fetch
    (r"self\._db\.fetchall\(",
     "await self._db.fetch("),
    
    # fetchone → fetchrow
    (r"self\._db\.fetchone\(",
     "await self._db.fetchrow("),
    
    # execute
    (r"self\._db\.execute\(",
     "await self._db.execute("),
    
    # executemany
    (r"self\._db\.executemany\(",
     "await self._db.executemany("),
    
    # SQLite placeholders ? → PostgreSQL $1, $2, ...
    (r'\?\s*,', lambda m: auto_replace_placeholders(m)),
]


def auto_replace_placeholders(content: str) -> str:
    """Replace SQLite ? placeholders with PostgreSQL $1, $2, ..."""
    lines = content.split('\n')
    result = []
    
    for line in lines:
        # Find SQL strings (between quotes)
        if '"""' in line or "'''" in line or '"' in line or "'" in line:
            # Simple replacement: ? → $n (incremental)
            count = 0
            def replace_placeholder(match):
                nonlocal count
                count += 1
                return f"${count}"
            
            # Match ? that are likely SQL placeholders
            line = re.sub(r'\?(?=\s*[,\)])', replace_placeholder, line)
        
        result.append(line)
    
    return '\n'.join(result)


def migrate_service(service_path: Path) -> bool:
    """Migrate one service file to async."""
    print(f"🔄 Migrating {service_path.name}...")
    
    content = service_path.read_text()
    original = content
    
    # Apply conversions
    for pattern, replacement in CONVERSIONS:
        if callable(replacement):
            content = re.sub(pattern, replacement, content)
        else:
            content = content.replace(pattern, replacement) if isinstance(pattern, str) else re.sub(pattern, replacement, content)
    
    # Auto-replace ? → $n
    content = auto_replace_placeholders(content)
    
    if content == original:
        print(f"   ⏭️  No changes needed")
        return False
    
    # Backup original
    BACKUP_DIR.mkdir(exist_ok=True)
    backup_path = BACKUP_DIR / service_path.name
    backup_path.write_text(original)
    
    # Write migrated version
    service_path.write_text(content)
    
    print(f"   ✅ Migrated (backup: {backup_path})")
    return True


def main():
    print("🚀 ORGON Services Migration: Sync → Async\n")
    
    services = list(SERVICES_DIR.glob("*_service.py"))
    print(f"📦 Found {len(services)} services\n")
    
    migrated = 0
    for service in services:
        if migrate_service(service):
            migrated += 1
    
    print(f"\n✅ Migration complete: {migrated}/{len(services)} services migrated")
    print(f"📁 Backups saved to: {BACKUP_DIR}")


if __name__ == "__main__":
    main()
