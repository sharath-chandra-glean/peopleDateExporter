# GCP Deployment Guide - People Data Exporter

This guide provides step-by-step instructions for deploying the People Data Exporter to Google Cloud Platform (GCP) using Cloud Run and Cloud Scheduler.

## 📋 Table of Contents

- [Architecture Overview](#architecture-overview)
- [Prerequisites](#prerequisites)
- [Initial Setup](#initial-setup)
- [Deployment Steps](#deployment-steps)
- [Testing](#testing)
- [Monitoring and Troubleshooting](#monitoring-and-troubleshooting)
- [Cost Management](#cost-management)
- [FAQ](#faq)

---

## 🏗️ Architecture Overview

### Components

```
┌─────────────────┐
│ Cloud Scheduler │ (Daily cron at 2 AM)
└────────┬────────┘
         │ POST /sync
         │ (with OIDC auth)
         ▼
┌─────────────────┐
│   Cloud Run     │ (HTTP server with Flask)
│  Service        │ - GET /health (health check)
│                 │ - POST /sync (trigger sync)
│                 │ - GET / (info)
└────────┬────────┘
         │
         ├─────────► Keycloak API (fetch users/groups)
         │
         └─────────► Glean People API (push data)
```

### Why This Architecture?

| Component | Purpose | Benefits |
|-----------|---------|----------|
| **Cloud Run** | Containerized HTTP service | Pay per use, scales to zero, 60-min execution time |
| **Cloud Scheduler** | Cron job scheduler | Reliable, managed, automatic retries |
| **Secret Manager** | Store API credentials | Secure, encrypted, version controlled |
| **Artifact Registry** | Docker image storage | Integrated with Cloud Run, secure |

### Cost Breakdown

- **Cloud Run**: ~$0.50-$5/month (daily 5-10 min runs)
- **Secret Manager**: $0.06/secret/month × 7 = ~$0.42/month
- **Cloud Scheduler**: $0.10/job/month
- **Artifact Registry**: $0.10/GB/month
- **Total**: **~$1-6/month**

---

## ✅ Prerequisites

### Required Tools

Install the following on your local machine:

1. **gcloud CLI** (Google Cloud SDK)
   ```bash
   # macOS
   brew install google-cloud-sdk
   
   # Or download from: https://cloud.google.com/sdk/docs/install
   ```

2. **Docker**
   ```bash
   # macOS
   brew install docker
   
   # Or download from: https://www.docker.com/products/docker-desktop
   ```

3. **curl** and **jq** (for testing)
   ```bash
   brew install curl jq
   ```

### GCP Project Setup

1. **Create a GCP Project** (if you don't have one)
   ```bash
   gcloud projects create YOUR-PROJECT-ID --name="People Data Exporter"
   ```

2. **Set the project**
   ```bash
   gcloud config set project YOUR-PROJECT-ID
   ```

3. **Enable billing** on the project
   - Go to: https://console.cloud.google.com/billing
   - Link a billing account to your project

4. **Enable required APIs**
   ```bash
   gcloud services enable \
     run.googleapis.com \
     artifactregistry.googleapis.com \
     cloudscheduler.googleapis.com \
     secretmanager.googleapis.com \
     cloudbuild.googleapis.com
   ```

5. **Authenticate with gcloud**
   ```bash
   gcloud auth login
   gcloud auth configure-docker us-central1-docker.pkg.dev
   ```

---

## 🚀 Initial Setup

### 1. Create Artifact Registry Repository

```bash
export GCP_PROJECT_ID="YOUR-PROJECT-ID"
export GCP_REGION="us-central1"  # Change to your preferred region

gcloud artifacts repositories create people-exporter \
    --repository-format=docker \
    --location=$GCP_REGION \
    --description="Docker repository for People Data Exporter" \
    --project=$GCP_PROJECT_ID
```

### 2. Configure Environment Variables

Create deployment configuration:

```bash
cd deploy
cp .env.template .env
```

Edit `deploy/.env` with your values:

```bash
# GCP Project configuration
GCP_PROJECT_ID=your-actual-project-id
GCP_REGION=us-central1

# Docker image configuration
ARTIFACT_REGISTRY_REPO=people-exporter
IMAGE_TAG=latest

# Cloud Run configuration
MIN_INSTANCES=0        # Scale to zero when idle
MAX_INSTANCES=1        # Only 1 instance needed
CPU=1                  # 1 vCPU
MEMORY=512Mi           # 512 MB RAM
TIMEOUT=3600           # 60 minutes

# Cron schedule (2 AM daily PST)
CRON_SCHEDULE="0 2 * * *"
TIME_ZONE=America/Los_Angeles
```

Source the configuration:

```bash
export $(cat .env | xargs)
```

---

## 📦 Deployment Steps

### Step 1: Store Secrets in Secret Manager

Store your Keycloak and Glean credentials securely:

```bash
# Make sure your .env file (in project root) has all required secrets
cd /Users/sharath/Projects/peopleDataExporter
./deploy/setup-secrets.sh
```

This script will:
- Read credentials from your `.env` file
- Create secrets in Google Cloud Secret Manager
- Enable Secret Manager API

**Secrets created:**
- `KEYCLOAK_BASE_URL`
- `KEYCLOAK_REALM`
- `KEYCLOAK_CLIENT_ID`
- `KEYCLOAK_CLIENT_SECRET`
- `GLEAN_API_URL`
- `GLEAN_API_TOKEN`
- `GLEAN_DATASOURCE`

### Step 2: Build and Push Docker Image

Build the Docker image and push to Artifact Registry:

```bash
./deploy/build-and-push.sh
```

This script will:
1. Configure Docker authentication
2. Build the Docker image with Flask HTTP server
3. Tag the image appropriately
4. Push to Artifact Registry

**Expected output:**
```
=== Building and Pushing People Data Exporter to GCP ===
Building Docker image...
Image: us-central1-docker.pkg.dev/your-project/people-exporter/people-data-exporter:latest
...
Image pushed to: us-central1-docker.pkg.dev/...
```

### Step 3: Deploy to Cloud Run

Deploy the service to Cloud Run:

```bash
./deploy/deploy-cloud-run.sh
```

This script will:
1. Create Cloud Run service
2. Configure resource limits and scaling
3. Mount secrets as environment variables
4. Disable public access (authentication required)

**Expected output:**
```
=== Deploying People Data Exporter to Cloud Run ===
Deploying to Cloud Run...
Service URL: https://people-data-exporter-xxxxx-uc.a.run.app
```

**Important:** Save the Service URL for the next step!

### Step 4: Setup Cloud Scheduler

Create a daily cron job to trigger the sync:

```bash
./deploy/setup-scheduler.sh
```

This script will:
1. Create a service account for Cloud Scheduler
2. Grant Cloud Run invoker permissions
3. Create a scheduled job with automatic retries
4. Configure OIDC authentication

**Expected output:**
```
=== Cloud Scheduler Setup Complete ===
Job name: people-data-exporter-daily
Schedule: 0 2 * * * (America/Los_Angeles)
Target URL: https://people-data-exporter-xxxxx-uc.a.run.app/sync
```

---

## 🧪 Testing

### Test Endpoints Manually

Run the test script to verify all endpoints:

```bash
./deploy/test-endpoints.sh
```

This will test:
1. **Root endpoint** (`/`) - Service information
2. **Health check** (`/health`) - Service health status
3. **Sync endpoint** (`/sync`) - Trigger a manual sync (optional)

### Manual Testing Commands

**Health Check:**
```bash
SERVICE_URL=$(gcloud run services describe people-data-exporter \
    --region=$GCP_REGION \
    --format='value(status.url)')

curl -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
    $SERVICE_URL/health | jq '.'
```

**Expected Response:**
```json
{
  "status": "healthy",
  "service": "people-data-exporter",
  "timestamp": "2025-12-19T10:30:00.000000"
}
```

**Trigger Manual Sync:**
```bash
curl -X POST \
    -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
    $SERVICE_URL/sync | jq '.'
```

**Expected Response (Success):**
```json
{
  "status": "success",
  "message": "Data sync completed successfully",
  "start_time": "2025-12-19T10:30:00.000000",
  "end_time": "2025-12-19T10:35:00.000000",
  "duration_seconds": 300
}
```

### Test Cloud Scheduler Job

Manually trigger the scheduled job:

```bash
gcloud scheduler jobs run people-data-exporter-daily \
    --location=$GCP_REGION \
    --project=$GCP_PROJECT_ID
```

Check job execution:

```bash
gcloud scheduler jobs describe people-data-exporter-daily \
    --location=$GCP_REGION \
    --project=$GCP_PROJECT_ID
```

---

## 📊 Monitoring and Troubleshooting

### View Cloud Run Logs

**Real-time logs:**
```bash
gcloud run services logs tail people-data-exporter \
    --region=$GCP_REGION \
    --project=$GCP_PROJECT_ID
```

**Recent logs:**
```bash
gcloud logging read \
    'resource.type=cloud_run_revision AND resource.labels.service_name=people-data-exporter' \
    --limit 50 \
    --format json \
    --project=$GCP_PROJECT_ID
```

**Filter by severity:**
```bash
gcloud logging read \
    'resource.type=cloud_run_revision AND resource.labels.service_name=people-data-exporter AND severity>=ERROR' \
    --limit 20 \
    --project=$GCP_PROJECT_ID
```

### View Cloud Scheduler Logs

```bash
gcloud logging read \
    'resource.type=cloud_scheduler_job AND resource.labels.job_id=people-data-exporter-daily' \
    --limit 20 \
    --project=$GCP_PROJECT_ID
```

### Cloud Console Dashboards

1. **Cloud Run Dashboard:**
   https://console.cloud.google.com/run/detail/us-central1/people-data-exporter

2. **Cloud Scheduler Dashboard:**
   https://console.cloud.google.com/cloudscheduler

3. **Logs Explorer:**
   https://console.cloud.google.com/logs/query

### Common Issues

#### Issue: Authentication Failed

**Symptom:** `403 Forbidden` or `401 Unauthorized`

**Solution:**
```bash
# Verify service account has invoker role
gcloud run services get-iam-policy people-data-exporter \
    --region=$GCP_REGION
```

#### Issue: Sync Timeout

**Symptom:** Service times out after 60 minutes

**Solution:**
```bash
# Increase timeout (max 60 minutes)
gcloud run services update people-data-exporter \
    --timeout=3600 \
    --region=$GCP_REGION
```

#### Issue: Out of Memory

**Symptom:** `Container killed due to memory limit`

**Solution:**
```bash
# Increase memory allocation
gcloud run services update people-data-exporter \
    --memory=1Gi \
    --region=$GCP_REGION
```

#### Issue: Secret Access Denied

**Symptom:** `Error: failed to access secret`

**Solution:**
```bash
# Grant secret accessor role to Cloud Run service account
SERVICE_ACCOUNT=$(gcloud run services describe people-data-exporter \
    --region=$GCP_REGION \
    --format='value(spec.template.spec.serviceAccountName)')

for SECRET in KEYCLOAK_CLIENT_SECRET GLEAN_API_TOKEN; do
    gcloud secrets add-iam-policy-binding $SECRET \
        --member="serviceAccount:$SERVICE_ACCOUNT" \
        --role="roles/secretmanager.secretAccessor"
done
```

### Set Up Alerts

Create alert for failed syncs:

```bash
# This will notify you when the sync endpoint returns 500 errors
gcloud monitoring policies create \
    --notification-channels=YOUR_CHANNEL_ID \
    --display-name="People Exporter Sync Failures" \
    --condition-display-name="High error rate" \
    --condition-threshold-value=1 \
    --condition-threshold-duration=300s
```

---

## 💰 Cost Management

### Monitor Costs

View current costs:
```bash
gcloud billing accounts list
```

Visit billing dashboard:
https://console.cloud.google.com/billing

### Set Budget Alerts

```bash
gcloud billing budgets create \
    --billing-account=YOUR_BILLING_ACCOUNT_ID \
    --display-name="People Exporter Budget" \
    --budget-amount=10 \
    --threshold-rule=percent=50 \
    --threshold-rule=percent=90 \
    --threshold-rule=percent=100
```

### Optimize Costs

1. **Use minimum resources**
   - Set `MIN_INSTANCES=0` to scale to zero
   - Use smallest viable `MEMORY` and `CPU`

2. **Optimize Docker image**
   - Use multi-stage builds
   - Minimize layers
   - Use slim base images

3. **Reduce log volume**
   - Set `LOG_LEVEL=INFO` (not DEBUG) in production
   - Configure log retention policies

---

## 🔄 Updates and Maintenance

### Update the Application

1. **Make code changes**
2. **Rebuild and redeploy:**
   ```bash
   ./deploy/build-and-push.sh
   ./deploy/deploy-cloud-run.sh
   ```

### Update Secrets

```bash
# Update a single secret
echo -n "new-secret-value" | gcloud secrets versions add SECRET_NAME \
    --data-file=- \
    --project=$GCP_PROJECT_ID

# Or re-run setup script after updating .env
./deploy/setup-secrets.sh
```

### Update Cron Schedule

```bash
gcloud scheduler jobs update http people-data-exporter-daily \
    --schedule="0 3 * * *" \
    --location=$GCP_REGION \
    --project=$GCP_PROJECT_ID
```

### Rollback Deployment

```bash
# List revisions
gcloud run revisions list \
    --service=people-data-exporter \
    --region=$GCP_REGION

# Rollback to previous revision
gcloud run services update-traffic people-data-exporter \
    --to-revisions=REVISION_NAME=100 \
    --region=$GCP_REGION
```

---

## 🔐 Security Best Practices

1. **Use Secret Manager** for all sensitive data (already configured)
2. **Disable public access** (already configured with `--no-allow-unauthenticated`)
3. **Use service accounts** with minimum required permissions
4. **Enable audit logging:**
   ```bash
   gcloud logging sinks create people-exporter-audit \
       bigquery.googleapis.com/projects/$GCP_PROJECT_ID/datasets/audit_logs \
       --log-filter='resource.type="cloud_run_revision"'
   ```
5. **Rotate secrets regularly** (every 90 days recommended)
6. **Monitor for suspicious activity** using Cloud Monitoring

---

## ❓ FAQ

### Q: How do I change the sync schedule?

Update the `CRON_SCHEDULE` in `deploy/.env` and re-run:
```bash
./deploy/setup-scheduler.sh
```

### Q: Can I run multiple syncs simultaneously?

No, by design. The Cloud Run service is configured with `--concurrency=1` and `--max-instances=1` to ensure only one sync runs at a time.

### Q: How do I dry-run before production?

Set environment variable in Cloud Run:
```bash
gcloud run services update people-data-exporter \
    --set-env-vars DRY_RUN=true \
    --region=$GCP_REGION
```

### Q: What if my sync takes longer than 60 minutes?

Cloud Run has a maximum timeout of 60 minutes. Consider:
1. Using `MAX_USERS` to limit batch size
2. Implementing pagination
3. Using Cloud Run Jobs instead of Cloud Run Service

### Q: How do I deploy to multiple environments (dev/staging/prod)?

Create separate:
- GCP Projects
- Cloud Run services with environment suffixes
- Artifact Registry tags (`:dev`, `:staging`, `:prod`)

Example:
```bash
export ENV=staging
gcloud run deploy people-data-exporter-$ENV \
    --image=...:$ENV \
    --region=$GCP_REGION
```

### Q: Can I use this with other cloud providers?

Yes! The application is containerized and can run on:
- AWS: ECS Fargate + EventBridge
- Azure: Container Instances + Logic Apps
- Kubernetes: CronJob

---

## 📞 Support

For issues:
1. Check logs with `LOG_LEVEL=DEBUG`
2. Review this documentation
3. Check GCP Status: https://status.cloud.google.com/
4. Open an issue in the repository

---

## 📝 Summary Checklist

- [ ] GCP Project created and billing enabled
- [ ] Required APIs enabled
- [ ] Artifact Registry repository created
- [ ] Secrets stored in Secret Manager
- [ ] Docker image built and pushed
- [ ] Cloud Run service deployed
- [ ] Cloud Scheduler job configured
- [ ] Endpoints tested successfully
- [ ] Monitoring and alerts set up
- [ ] Documentation reviewed

**Congratulations!** 🎉 Your People Data Exporter is now running on GCP with automated daily syncs.

