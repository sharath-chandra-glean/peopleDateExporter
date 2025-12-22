#!/bin/bash

# Store secrets in Google Cloud Secret Manager
# Usage: ./deploy/setup-secrets.sh

set -e

# Configuration
PROJECT_ID="${GCP_PROJECT_ID:-your-gcp-project-id}"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}=== Setting up Secret Manager for People Data Exporter ===${NC}"
echo ""

# Check if project ID is set
if [ "$PROJECT_ID" = "your-gcp-project-id" ]; then
    echo -e "${RED}Error: Please set GCP_PROJECT_ID environment variable${NC}"
    echo "Usage: GCP_PROJECT_ID=my-project ./deploy/setup-secrets.sh"
    exit 1
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo -e "${RED}Error: .env file not found${NC}"
    echo "Please create .env file with your configuration"
    exit 1
fi

echo -e "${YELLOW}Reading secrets from .env file...${NC}"
echo ""

# Source the .env file
set -a
source .env
set +a

# Enable Secret Manager API
echo -e "${YELLOW}Enabling Secret Manager API...${NC}"
gcloud services enable secretmanager.googleapis.com --project="$PROJECT_ID"

# Function to create or update secret
create_or_update_secret() {
    local secret_name=$1
    local secret_value=$2
    
    if [ -z "$secret_value" ]; then
        echo -e "${YELLOW}Skipping $secret_name (not set in .env)${NC}"
        return
    fi
    
    # Check if secret exists
    if gcloud secrets describe "$secret_name" --project="$PROJECT_ID" &>/dev/null; then
        echo -e "${YELLOW}Updating secret: $secret_name${NC}"
        echo -n "$secret_value" | gcloud secrets versions add "$secret_name" \
            --project="$PROJECT_ID" \
            --data-file=-
    else
        echo -e "${GREEN}Creating secret: $secret_name${NC}"
        echo -n "$secret_value" | gcloud secrets create "$secret_name" \
            --project="$PROJECT_ID" \
            --replication-policy="automatic" \
            --data-file=-
    fi
}

echo -e "${GREEN}Creating/Updating secrets...${NC}"
echo ""

# Create secrets for all sensitive configuration
create_or_update_secret "KEYCLOAK_BASE_URL" "$KEYCLOAK_BASE_URL"
create_or_update_secret "KEYCLOAK_REALM" "$KEYCLOAK_REALM"
create_or_update_secret "KEYCLOAK_CLIENT_ID" "$KEYCLOAK_CLIENT_ID"
create_or_update_secret "KEYCLOAK_CLIENT_SECRET" "$KEYCLOAK_CLIENT_SECRET"
create_or_update_secret "GLEAN_API_URL" "$GLEAN_API_URL"
create_or_update_secret "GLEAN_API_TOKEN" "$GLEAN_API_TOKEN"
create_or_update_secret "GLEAN_DATASOURCE" "$GLEAN_DATASOURCE"

echo ""
echo -e "${GREEN}=== Secrets Setup Complete ===${NC}"
echo ""
echo "Secrets created in project: $PROJECT_ID"
echo ""
echo "To grant Cloud Run service account access to secrets:"
echo "Run the following for the Cloud Run service account:"
echo ""
echo "SERVICE_ACCOUNT=\$(gcloud run services describe people-data-exporter --region=us-central1 --format='value(spec.template.spec.serviceAccountName)')"
echo "gcloud secrets add-iam-policy-binding KEYCLOAK_CLIENT_SECRET --member=\"serviceAccount:\$SERVICE_ACCOUNT\" --role=\"roles/secretmanager.secretAccessor\""
echo ""
echo "Or deploy Cloud Run with ./deploy/deploy-cloud-run.sh which automatically configures secret access"

