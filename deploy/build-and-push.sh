#!/bin/bash

# Build and Push Docker Image to Google Artifact Registry
# Usage: ./deploy/build-and-push.sh

set -e

# Configuration - Update these values for your GCP project
PROJECT_ID="${GCP_PROJECT_ID:-your-gcp-project-id}"
REGION="${GCP_REGION:-us-central1}"
REPOSITORY="${ARTIFACT_REGISTRY_REPO:-people-exporter}"
IMAGE_NAME="people-data-exporter"
TAG="${IMAGE_TAG:-latest}"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Building and Pushing People Data Exporter to GCP ===${NC}"
echo ""

# Verify gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}Error: gcloud CLI is not installed${NC}"
    echo "Install from: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Verify docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker is not installed${NC}"
    exit 1
fi

# Check if project ID is set
if [ "$PROJECT_ID" = "your-gcp-project-id" ]; then
    echo -e "${RED}Error: Please set GCP_PROJECT_ID environment variable or update the script${NC}"
    echo "Usage: GCP_PROJECT_ID=my-project ./deploy/build-and-push.sh"
    exit 1
fi

# Set gcloud project
echo -e "${YELLOW}Setting GCP project to: $PROJECT_ID${NC}"
gcloud config set project "$PROJECT_ID"

# Configure Docker to use gcloud credentials
echo -e "${YELLOW}Configuring Docker authentication...${NC}"
gcloud auth configure-docker "${REGION}-docker.pkg.dev" --quiet

# Build image name
FULL_IMAGE_NAME="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/${IMAGE_NAME}:${TAG}"

echo ""
echo -e "${GREEN}Building Docker image...${NC}"
echo "Image: $FULL_IMAGE_NAME"
echo ""

# Build the Docker image for amd64/linux (required by Cloud Run)
# Use --platform flag to ensure compatibility with Cloud Run
echo -e "${YELLOW}Building for linux/amd64 platform (Cloud Run requirement)${NC}"
docker build --platform linux/amd64 -t "$FULL_IMAGE_NAME" .

echo ""
echo -e "${GREEN}Pushing image to Artifact Registry...${NC}"
echo ""

# Push the image
docker push "$FULL_IMAGE_NAME"

echo ""
echo -e "${GREEN}=== Build and Push Complete ===${NC}"
echo ""
echo "Image pushed to: $FULL_IMAGE_NAME"
echo ""
echo "Next steps:"
echo "1. Deploy to Cloud Run: ./deploy/deploy-cloud-run.sh"
echo "2. Set up Cloud Scheduler: ./deploy/setup-scheduler.sh"

