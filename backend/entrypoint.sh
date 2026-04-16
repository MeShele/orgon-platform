#!/bin/sh

# Create SQLite fallback tables
python3 -c "
import sqlite3, os
os.makedirs('/app/data', exist_ok=True)
c = sqlite3.connect('/app/data/orgon.db')
c.execute('CREATE TABLE IF NOT EXISTS sync_state (key TEXT PRIMARY KEY, value TEXT, updated_at TEXT)')
c.execute('CREATE TABLE IF NOT EXISTS wallets (id TEXT PRIMARY KEY, network TEXT, address TEXT, name TEXT, balance REAL DEFAULT 0)')
c.execute('CREATE TABLE IF NOT EXISTS transactions (id TEXT PRIMARY KEY, wallet_id TEXT, tx_hash TEXT, amount REAL, status TEXT)')
c.execute('CREATE TABLE IF NOT EXISTS signatures (id TEXT PRIMARY KEY, tx_id TEXT, signer TEXT, status TEXT)')
c.commit()
print('SQLite tables ready')
"

# Patch main.py: force eager pool.connect() before pool check
python3 << 'PATCH'
main = open('/app/main.py').read()
if 'await _async_db.connect()' not in main:
    main = main.replace(
        'logger.info("Database initialized")',
        'logger.info("Database initialized")\n        if _async_db:\n            await _async_db.connect()\n            logger.info("PostgreSQL pool eagerly connected")'
    )
    open('/app/main.py', 'w').write(main)
    print('Patched main.py: added eager connect()')
else:
    print('main.py already patched')
PATCH

exec uvicorn main:app --host 0.0.0.0 --port 8890
