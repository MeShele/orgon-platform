#!/bin/bash
# Apply Multi-Tenant Migrations to PostgreSQL
# Usage: ./apply_migrations.sh [local|production]

set -e  # Exit on error

MODE="${1:-local}"
MIGRATIONS_DIR="$(dirname "$0")"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}🔧 ORGON Multi-Tenant Migrations${NC}"
echo -e "${YELLOW}Mode: $MODE${NC}"
echo ""

# Determine DATABASE_URL
if [ "$MODE" = "local" ]; then
    DATABASE_URL="postgresql://orgon_user:orgon_dev_password@localhost:5432/orgon_db"
    echo -e "${GREEN}Using local dev database${NC}"
elif [ "$MODE" = "production" ]; then
    # Read from docker.env
    if [ -f "$(dirname "$0")/../../docker.env" ]; then
        export $(grep DATABASE_URL "$(dirname "$0")/../../docker.env" | xargs)
    else
        echo -e "${RED}❌ docker.env not found${NC}"
        exit 1
    fi
    echo -e "${YELLOW}⚠️  WARNING: Applying to PRODUCTION database${NC}"
    read -p "Type 'YES' to confirm: " CONFIRM
    if [ "$CONFIRM" != "YES" ]; then
        echo -e "${RED}Aborted.${NC}"
        exit 1
    fi
else
    echo -e "${RED}❌ Invalid mode. Use: local or production${NC}"
    exit 1
fi

# Check psql
if ! command -v psql &> /dev/null; then
    echo -e "${RED}❌ psql not found. Install PostgreSQL client.${NC}"
    exit 1
fi

# Test connection
echo -e "${YELLOW}Testing database connection...${NC}"
if ! psql "$DATABASE_URL" -c "SELECT 1" > /dev/null 2>&1; then
    echo -e "${RED}❌ Cannot connect to database${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Connection successful${NC}"
echo ""

# Apply migrations
MIGRATIONS=(
    "001_create_organizations.sql"
    "002_add_tenant_columns.sql"
    "003_create_user_organizations.sql"
    "004_create_tenant_settings.sql"
    "005_enable_rls_policies.sql"
)

for MIGRATION in "${MIGRATIONS[@]}"; do
    echo -e "${YELLOW}Applying: $MIGRATION${NC}"
    
    if psql "$DATABASE_URL" -f "$MIGRATIONS_DIR/$MIGRATION" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Applied: $MIGRATION${NC}"
    else
        echo -e "${RED}❌ Failed: $MIGRATION${NC}"
        echo -e "${YELLOW}Rolling back...${NC}"
        # Note: Add rollback logic here if needed
        exit 1
    fi
done

echo ""
echo -e "${GREEN}🎉 All migrations applied successfully!${NC}"
echo ""

# Verify tables
echo -e "${YELLOW}Verifying tables...${NC}"
TABLES=$(psql "$DATABASE_URL" -t -c "SELECT tablename FROM pg_tables WHERE schemaname = 'public' AND tablename IN ('organizations', 'user_organizations', 'organization_settings')")
echo "$TABLES"

if echo "$TABLES" | grep -q "organizations"; then
    echo -e "${GREEN}✅ organizations table exists${NC}"
else
    echo -e "${RED}❌ organizations table not found${NC}"
fi

if echo "$TABLES" | grep -q "user_organizations"; then
    echo -e "${GREEN}✅ user_organizations table exists${NC}"
else
    echo -e "${RED}❌ user_organizations table not found${NC}"
fi

if echo "$TABLES" | grep -q "organization_settings"; then
    echo -e "${GREEN}✅ organization_settings table exists${NC}"
else
    echo -e "${RED}❌ organization_settings table not found${NC}"
fi

echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Apply seed data: psql \$DATABASE_URL -f seed_test_organizations.sql"
echo "2. Test RLS: Follow instructions in README.md"
echo "3. Update backend models and services"
echo ""
