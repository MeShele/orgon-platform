#!/bin/bash
# ASYSTEM ORGON - Partner API cURL Examples
# Requires: jq (for JSON pretty-printing)

# Configuration — set these in your environment or .env file
API_KEY="${ORGON_PARTNER_API_KEY:?Set ORGON_PARTNER_API_KEY}"
API_SECRET="${ORGON_PARTNER_API_SECRET:?Set ORGON_PARTNER_API_SECRET}"
BASE_URL="${ORGON_BASE_URL:-http://localhost:8890}"

# Common headers
HEADERS=(
  -H "X-API-Key: $API_KEY"
  -H "X-API-Secret: $API_SECRET"
  -H "Content-Type: application/json"
  -H "Accept: application/json"
)

# ============================================================================
# WALLET ENDPOINTS
# ============================================================================

echo "============================================================================"
echo "1. LIST WALLETS"
echo "============================================================================"
curl -s "${HEADERS[@]}" \
  "$BASE_URL/api/v1/partner/wallets?limit=50&offset=0" | jq .

echo ""
echo "============================================================================"
echo "2. LIST WALLETS (filtered by network)"
echo "============================================================================"
curl -s "${HEADERS[@]}" \
  "$BASE_URL/api/v1/partner/wallets?limit=50&offset=0&network_id=5010" | jq .

echo ""
echo "============================================================================"
echo "3. GET WALLET DETAILS"
echo "============================================================================"
WALLET_NAME="E55EF29AACC3C7B145258D930049023B"
curl -s "${HEADERS[@]}" \
  "$BASE_URL/api/v1/partner/wallets/$WALLET_NAME" | jq .

echo ""
echo "============================================================================"
echo "4. CREATE WALLET"
echo "============================================================================"
curl -s "${HEADERS[@]}" \
  -X POST \
  -d '{
    "name": "test-wallet-'$(date +%s)'",
    "network_id": 5010,
    "wallet_type": 1,
    "label": "Test Wallet"
  }' \
  "$BASE_URL/api/v1/partner/wallets" | jq .

# ============================================================================
# TRANSACTION ENDPOINTS
# ============================================================================

echo ""
echo "============================================================================"
echo "5. LIST TRANSACTIONS"
echo "============================================================================"
curl -s "${HEADERS[@]}" \
  "$BASE_URL/api/v1/partner/transactions?limit=50&offset=0" | jq .

echo ""
echo "============================================================================"
echo "6. LIST TRANSACTIONS (filtered by wallet)"
echo "============================================================================"
curl -s "${HEADERS[@]}" \
  "$BASE_URL/api/v1/partner/transactions?wallet_name=$WALLET_NAME&limit=50" | jq .

echo ""
echo "============================================================================"
echo "7. CREATE TRANSACTION"
echo "============================================================================"
curl -s "${HEADERS[@]}" \
  -X POST \
  -d '{
    "wallet_name": "'$WALLET_NAME'",
    "to_address": "TTestRecipientAddress123456789ABCDEF",
    "amount": "100.50",
    "token_id": null,
    "notes": "Test transaction via Partner API"
  }' \
  "$BASE_URL/api/v1/partner/transactions" | jq .

echo ""
echo "============================================================================"
echo "8. GET TRANSACTION DETAILS"
echo "============================================================================"
TX_UNID="example-unid-12345"
curl -s "${HEADERS[@]}" \
  "$BASE_URL/api/v1/partner/transactions/$TX_UNID" | jq .

# ============================================================================
# SIGNATURE ENDPOINTS
# ============================================================================

echo ""
echo "============================================================================"
echo "9. LIST PENDING SIGNATURES"
echo "============================================================================"
curl -s "${HEADERS[@]}" \
  "$BASE_URL/api/v1/partner/signatures/pending?limit=50" | jq .

echo ""
echo "============================================================================"
echo "10. APPROVE SIGNATURE"
echo "============================================================================"
SIG_ID="example-signature-id"
curl -s "${HEADERS[@]}" \
  -X POST \
  -d '{
    "signature_id": "'$SIG_ID'",
    "approved_by": "admin@example.com"
  }' \
  "$BASE_URL/api/v1/partner/signatures/approve" | jq .

echo ""
echo "============================================================================"
echo "11. REJECT SIGNATURE"
echo "============================================================================"
curl -s "${HEADERS[@]}" \
  -X POST \
  -d '{
    "signature_id": "'$SIG_ID'",
    "reason": "Insufficient funds"
  }' \
  "$BASE_URL/api/v1/partner/signatures/reject" | jq .

# ============================================================================
# NETWORK & TOKEN INFO
# ============================================================================

echo ""
echo "============================================================================"
echo "12. GET SUPPORTED NETWORKS"
echo "============================================================================"
curl -s "${HEADERS[@]}" \
  "$BASE_URL/api/v1/partner/networks" | jq .

echo ""
echo "============================================================================"
echo "13. GET TOKEN INFORMATION"
echo "============================================================================"
curl -s "${HEADERS[@]}" \
  "$BASE_URL/api/v1/partner/tokens-info" | jq .

echo ""
echo "============================================================================"
echo "✅ Partner API cURL Examples Complete!"
echo "============================================================================"
