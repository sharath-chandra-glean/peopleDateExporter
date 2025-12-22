#!/bin/bash

# Setup Cloud Scheduler to trigger daily sync
# Usage: ./deploy/setup-scheduler.sh

set -e

# Configuration
PROJECT_ID="${GCP_PROJECT_ID:-your-gcp-project-id}"
REGION="${GCP_REGION:-us-central1}"
SERVICE_NAME="people-data-exporter"
JOB_NAME="people-data-exporter-daily"
SCHEDULE="${CRON_SCHEDULE:-0 2 * * *}"  # Default: 2 AM daily
TIME_ZONE="${TIME_ZONE:-America/Los_Angeles}"  # Update to your timezone

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}=== Setting up Cloud Scheduler ===${NC}"
echo ""

# Check if project ID is set
if [ "$PROJECT_ID" = "your-gcp-project-id" ]; then
    echo -e "${RED}Error: Please set GCP_PROJECT_ID environment variable${NC}"
    echo "Usage: GCP_PROJECT_ID=my-project ./deploy/setup-scheduler.sh"
    exit 1
fi

# Enable Cloud Scheduler API
echo -e "${YELLOW}Enabling Cloud Scheduler API...${NC}"
gcloud services enable cloudscheduler.googleapis.com --project="$PROJECT_ID"

# Get Cloud Run service URL
echo -e "${YELLOW}Getting Cloud Run service URL...${NC}"
SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" \
    --platform managed \
    --region "$REGION" \
    --project "$PROJECT_ID" \
    --format 'value(status.url)')

if [ -z "$SERVICE_URL" ]; then
    echo -e "${RED}Error: Could not find Cloud Run service '$SERVICE_NAME'${NC}"
    echo "Please deploy the service first: ./deploy/deploy-cloud-run.sh"
    exit 1
fi

SYNC_URL="${SERVICE_URL}/sync"
HEALTH_URL="${SERVICE_URL}/health"

echo "Service URL: $SERVICE_URL"
echo "Sync endpoint: $SYNC_URL"
echo ""

# Create service account for Cloud Scheduler
SERVICE_ACCOUNT_NAME="cloud-scheduler-invoker"
SERVICE_ACCOUNT_EMAIL="${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

echo -e "${YELLOW}Creating service account for Cloud Scheduler...${NC}"
if ! gcloud iam service-accounts describe "$SERVICE_ACCOUNT_EMAIL" --project="$PROJECT_ID" &>/dev/null; then
    gcloud iam service-accounts create "$SERVICE_ACCOUNT_NAME" \
        --display-name="Cloud Scheduler Invoker for People Data Exporter" \
        --project="$PROJECT_ID"
    echo -e "${GREEN}Service account created${NC}"
else
    echo -e "${YELLOW}Service account already exists${NC}"
fi

# Grant invoker permission to Cloud Run service
echo -e "${YELLOW}Granting Cloud Run Invoker role...${NC}"
gcloud run services add-iam-policy-binding "$SERVICE_NAME" \
    --member="serviceAccount:${SERVICE_ACCOUNT_EMAIL}" \
    --role="roles/run.invoker" \
    --region="$REGION" \
    --project="$PROJECT_ID"

# Delete existing job if it exists
if gcloud scheduler jobs describe "$JOB_NAME" --location="$REGION" --project="$PROJECT_ID" &>/dev/null; then
    echo -e "${YELLOW}Deleting existing scheduler job...${NC}"
    gcloud scheduler jobs delete "$JOB_NAME" \
        --location="$REGION" \
        --project="$PROJECT_ID" \
        --quiet
fi

# Create Cloud Scheduler job
echo -e "${GREEN}Creating Cloud Scheduler job...${NC}"
echo "Schedule: $SCHEDULE ($TIME_ZONE)"
echo ""

gcloud scheduler jobs create http "$JOB_NAME" \
    --location="$REGION" \
    --schedule="$SCHEDULE" \
    --time-zone="$TIME_ZONE" \
    --uri="$SYNC_URL" \
    --http-method=POST \
    --oidc-service-account-email="$SERVICE_ACCOUNT_EMAIL" \
    --oidc-token-audience="$SERVICE_URL" \
    --max-retry-attempts=2 \
    --max-retry-duration=3600s \
    --min-backoff-duration=30s \
    --max-backoff-duration=300s \
    --project="$PROJECT_ID"

echo ""
echo -e "${GREEN}=== Cloud Scheduler Setup Complete ===${NC}"
echo ""
echo "Job name: $JOB_NAME"
echo "Schedule: $SCHEDULE ($TIME_ZONE)"
echo "Target URL: $SYNC_URL"
echo ""
echo "To manually trigger the job now:"
echo "gcloud scheduler jobs run $JOB_NAME --location=$REGION --project=$PROJECT_ID"
echo ""
echo "To view job history:"
echo "gcloud scheduler jobs describe $JOB_NAME --location=$REGION --project=$PROJECT_ID"
echo ""
echo "To test health check manually:"
echo "curl -H \"Authorization: Bearer \$(gcloud auth print-identity-token)\" $HEALTH_URL"

