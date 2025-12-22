#!/bin/bash

# Deploy People Data Exporter to Cloud Run
# Usage: ./deploy/deploy-cloud-run.sh

set -e

# Configuration - Update these values for your GCP project
PROJECT_ID="${GCP_PROJECT_ID:-your-gcp-project-id}"
REGION="${GCP_REGION:-us-central1}"
REPOSITORY="${ARTIFACT_REGISTRY_REPO:-people-exporter}"
IMAGE_NAME="people-data-exporter"
TAG="${IMAGE_TAG:-latest}"
SERVICE_NAME="people-data-exporter"

# Cloud Run Configuration
MIN_INSTANCES="${MIN_INSTANCES:-0}"  # Scale to zero when idle
MAX_INSTANCES="${MAX_INSTANCES:-1}"  # Only 1 instance needed for batch job
CPU="${CPU:-1}"
MEMORY="${MEMORY:-512Mi}"
TIMEOUT="${TIMEOUT:-3600}"  # 60 minutes (3600 seconds)
CONCURRENCY="${CONCURRENCY:-1}"  # Process one sync at a time

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}=== Deploying People Data Exporter to Cloud Run ===${NC}"
echo ""

# Check if project ID is set
if [ "$PROJECT_ID" = "your-gcp-project-id" ]; then
    echo -e "${RED}Error: Please set GCP_PROJECT_ID environment variable${NC}"
    echo "Usage: GCP_PROJECT_ID=my-project ./deploy/deploy-cloud-run.sh"
    exit 1
fi

# Build image name
FULL_IMAGE_NAME="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/${IMAGE_NAME}:${TAG}"

echo -e "${YELLOW}Deploying service: $SERVICE_NAME${NC}"
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo "Image: $FULL_IMAGE_NAME"
echo ""

# Check if .env file exists for reference
if [ -f ".env" ]; then
    echo -e "${YELLOW}Note: Found .env file. Make sure secrets are stored in Secret Manager!${NC}"
    echo "See: ./deploy/setup-secrets.sh"
    echo ""
fi

# Deploy to Cloud Run
echo -e "${GREEN}Deploying to Cloud Run...${NC}"
echo ""

gcloud run deploy "$SERVICE_NAME" \
    --image "$FULL_IMAGE_NAME" \
    --platform managed \
    --region "$REGION" \
    --project "$PROJECT_ID" \
    --min-instances "$MIN_INSTANCES" \
    --max-instances "$MAX_INSTANCES" \
    --cpu "$CPU" \
    --memory "$MEMORY" \
    --timeout "$TIMEOUT" \
    --concurrency "$CONCURRENCY" \
    --no-allow-unauthenticated \
    --set-env-vars "LOG_LEVEL=INFO" \
    --set-secrets "KEYCLOAK_BASE_URL=KEYCLOAK_BASE_URL:latest,\
KEYCLOAK_REALM=KEYCLOAK_REALM:latest,\
KEYCLOAK_CLIENT_ID=KEYCLOAK_CLIENT_ID:latest,\
KEYCLOAK_CLIENT_SECRET=KEYCLOAK_CLIENT_SECRET:latest,\
GLEAN_API_URL=GLEAN_API_URL:latest,\
GLEAN_API_TOKEN=GLEAN_API_TOKEN:latest,\
GLEAN_DATASOURCE=GLEAN_DATASOURCE:latest"

echo ""
echo -e "${GREEN}=== Deployment Complete ===${NC}"
echo ""
echo "Service URL:"
gcloud run services describe "$SERVICE_NAME" \
    --platform managed \
    --region "$REGION" \
    --project "$PROJECT_ID" \
    --format 'value(status.url)'

echo ""
echo "Next steps:"
echo "1. Test the health endpoint manually"
echo "2. Set up Cloud Scheduler: ./deploy/setup-scheduler.sh"
echo ""
echo "To view logs:"
echo "gcloud logging read 'resource.type=cloud_run_revision AND resource.labels.service_name=$SERVICE_NAME' --limit 50 --format json"

