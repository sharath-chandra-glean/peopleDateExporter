#!/bin/bash

# Test Cloud Run endpoints
# Usage: ./deploy/test-endpoints.sh

set -e

# Configuration
PROJECT_ID="${GCP_PROJECT_ID:-your-gcp-project-id}"
REGION="${GCP_REGION:-us-central1}"
SERVICE_NAME="people-data-exporter"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}=== Testing Cloud Run Endpoints ===${NC}"
echo ""

# Check if project ID is set
if [ "$PROJECT_ID" = "your-gcp-project-id" ]; then
    echo -e "${RED}Error: Please set GCP_PROJECT_ID environment variable${NC}"
    echo "Usage: GCP_PROJECT_ID=my-project ./deploy/test-endpoints.sh"
    exit 1
fi

# Get Cloud Run service URL
echo -e "${YELLOW}Getting service URL...${NC}"
SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" \
    --platform managed \
    --region "$REGION" \
    --project "$PROJECT_ID" \
    --format 'value(status.url)')

if [ -z "$SERVICE_URL" ]; then
    echo -e "${RED}Error: Could not find Cloud Run service '$SERVICE_NAME'${NC}"
    exit 1
fi

echo "Service URL: $SERVICE_URL"
echo ""

# Get authentication token
echo -e "${YELLOW}Getting authentication token...${NC}"
TOKEN=$(gcloud auth print-identity-token)

# Test root endpoint
echo -e "${GREEN}Testing root endpoint (/)...${NC}"
curl -H "Authorization: Bearer $TOKEN" "$SERVICE_URL/" | jq '.'
echo ""

# Test health endpoint
echo -e "${GREEN}Testing health check endpoint (/health)...${NC}"
HEALTH_RESPONSE=$(curl -w "\n%{http_code}" -H "Authorization: Bearer $TOKEN" "$SERVICE_URL/health")
HEALTH_CODE=$(echo "$HEALTH_RESPONSE" | tail -n1)
HEALTH_BODY=$(echo "$HEALTH_RESPONSE" | sed '$d')

echo "$HEALTH_BODY" | jq '.'
echo ""

if [ "$HEALTH_CODE" = "200" ]; then
    echo -e "${GREEN}✓ Health check passed${NC}"
else
    echo -e "${RED}✗ Health check failed (HTTP $HEALTH_CODE)${NC}"
fi
echo ""

# Ask before triggering sync
echo -e "${YELLOW}Do you want to trigger a sync job? (y/N)${NC}"
read -r response

if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
    echo ""
    echo -e "${GREEN}Triggering sync endpoint (/sync)...${NC}"
    echo "This may take several minutes..."
    echo ""
    
    SYNC_RESPONSE=$(curl -w "\n%{http_code}" \
        -X POST \
        -H "Authorization: Bearer $TOKEN" \
        "$SERVICE_URL/sync")
    
    SYNC_CODE=$(echo "$SYNC_RESPONSE" | tail -n1)
    SYNC_BODY=$(echo "$SYNC_RESPONSE" | sed '$d')
    
    echo "$SYNC_BODY" | jq '.'
    echo ""
    
    if [ "$SYNC_CODE" = "200" ]; then
        echo -e "${GREEN}✓ Sync completed successfully${NC}"
    else
        echo -e "${RED}✗ Sync failed (HTTP $SYNC_CODE)${NC}"
    fi
else
    echo "Skipping sync test"
fi

echo ""
echo -e "${GREEN}=== Testing Complete ===${NC}"

