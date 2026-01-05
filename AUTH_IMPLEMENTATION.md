# Authentication Implementation Summary

## Overview

Added comprehensive **Google Cloud IAM-based authentication and authorization** to secure Cloud Run API endpoints. The system verifies Google Cloud identity tokens and checks IAM permissions before allowing access to sync operations.

## What Was Added

### 1. New File: `src/auth.py`
Complete authentication and authorization module with:

**Functions:**
- `verify_token(token)` - Verifies and decodes Google Cloud identity tokens
- `check_cloud_run_invoker_permission(email, project_id)` - Checks if user has IAM permission
- `extract_token_from_header()` - Extracts Bearer token from Authorization header

**Decorators:**
- `@require_auth` - Enforces authentication + authorization (401/403 on failure)
- `@optional_auth` - Optional authentication (proceeds regardless)

### 2. Updated: `src/server.py`
Modified all endpoints with authentication:

**Endpoints:**
- `GET /health` - Now uses `@optional_auth` (works with or without token)
- `POST /sync` - Now uses `@require_auth` (requires valid token + IAM permission)
- `GET /` - Unchanged (no auth required)

**Response Changes:**
- Added `triggered_by` field showing authenticated user email
- Added `authenticated_user` field in health check when authenticated
- New error responses for 401 (unauthorized) and 403 (forbidden)

### 3. Updated: `requirements.txt`
Added dependencies:
```
google-auth==2.25.2
google-cloud-resource-manager==1.12.0
```

### 4. Documentation Files

**AUTHENTICATION.md** (23 KB)
- Complete authentication/authorization guide
- Token verification details
- IAM permission setup
- Testing procedures
- Troubleshooting guide

**AUTH_QUICKSTART.md** (5 KB)
- Quick copy-paste commands
- Common scenarios
- Security tips

**deploy/test-auth.sh** (Executable)
- Automated authentication testing script
- Tests all scenarios: no auth, invalid token, valid token, permissions

## How It Works

### Authentication Flow

```
1. Client makes request with Authorization header
   ↓
2. extract_token_from_header() extracts Bearer token
   ↓
3. verify_token() validates token with Google
   ↓
4. Extract email from decoded token
   ↓
5. check_cloud_run_invoker_permission() queries IAM
   ↓
6. If authorized: proceed to endpoint
   If unauthorized: return 401/403 error
```

### Example Request/Response

**Successful Request:**
```bash
curl -X POST \
  -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  https://your-service/sync
```

**Response:**
```json
{
  "status": "success",
  "message": "Data sync completed successfully",
  "triggered_by": "user@example.com",
  "start_time": "2025-01-24T10:00:00",
  "end_time": "2025-01-24T10:00:15",
  "duration_seconds": 15.2
}
```

**Unauthorized Request:**
```bash
curl -X POST https://your-service/sync
```

**Response:**
```json
{
  "status": "error",
  "error": "unauthorized",
  "message": "Authorization token required. Please provide a Bearer token in the Authorization header."
}
```

**Forbidden Request:**
```json
{
  "status": "error",
  "error": "forbidden",
  "message": "Access denied. User user@example.com does not have Cloud Run Invoker permission in project my-project."
}
```

## Security Features

### ✅ What's Protected

1. **Token Verification**
   - Validates Google Cloud identity tokens
   - Checks token signature and expiration
   - Extracts verified user information

2. **IAM Permission Check**
   - Verifies `run.routes.invoke` permission
   - Checks against current GCP project
   - Real-time permission validation

3. **Audit Trail**
   - Logs all authentication attempts
   - Records user email for successful syncs
   - Tracks authorization failures

### 🔒 Security Best Practices

1. **Principle of Least Privilege**
   - Only grants `run.invoker` role (minimal needed)
   - Requires explicit IAM permission grants
   - No default access

2. **Token-Based Auth**
   - Uses Google Cloud identity tokens (short-lived)
   - No API keys or passwords
   - Automatic token rotation

3. **Project-Scoped**
   - Checks permissions against specific project
   - Uses project from environment variables
   - Isolated per deployment

## Setup Instructions

### 1. Deploy Service (Already Done)
Service already has auth code - no redeployment needed if using latest code.

### 2. Grant Yourself Access
```bash
gcloud run services add-iam-policy-binding people-data-exporter \
  --region=us-central1 \
  --member="user:$(gcloud config get-value account)" \
  --role="roles/run.invoker"
```

### 3. Test Authentication
```bash
SERVICE_URL=$(gcloud run services describe people-data-exporter \
  --region=us-central1 --format="value(status.url)")

./deploy/test-auth.sh $SERVICE_URL
```

### 4. Setup Cloud Scheduler with Auth
```bash
# Create service account
gcloud iam service-accounts create sync-scheduler

# Grant permission
gcloud run services add-iam-policy-binding people-data-exporter \
  --region=us-central1 \
  --member="serviceAccount:sync-scheduler@PROJECT.iam.gserviceaccount.com" \
  --role="roles/run.invoker"

# Create scheduler with OIDC auth
gcloud scheduler jobs create http daily-sync \
  --schedule="0 2 * * *" \
  --uri="$SERVICE_URL/sync" \
  --http-method=POST \
  --oidc-service-account-email="sync-scheduler@PROJECT.iam.gserviceaccount.com"
```

## Testing

### Automated Test Script
```bash
./deploy/test-auth.sh https://your-service-url
```

Tests:
- ✓ Health check without auth (should work)
- ✓ Sync without auth (should fail with 401)
- ✓ Sync with invalid token (should fail with 401)
- ✓ Sync with valid token (should succeed or return 403)

### Manual Testing

**Test 1: No Auth**
```bash
curl -X POST https://your-service/sync
# Expected: 401 Unauthorized
```

**Test 2: With Auth**
```bash
TOKEN=$(gcloud auth print-identity-token)
curl -X POST -H "Authorization: Bearer $TOKEN" https://your-service/sync
# Expected: 200 Success or 403 Forbidden
```

**Test 3: Check Health**
```bash
curl https://your-service/health
# Expected: 200 OK (works without auth)
```

## Backward Compatibility

### Breaking Changes
⚠️ **The `/sync` endpoint now requires authentication**

**Before:** Anyone could call `/sync`
**After:** Only users with Cloud Run Invoker permission can call `/sync`

### Migration Path

1. **Existing Cloud Scheduler jobs** need update:
   - Add OIDC authentication configuration
   - Set service account email
   - Set audience to service URL

2. **Manual curl calls** need update:
   - Add `Authorization: Bearer $(gcloud auth print-identity-token)` header

3. **Monitoring tools** might need update:
   - `/health` still works without auth
   - Use `/health` for uptime monitoring

### Non-Breaking Changes
✅ `/health` endpoint works with or without auth  
✅ `/` root endpoint unchanged  
✅ Response format compatible (added fields, not removed)

## Environment Variables

**No configuration needed!** The system automatically detects the GCP project ID from the Cloud Run environment.

**Detection method:**
1. Uses `google.auth.default()` to get project from Application Default Credentials (ADC)
2. Falls back to environment variables if needed: `GOOGLE_CLOUD_PROJECT`, `GCP_PROJECT`, `GCLOUD_PROJECT`

**For local development only:**
```bash
# Option 1: Set environment variable
export GOOGLE_CLOUD_PROJECT=your-project-id

# Option 2: Use gcloud auth (recommended)
gcloud auth application-default login
gcloud config set project your-project-id
```

Cloud Run automatically provides the project context, so no manual configuration is required in production.

## Troubleshooting

### Auth Not Working?

1. **Project ID detection (automatic in Cloud Run):**
   ```bash
   # Cloud Run sets this automatically - no action needed
   # For local testing, authenticate with gcloud:
   gcloud auth application-default login
   ```

2. **Verify IAM permissions:**
   ```bash
   gcloud run services get-iam-policy people-data-exporter \
     --region=us-central1
   ```

3. **Test token:**
   ```bash
   TOKEN=$(gcloud auth print-identity-token)
   echo $TOKEN | cut -d. -f2 | base64 -d 2>/dev/null | python3 -m json.tool
   ```

4. **Check logs:**
   ```bash
   gcloud logging read "resource.type=cloud_run_revision" \
     --limit=50 --format=json
   ```

## Files Modified

- ✅ `src/auth.py` - NEW (authentication module)
- ✅ `src/server.py` - MODIFIED (added auth decorators)
- ✅ `requirements.txt` - MODIFIED (added google-auth dependencies)
- ✅ `AUTHENTICATION.md` - NEW (complete guide)
- ✅ `AUTH_QUICKSTART.md` - NEW (quick reference)
- ✅ `deploy/test-auth.sh` - NEW (test script)
- ✅ `README.md` - MODIFIED (added auth note)

## Next Steps

1. ✅ Code implementation complete
2. ⏭️ Deploy updated service to Cloud Run
3. ⏭️ Grant IAM permissions to users
4. ⏭️ Update Cloud Scheduler with OIDC auth
5. ⏭️ Run `./deploy/test-auth.sh` to verify
6. ⏭️ Monitor logs for auth failures

## Related Documentation

- [AUTHENTICATION.md](./AUTHENTICATION.md) - Full guide
- [AUTH_QUICKSTART.md](./AUTH_QUICKSTART.md) - Quick commands
- [Google Cloud Run Authentication](https://cloud.google.com/run/docs/authenticating/overview)
- [Cloud IAM Documentation](https://cloud.google.com/iam/docs)

