-- Migration 020: promote naive timestamp columns to TIMESTAMPTZ
-- Date: 2026-04-29
-- Purpose: Early migrations created some tables with `TIMESTAMP WITHOUT TIME
--          ZONE` and others with `TIMESTAMPTZ`. Service code uniformly writes
--          `datetime.now(timezone.utc)` — asyncpg refuses to bind tz-aware
--          values to naive columns and the wallet/transaction insert paths
--          have been crashing with:
--             "can't subtract offset-naive and offset-aware datetimes"
--
--          This migration converts every offending column in-place:
--             ALTER COLUMN x TYPE TIMESTAMPTZ USING x AT TIME ZONE 'UTC'
--          The existing data is interpreted as already-UTC (which is what
--          the app has been writing). After this point services can keep
--          using `datetime.now(timezone.utc)` and inserts succeed.
--
-- Idempotent: ALTER COLUMN ... TYPE TIMESTAMPTZ is a no-op when the column
-- is already that type. Safe to re-run.

BEGIN;

DO $$
DECLARE
    -- (table, column) pairs that were created naive and need promotion.
    targets text[][] := ARRAY[
        ['wallets',      'created_at'],
        ['wallets',      'updated_at'],
        ['wallets',      'synced_at'],
        ['transactions', 'created_at'],
        ['transactions', 'updated_at'],
        ['signatures',   'created_at'],
        ['contacts',     'created_at'],
        ['contacts',     'updated_at']
    ];
    t text;
    c text;
    current_type text;
    i int;
BEGIN
    FOR i IN 1 .. array_length(targets, 1) LOOP
        t := targets[i][1];
        c := targets[i][2];

        -- Skip if the table doesn't exist (e.g. fresh DB without legacy schema).
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.tables
             WHERE table_schema = 'public' AND table_name = t
        ) THEN
            CONTINUE;
        END IF;

        SELECT data_type INTO current_type
          FROM information_schema.columns
         WHERE table_schema = 'public' AND table_name = t AND column_name = c;

        IF current_type IS NULL THEN
            -- Column doesn't exist on this DB, skip.
            CONTINUE;
        END IF;

        IF current_type = 'timestamp without time zone' THEN
            EXECUTE format(
                'ALTER TABLE %I ALTER COLUMN %I TYPE TIMESTAMPTZ USING %I AT TIME ZONE ''UTC''',
                t, c, c
            );
            RAISE NOTICE 'Promoted %.% to TIMESTAMPTZ', t, c;
        END IF;
    END LOOP;
END $$;

COMMIT;
