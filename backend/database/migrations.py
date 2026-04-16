"""Schema migration runner for ORGON."""

import logging
from pathlib import Path

from .db import Database

logger = logging.getLogger("orgon.migrations")

SCHEMA_DIR = Path(__file__).parent / "schema"


def run_migrations(db: Database):
    """Run all SQL schema files in order."""
    schema_files = sorted(SCHEMA_DIR.glob("*.sql"))

    for schema_file in schema_files:
        logger.info("Running migration: %s", schema_file.name)
        sql = schema_file.read_text()
        with db.get_connection() as conn:
            conn.executescript(sql)

    # Record migration state
    db.execute(
        "INSERT OR REPLACE INTO sync_state (key, value) VALUES (?, ?)",
        ("last_migration", schema_files[-1].name if schema_files else "none"),
    )
    logger.info("Migrations complete (%d schemas)", len(schema_files))
