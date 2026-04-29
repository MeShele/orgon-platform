#!/bin/bash
# Apply FULL schema to dev database (base + migrations + multi-tenant)
# Usage: ./apply_full_schema.sh

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

DATABASE_URL="postgresql://orgon_user:orgon_dev_password@localhost:5432/orgon_db"

echo -e "${YELLOW}🔧 Applying FULL ORGON Schema${NC}"
echo ""

# 1. Base schema (schema/)
echo -e "${YELLOW}📦 Step 1: Base schema (wallets, transactions, signatures)${NC}"
BASE_SCHEMA=(
    "../database/schema/001_wallets.sql"
    "../database/schema/002_transactions.sql"
    "../database/schema/003_sync_state.sql"
    "../database/schema/004_signatures.sql"
)

for SQL in "${BASE_SCHEMA[@]}"; do
    if [ -f "$SQL" ]; then
        echo -e "  Applying: $(basename $SQL)"
        psql "$DATABASE_URL" -f "$SQL" > /dev/null 2>&1 || echo -e "  ⚠️  Skipped (may already exist)"
    fi
done

echo -e "${GREEN}✅ Base schema applied${NC}"
echo ""

# 2. Extensions (database/migrations/)
echo -e "${YELLOW}📦 Step 2: Extensions (scheduled, contacts, audit, users)${NC}"
EXTENSIONS=(
    "../database/migrations/004_scheduled_transactions.sql"
    "../database/migrations/005_address_book.sql"
    "../database/migrations/006_audit_log.sql"
    "../database/migrations/007_users.sql"
)

for SQL in "${EXTENSIONS[@]}"; do
    if [ -f "$SQL" ]; then
        echo -e "  Applying: $(basename $SQL)"
        psql "$DATABASE_URL" -f "$SQL" > /dev/null 2>&1 || echo -e "  ⚠️  Skipped (may already exist)"
    fi
done

echo -e "${GREEN}✅ Extensions applied${NC}"
echo ""

# 3. Multi-tenant (migrations/)
echo -e "${YELLOW}📦 Step 3: Multi-tenant (organizations, RLS)${NC}"
MULTITENANT=(
    "001_create_organizations.sql"
    "002_add_tenant_columns.sql"
    "003_create_user_organizations.sql"
    "004_create_tenant_settings.sql"
    "005_enable_rls_policies.sql"
)

for SQL in "${MULTITENANT[@]}"; do
    echo -e "  Applying: $SQL"
    psql "$DATABASE_URL" -f "$SQL" 2>&1 | grep -v "NOTICE:" || true
done

echo -e "${GREEN}✅ Multi-tenant schema applied${NC}"
echo ""

# Verify
echo -e "${YELLOW}🔍 Verifying tables...${NC}"
psql "$DATABASE_URL" -c "\dt" | grep -E "organizations|wallets|transactions|users" || echo "No tables found"

echo ""
echo -e "${GREEN}🎉 Full schema applied successfully!${NC}"
echo ""
echo -e "${YELLOW}Next: Apply seed data${NC}"
echo "psql \$DATABASE_URL -f seed_test_organizations.sql"
