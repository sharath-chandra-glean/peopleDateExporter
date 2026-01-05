#!/bin/bash

# Test authentication for Cloud Run deployment
# This script tests various authentication scenarios

set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get service URL from environment or argument
SERVICE_URL=${1:-${SERVICE_URL}}

if [ -z "$SERVICE_URL" ]; then
    echo -e "${RED}Error: SERVICE_URL not provided${NC}"
    echo "Usage: $0 <service-url>"
    echo "   or: SERVICE_URL=<url> $0"
    exit 1
fi

echo -e "${YELLOW}=== Testing Authentication ===${NC}"
echo "Service URL: $SERVICE_URL"
echo ""

# Test 1: Health check without auth (should work)
echo -e "${YELLOW}Test 1: Health check without authentication${NC}"
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "$SERVICE_URL/health")
if [ "$RESPONSE" -eq 200 ]; then
    echo -e "${GREEN}✓ PASS${NC} - Health check works without auth (HTTP $RESPONSE)"
else
    echo -e "${RED}✗ FAIL${NC} - Health check failed (HTTP $RESPONSE)"
fi
echo ""

# Test 2: Sync without auth (should fail with 401)
echo -e "${YELLOW}Test 2: Sync without authentication (should fail)${NC}"
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$SERVICE_URL/sync")
if [ "$RESPONSE" -eq 401 ]; then
    echo -e "${GREEN}✓ PASS${NC} - Correctly rejected (HTTP $RESPONSE)"
else
    echo -e "${RED}✗ FAIL${NC} - Unexpected response (HTTP $RESPONSE, expected 401)"
fi
echo ""

# Test 3: Sync with invalid token (should fail with 401)
echo -e "${YELLOW}Test 3: Sync with invalid token (should fail)${NC}"
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" \
    -X POST \
    -H "Authorization: Bearer invalid-token-12345" \
    "$SERVICE_URL/sync")
if [ "$RESPONSE" -eq 401 ]; then
    echo -e "${GREEN}✓ PASS${NC} - Invalid token rejected (HTTP $RESPONSE)"
else
    echo -e "${RED}✗ FAIL${NC} - Unexpected response (HTTP $RESPONSE, expected 401)"
fi
echo ""

# Test 4: Get identity token and test with valid auth
echo -e "${YELLOW}Test 4: Getting identity token from gcloud${NC}"
TOKEN=$(gcloud auth print-identity-token 2>/dev/null)

if [ -z "$TOKEN" ]; then
    echo -e "${RED}✗ SKIP${NC} - Could not get identity token. Run 'gcloud auth login' first."
    echo ""
else
    echo -e "${GREEN}✓ Token obtained${NC}"
    echo "Token (first 50 chars): ${TOKEN:0:50}..."
    echo ""
    
    # Test 4a: Health check with auth
    echo -e "${YELLOW}Test 4a: Health check with authentication${NC}"
    RESPONSE=$(curl -s "$SERVICE_URL/health" \
        -H "Authorization: Bearer $TOKEN")
    echo "Response: $RESPONSE"
    
    if echo "$RESPONSE" | grep -q "authenticated_user"; then
        echo -e "${GREEN}✓ PASS${NC} - Authenticated user info returned"
    else
        echo -e "${YELLOW}⚠ WARNING${NC} - No authenticated user info (might be OK)"
    fi
    echo ""
    
    # Test 4b: Sync with valid auth
    echo -e "${YELLOW}Test 4b: Sync with valid authentication${NC}"
    echo "Note: This will trigger an actual sync if you have permissions!"
    echo "Press Ctrl+C to cancel or wait 5 seconds to continue..."
    sleep 5
    
    FULL_RESPONSE=$(curl -s -w "\nHTTP_STATUS:%{http_code}" \
        -X POST \
        -H "Authorization: Bearer $TOKEN" \
        -H "Content-Type: application/json" \
        "$SERVICE_URL/sync")
    
    BODY=$(echo "$FULL_RESPONSE" | sed -n '1,/^HTTP_STATUS:/p' | sed '$d')
    STATUS=$(echo "$FULL_RESPONSE" | grep "HTTP_STATUS:" | cut -d: -f2)
    
    echo "HTTP Status: $STATUS"
    echo "Response Body:"
    echo "$BODY" | python3 -m json.tool 2>/dev/null || echo "$BODY"
    
    if [ "$STATUS" -eq 200 ]; then
        echo -e "${GREEN}✓ PASS${NC} - Sync successful with valid auth"
    elif [ "$STATUS" -eq 403 ]; then
        echo -e "${YELLOW}⚠ EXPECTED${NC} - Forbidden: Your user lacks Cloud Run Invoker permission"
        echo "To fix, run:"
        echo "  gcloud run services add-iam-policy-binding people-data-exporter \\"
        echo "    --region=us-central1 \\"
        echo "    --member=\"user:\$(gcloud config get-value account)\" \\"
        echo "    --role=\"roles/run.invoker\""
    else
        echo -e "${RED}✗ FAIL${NC} - Unexpected response (HTTP $STATUS)"
    fi
    echo ""
fi

echo -e "${YELLOW}=== Summary ===${NC}"
echo "Authentication is working correctly if:"
echo "  ✓ Health checks work without auth"
echo "  ✓ Sync is rejected without auth (401)"
echo "  ✓ Sync is rejected with invalid token (401)"
echo "  ✓ Sync works with valid token + permissions (200)"
echo "  ✓ Sync is rejected with valid token but no permissions (403)"
echo ""
echo "For more information, see: AUTHENTICATION.md"

