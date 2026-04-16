#!/usr/bin/env python3
"""Fix INSERT OR REPLACE → INSERT ... ON CONFLICT for PostgreSQL."""

import re
from pathlib import Path

SERVICES_DIR = Path("backend/services")

# Known UPSERT patterns
UPSERT_FIXES = {
    # wallets table
    "INSERT INTO wallets": {
        "conflict": "(name)",
        "update": "wallet_id = EXCLUDED.wallet_id, network = EXCLUDED.network, wallet_type = EXCLUDED.wallet_type, info = EXCLUDED.info, addr = EXCLUDED.addr, addr_info = EXCLUDED.addr_info, my_unid = EXCLUDED.my_unid, token_short_names = EXCLUDED.token_short_names, synced_at = EXCLUDED.synced_at, updated_at = EXCLUDED.updated_at"
    },
    # networks_cache table
    "INSERT INTO networks_cache": {
        "conflict": "(network_id)",
        "update": "network_name = EXCLUDED.network_name, link = EXCLUDED.link, address_explorer = EXCLUDED.address_explorer, tx_explorer = EXCLUDED.tx_explorer, block_explorer = EXCLUDED.block_explorer, info = EXCLUDED.info, status = EXCLUDED.status, updated_at = EXCLUDED.updated_at"
    },
    # tokens_info_cache table
    "INSERT INTO tokens_info_cache": {
        "conflict": "(token)",
        "update": "commission = EXCLUDED.commission, commission_min = EXCLUDED.commission_min, commission_max = EXCLUDED.commission_max, updated_at = EXCLUDED.updated_at"
    },
    # sync_state table
    "INSERT INTO sync_state": {
        "conflict": "(key)",
        "update": "value = EXCLUDED.value, updated_at = EXCLUDED.updated_at"
    },
    # transactions table
    "INSERT INTO transactions": {
        "conflict": "(unid)",
        "update": "safina_id = EXCLUDED.safina_id, tx_hash = EXCLUDED.tx_hash, token = EXCLUDED.token, token_name = EXCLUDED.token_name, to_addr = EXCLUDED.to_addr, value = EXCLUDED.value, value_hex = EXCLUDED.value_hex, init_ts = EXCLUDED.init_ts, min_sign = EXCLUDED.min_sign, status = EXCLUDED.status, info = EXCLUDED.info, wallet_name = EXCLUDED.wallet_name, network = EXCLUDED.network, synced_at = EXCLUDED.synced_at, updated_at = EXCLUDED.updated_at"
    },
}


def fix_file(file_path: Path) -> bool:
    """Fix UPSERT patterns in one file."""
    content = file_path.read_text()
    original = content
    
    # Find all INSERT statements
    pattern = r'("""INSERT INTO \w+.*?""")'
    
    def replace_insert(match):
        sql = match.group(0)
        
        # Check if it's a known table
        for table_pattern, fix in UPSERT_FIXES.items():
            if table_pattern in sql and "ON CONFLICT" not in sql:
                # Add ON CONFLICT clause before the closing quotes
                upsert = sql.rstrip('"""')
                upsert += f'\n               ON CONFLICT {fix["conflict"]} DO UPDATE SET\n                   {fix["update"]}"""'
                return upsert
        
        return sql
    
    content = re.sub(pattern, replace_insert, content, flags=re.DOTALL)
    
    if content == original:
        return False
    
    file_path.write_text(content)
    return True


def main():
    print("🔧 Fixing INSERT OR REPLACE → PostgreSQL UPSERT\n")
    
    files = list(SERVICES_DIR.glob("*_service.py"))
    fixed = 0
    
    for file_path in files:
        if fix_file(file_path):
            print(f"✅ Fixed {file_path.name}")
            fixed += 1
        else:
            print(f"⏭️  {file_path.name} - no changes")
    
    print(f"\n✅ Fixed {fixed}/{len(files)} files")


if __name__ == "__main__":
    main()
