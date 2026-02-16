# Quick Start - GCP Deployment

Deploy the People Data Exporter to Google Cloud Platform in ~10 minutes.

## Prerequisites

- Google Cloud account with billing enabled
- `gcloud` CLI installed and authenticated
- Docker installed
- Project `.env` file configured

## Step-by-Step Deployment

### 1. Set Your GCP Project

```bash
export GCP_PROJECT_ID="glean-sandbox"
export GCP_REGION="us-central1"

gcloud config set project $GCP_PROJECT_ID
```

### 2. Enable Required APIs

```bash
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  cloudscheduler.googleapis.com \
  secretmanager.googleapis.com
```

### 3. Create Artifact Registry

```bash
gcloud artifacts repositories create people-exporter \
    --repository-format=docker \
    --location=$GCP_REGION \
    --description="People Data Exporter"
```

### 4. Run Deployment Scripts

```bash
# Store secrets (reads from your .env file)
./deploy/setup-secrets.sh

# Build and push Docker image
./deploy/build-and-push.sh

# Deploy to Cloud Run
./deploy/deploy-cloud-run.sh

# Setup daily cron job
./deploy/setup-scheduler.sh
```

### 5. Test the Deployment

```bash
# Test all endpoints
./deploy/test-endpoints.sh

# Or manually test health check
SERVICE_URL=$(gcloud run services describe people-data-exporter \
    --region=$GCP_REGION \
    --format='value(status.url)')

curl -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
    $SERVICE_URL/health
```

## What Gets Deployed?

- **Cloud Run Service**: HTTP server with sync and health check endpoints
- **Cloud Scheduler**: Daily cron job at 2 AM
- **Secret Manager**: Secure storage for API credentials
- **Artifact Registry**: Docker image storage

## Cost

Approximately **$1-6/month** for daily runs.

## Next Steps

- [Read full deployment guide](./GCP_DEPLOYMENT.md)
- Configure monitoring and alerts
- Set up budget alerts
- Review logs after first sync

## Troubleshooting

**View logs:**
```bash
gcloud run services logs tail people-data-exporter --region=$GCP_REGION
```

**Manually trigger sync:**
```bash
gcloud scheduler jobs run people-data-exporter-daily --location=$GCP_REGION
```

**Update environment:**
```bash
gcloud run services update people-data-exporter \
    --set-env-vars KEY=VALUE \
    --region=$GCP_REGION
```

## Architecture

```
Cloud Scheduler (daily cron)
    ↓ POST /sync
Cloud Run Service (Flask)
    ↓
Keycloak API → Glean API
```

For detailed information, see [GCP_DEPLOYMENT.md](./GCP_DEPLOYMENT.md).

