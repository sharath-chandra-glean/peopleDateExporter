# Authentication and Authorization

This document explains how authentication and authorization work for the Cloud Run deployment.

## Overview

The People Data Exporter uses **Google Cloud IAM-based authentication** to secure API endpoints. When deployed on Cloud Run, all sync operations require proper authentication and authorization.

## How It Works

### 1. Token Verification
When a request is made to a protected endpoint:
1. The system extracts the Bearer token from the `Authorization` header
2. Verifies it's a valid Google Cloud identity token
3. Decodes the token to extract user information (email, etc.)

### 2. IAM Permission Check
After verifying the token:
1. Extracts the user's email from the token
2. Checks if the user has `run.routes.invoke` permission in the GCP project
3. Grants or denies access based on the permission check

### 3. Request Processing
- ✅ If authorized: Request proceeds to the endpoint
- ❌ If unauthorized: Returns 401 or 403 error

## Protected Endpoints

### `/sync` - **REQUIRES AUTH** 🔒
Triggers the data synchronization process.

**Required:** Valid Google Cloud identity token + Cloud Run Invoker permission

**Example:**
```bash
# Get your identity token
TOKEN=$(gcloud auth print-identity-token)

# Make authenticated request
curl -X POST \
  -H "Authorization: Bearer $TOKEN" \
  https://your-service-url/sync
```

**Responses:**
- `200` - Sync completed successfully
- `401` - Unauthorized (invalid or missing token)
- `403` - Forbidden (user lacks Cloud Run Invoker permission)
- `500` - Sync failed

### `/health` - **OPTIONAL AUTH**
Health check endpoint.

**Authentication:** Optional (works with or without auth)

**Example:**
```bash
# Without authentication
curl https://your-service-url/health

# With authentication (shows user info)
curl -H "Authorization: Bearer $TOKEN" \
  https://your-service-url/health
```

### `/` - **NO AUTH**
Service information endpoint (unprotected).

## Setting Up IAM Permissions

### Grant Cloud Run Invoker Permission

To allow a user or service account to trigger syncs:

```bash
# For a user
gcloud run services add-iam-policy-binding people-data-exporter \
  --region=us-central1 \
  --member="user:alice@example.com" \
  --role="roles/run.invoker"

# For a service account
gcloud run services add-iam-policy-binding people-data-exporter \
  --region=us-central1 \
  --member="serviceAccount:sync-scheduler@project.iam.gserviceaccount.com" \
  --role="roles/run.invoker"

# For Cloud Scheduler
gcloud run services add-iam-policy-binding people-data-exporter \
  --region=us-central1 \
  --member="serviceAccount:PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
  --role="roles/run.invoker"
```

### List Current Permissions

```bash
gcloud run services get-iam-policy people-data-exporter \
  --region=us-central1
```

### Revoke Permission

```bash
gcloud run services remove-iam-policy-binding people-data-exporter \
  --region=us-central1 \
  --member="user:alice@example.com" \
  --role="roles/run.invoker"
```

## Testing Authentication

### 1. Test with Valid Token

```bash
# Get your identity token
TOKEN=$(gcloud auth print-identity-token)

# Test sync endpoint
curl -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  https://your-service-url/sync
```

**Expected Response:**
```json
{
  "status": "success",
  "message": "Data sync completed successfully",
  "triggered_by": "your-email@example.com",
  "start_time": "2025-01-24T10:30:00.000000",
  "end_time": "2025-01-24T10:30:15.000000",
  "duration_seconds": 15.5
}
```

### 2. Test Without Token

```bash
curl -X POST https://your-service-url/sync
```

**Expected Response:**
```json
{
  "status": "error",
  "error": "unauthorized",
  "message": "Authorization token required. Please provide a Bearer token in the Authorization header."
}
```

### 3. Test with Invalid Token

```bash
curl -X POST \
  -H "Authorization: Bearer invalid-token-here" \
  https://your-service-url/sync
```

**Expected Response:**
```json
{
  "status": "error",
  "error": "unauthorized",
  "message": "Invalid authentication token"
}
```

### 4. Test Without IAM Permission

If your user doesn't have Cloud Run Invoker permission:

```json
{
  "status": "error",
  "error": "forbidden",
  "message": "Access denied. User your-email@example.com does not have Cloud Run Invoker permission in project your-project-id."
}
```

## Cloud Scheduler Authentication

Cloud Scheduler needs to authenticate when triggering the sync job.

### Option 1: Use Service Account (Recommended)

1. **Create service account:**
```bash
gcloud iam service-accounts create sync-scheduler \
  --display-name="Cloud Scheduler for People Sync"
```

2. **Grant Cloud Run Invoker permission:**
```bash
gcloud run services add-iam-policy-binding people-data-exporter \
  --region=us-central1 \
  --member="serviceAccount:sync-scheduler@PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/run.invoker"
```

3. **Configure Cloud Scheduler job:**
```bash
gcloud scheduler jobs create http daily-people-sync \
  --schedule="0 2 * * *" \
  --uri="https://your-service-url/sync" \
  --http-method=POST \
  --oidc-service-account-email="sync-scheduler@PROJECT_ID.iam.gserviceaccount.com" \
  --oidc-token-audience="https://your-service-url"
```

### Option 2: Use Default Compute Service Account

```bash
gcloud scheduler jobs create http daily-people-sync \
  --schedule="0 2 * * *" \
  --uri="https://your-service-url/sync" \
  --http-method=POST \
  --oidc-service-account-email="PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
  --oidc-token-audience="https://your-service-url"
```

## Security Best Practices

### 1. Principle of Least Privilege
Only grant Cloud Run Invoker permission to users/services that need it:
```bash
# Good: Specific users
gcloud run services add-iam-policy-binding people-data-exporter \
  --member="user:admin@example.com" \
  --role="roles/run.invoker"

# Bad: All authenticated users
gcloud run services add-iam-policy-binding people-data-exporter \
  --member="allAuthenticatedUsers" \
  --role="roles/run.invoker"
```

### 2. Use Service Accounts for Automation
- Create dedicated service accounts for Cloud Scheduler
- Don't use personal user accounts for automated jobs
- Rotate service account keys regularly

### 3. Monitor Access Logs
```bash
# View Cloud Run logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=people-data-exporter" \
  --limit=50 \
  --format=json
```

### 4. Set Up Alerts
Configure Cloud Monitoring alerts for:
- Unauthorized access attempts (401/403 responses)
- Failed sync operations
- Unusual API call patterns

## Environment Variables

The auth system requires:

```bash
# Set automatically by Cloud Run
GOOGLE_CLOUD_PROJECT=your-project-id

# Or set manually
GCP_PROJECT_ID=your-project-id
```

## Troubleshooting

### "Authorization token required"
**Problem:** No token in request  
**Solution:** Add `Authorization: Bearer <token>` header

### "Invalid authentication token"
**Problem:** Token is malformed or expired  
**Solution:** Get a fresh token with `gcloud auth print-identity-token`

### "Access denied. User does not have Cloud Run Invoker permission"
**Problem:** User lacks IAM permission  
**Solution:** Grant `roles/run.invoker` role:
```bash
gcloud run services add-iam-policy-binding people-data-exporter \
  --member="user:your-email@example.com" \
  --role="roles/run.invoker"
```

### "Server configuration error: project ID not set"
**Problem:** GCP_PROJECT_ID environment variable missing  
**Solution:** Set in Cloud Run service:
```bash
gcloud run services update people-data-exporter \
  --set-env-vars=GCP_PROJECT_ID=your-project-id
```

### Token Expires Quickly
**Problem:** Identity tokens expire after 1 hour  
**Solution:** 
- For manual testing: Get a fresh token before each request
- For automation: Use service accounts with Cloud Scheduler (auto-refreshes)

## Code Reference

### Apply Authentication to Endpoint

```python
from src.auth import require_auth, optional_auth

# Require authentication
@app.route('/protected', methods=['POST'])
@require_auth
def protected_endpoint():
    user_email = request.user_email  # Available after auth
    return {'user': user_email}

# Optional authentication
@app.route('/optional', methods=['GET'])
@optional_auth
def optional_endpoint():
    user = getattr(request, 'user_email', None)
    return {'user': user or 'anonymous'}
```

### Check Permissions Programmatically

```python
from src.auth import check_cloud_run_invoker_permission

has_permission = check_cloud_run_invoker_permission(
    email='user@example.com',
    project_id='my-project'
)
```

## Related Documentation

- [Google Cloud IAM Documentation](https://cloud.google.com/iam/docs)
- [Cloud Run Authentication](https://cloud.google.com/run/docs/authenticating/overview)
- [Cloud Scheduler OIDC Authentication](https://cloud.google.com/scheduler/docs/http-target-auth)

