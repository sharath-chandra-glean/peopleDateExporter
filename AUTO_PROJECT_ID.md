# Automatic Project ID Detection - Update Summary

## Change Overview

Updated the authentication system to **automatically detect the GCP project ID** from the Cloud Run environment instead of requiring manual environment variable configuration.

## What Changed

### Before (Manual Configuration)
```python
# Required manual environment variable
project_id = os.environ.get('GCP_PROJECT_ID') or os.environ.get('GOOGLE_CLOUD_PROJECT')
if not project_id:
    raise error
```

**Issues:**
- ❌ Required manual setup
- ❌ Could be misconfigured
- ❌ Extra deployment step

### After (Automatic Detection)
```python
def get_project_id() -> str:
    """Get project ID from Cloud Run environment automatically."""
    # Try Application Default Credentials (automatic in Cloud Run)
    _, project_id = google.auth.default()
    if project_id:
        return project_id
    
    # Fallback to environment variables
    project_id = os.environ.get('GOOGLE_CLOUD_PROJECT') or \
                 os.environ.get('GCP_PROJECT') or \
                 os.environ.get('GCLOUD_PROJECT')
    if project_id:
        return project_id
    
    raise RuntimeError("Unable to determine GCP project ID")
```

**Benefits:**
- ✅ Works automatically in Cloud Run
- ✅ No manual configuration needed
- ✅ Uses Google's recommended approach
- ✅ Caches result for performance
- ✅ Falls back gracefully

## How It Works

### In Cloud Run (Production)
1. Cloud Run automatically sets up Application Default Credentials (ADC)
2. `google.auth.default()` returns the project ID from ADC
3. ✅ **Zero configuration required!**

### Local Development
1. Run `gcloud auth application-default login`
2. ADC is set up locally with your project
3. ✅ **Works the same as production!**

### Fallback (If Needed)
If ADC is not available, checks these environment variables:
- `GOOGLE_CLOUD_PROJECT` (Cloud Run sets this)
- `GCP_PROJECT` (custom)
- `GCLOUD_PROJECT` (legacy)

## Code Changes

### `src/auth.py`

**Added:**
```python
import google.auth

# Cache for performance
_cached_project_id: Optional[str] = None

def get_project_id() -> str:
    """Automatically detect GCP project ID from Cloud Run environment."""
    global _cached_project_id
    
    if _cached_project_id:
        return _cached_project_id
    
    # Try Application Default Credentials
    try:
        _, project_id = google.auth.default()
        if project_id:
            _cached_project_id = project_id
            logger.info(f"Detected GCP project ID: {project_id}")
            return project_id
    except Exception as e:
        logger.warning(f"Could not detect project from default credentials: {e}")
    
    # Fallback to environment variables
    project_id = os.environ.get('GOOGLE_CLOUD_PROJECT') or \
                 os.environ.get('GCP_PROJECT') or \
                 os.environ.get('GCLOUD_PROJECT')
    if project_id:
        _cached_project_id = project_id
        logger.info(f"Using project ID from environment: {project_id}")
        return project_id
    
    raise RuntimeError(
        "Unable to determine GCP project ID. This service must run in a GCP environment"
    )
```

**Updated:**
```python
# In require_auth decorator
try:
    project_id = get_project_id()  # Automatic detection
except RuntimeError as e:
    logger.error(f"Failed to get project ID: {e}")
    return jsonify({'error': 'configuration_error'}), 500
```

## Benefits

### 1. **Zero Configuration**
No need to set environment variables in Cloud Run:
```bash
# Before: Required this
gcloud run services update people-data-exporter \
  --set-env-vars=GCP_PROJECT_ID=my-project

# After: Not needed! Works automatically
```

### 2. **Best Practice**
Uses Google's recommended approach via Application Default Credentials.

### 3. **Secure**
Project ID comes from Google's infrastructure, not user input.

### 4. **Performance**
Caches the project ID after first retrieval (no repeated lookups).

### 5. **Local Development**
Works seamlessly with `gcloud auth application-default login`.

## Testing

### In Cloud Run
```bash
# Deploy and test - works automatically
gcloud run deploy people-data-exporter --source .

# Get token and test
TOKEN=$(gcloud auth print-identity-token)
curl -X POST -H "Authorization: Bearer $TOKEN" \
  https://your-service-url/sync
```

### Local Development
```bash
# Setup ADC locally
gcloud auth application-default login
gcloud config set project your-project-id

# Run locally
python -m src.server

# Test
TOKEN=$(gcloud auth print-identity-token)
curl -X POST -H "Authorization: Bearer $TOKEN" \
  http://localhost:8080/sync
```

## Migration Guide

### Existing Deployments

**Good news: No action required!**

If you previously set `GCP_PROJECT_ID` or `GOOGLE_CLOUD_PROJECT`:
- ✅ Still works (fallback mechanism)
- ✅ No breaking changes
- ℹ️ Can remove the env var if you want (not necessary)

### New Deployments

Just deploy - no project ID configuration needed:
```bash
gcloud run deploy people-data-exporter \
  --source . \
  --region us-central1 \
  --allow-unauthenticated
```

## Troubleshooting

### "Unable to determine GCP project ID"

**Cause:** Running outside of GCP without proper setup

**Solutions:**

1. **For Cloud Run:** Should never happen (ADC is automatic)

2. **For local development:**
   ```bash
   # Setup ADC
   gcloud auth application-default login
   
   # Or set environment variable
   export GOOGLE_CLOUD_PROJECT=your-project-id
   ```

3. **For other environments:**
   ```bash
   # Set any of these
   export GOOGLE_CLOUD_PROJECT=your-project-id
   export GCP_PROJECT=your-project-id
   export GCLOUD_PROJECT=your-project-id
   ```

### Verify Detection

Check logs to see how project ID was detected:
```bash
gcloud logging read "resource.type=cloud_run_revision" \
  --format="value(textPayload)" \
  | grep "project ID"
```

Expected output:
```
INFO - Detected GCP project ID: your-project-id
```

## Documentation Updates

Updated all documentation to reflect automatic detection:

- ✅ `AUTHENTICATION.md` - Updated environment variables section
- ✅ `AUTH_IMPLEMENTATION.md` - Updated configuration details
- ✅ `README.md` - Added note about automatic detection
- ✅ Created this summary document

## Key Takeaway

**No configuration needed!** The system now automatically detects the project ID from Cloud Run's environment. This follows Google Cloud best practices and eliminates a common configuration error.

## Related Links

- [Google Cloud Application Default Credentials](https://cloud.google.com/docs/authentication/application-default-credentials)
- [Cloud Run Environment Variables](https://cloud.google.com/run/docs/configuring/environment-variables)
- [google.auth Python Library](https://google-auth.readthedocs.io/)

