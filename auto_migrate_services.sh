#!/bin/bash
# Auto-migrate ORGON services to async PostgreSQL

set -e

SERVICES_DIR="backend/services"
BACKUP_DIR="backend/services/.backup_sqlite"

mkdir -p "$BACKUP_DIR"

echo "🚀 Auto-migrating services to async PostgreSQL..."
echo ""

for service in balance_service network_service sync_service signature_service dashboard_service transaction_service; do
    file="$SERVICES_DIR/${service}.py"
    
    if [ ! -f "$file" ]; then
        echo "⏭️  $file not found"
        continue
    fi
    
    echo "📦 Migrating $service.py..."
    
    # Backup
    cp "$file" "$BACKUP_DIR/${service}_backup.py"
    
    # Create temp file
    temp_file=$(mktemp)
    
    # 1. Import changes
    sed 's/from backend\.database\.db import Database/from backend.database.db_postgres import AsyncDatabase/' "$file" > "$temp_file"
    
    # 2. Type hints
    sed -i '' 's/db: Database/db: AsyncDatabase/g' "$temp_file"
    
    # 3. Add await to db calls
    sed -i '' 's/self\._db\.fetchall(/await self._db.fetch(/g' "$temp_file"
    sed -i '' 's/self\._db\.fetchone(/await self._db.fetchrow(/g' "$temp_file"
    sed -i '' 's/self\._db\.execute(/await self._db.execute(/g' "$temp_file"
    sed -i '' 's/self\._db\.executemany(/await self._db.executemany(/g' "$temp_file"
    
    # 4. Convert ? to $n placeholders (simple cases)
    # This is tricky - will need manual review
    
    # Write back
    mv "$temp_file" "$file"
    
    echo "   ✅ Migrated (backup: $BACKUP_DIR/${service}_backup.py)"
done

echo ""
echo "✅ Auto-migration complete!"
echo "⚠️  Manual review required:"
echo "   - SQL placeholders (? → \$1, \$2, ...)"
echo "   - INSERT OR REPLACE → INSERT ... ON CONFLICT"
echo "   - Async/await completeness"
