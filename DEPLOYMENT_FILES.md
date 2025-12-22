# GCP Deployment - Files Summary

This document lists all files created for GCP deployment.

## 📁 Project Structure

```
peopleDataExporter/
├── src/
│   ├── server.py                    # ✨ NEW: Flask HTTP server for Cloud Run
│   ├── main.py                      # Existing: Batch mode sync logic
│   └── ...
│
├── deploy/                           # ✨ NEW: Deployment scripts
│   ├── setup-secrets.sh             # Store secrets in Secret Manager
│   ├── build-and-push.sh            # Build & push Docker image
│   ├── deploy-cloud-run.sh          # Deploy service to Cloud Run
│   ├── setup-scheduler.sh           # Configure Cloud Scheduler cron
│   ├── test-endpoints.sh            # Test HTTP endpoints
│   └── cloud-run-service.yaml       # Cloud Run service definition
│
├── Dockerfile                        # ✨ UPDATED: Multi-mode support
├── docker-compose.yml                # ✨ UPDATED: Added server mode
├── requirements.txt                  # ✨ UPDATED: Added Flask
├── run-server-local.sh               # ✨ NEW: Local HTTP server testing
│
├── GCP_DEPLOYMENT.md                 # ✨ NEW: Comprehensive deployment guide
├── QUICKSTART_GCP.md                 # ✨ NEW: Quick start guide
├── ARCHITECTURE.md                   # ✨ NEW: Architecture diagrams
├── GCP_OPTIONS_COMPARISON.md         # ✨ NEW: Comparison of GCP options
├── README.md                         # ✨ UPDATED: Added GCP deployment section
└── ...
```

---

## 📄 New Files Created

### 1. Application Code

#### `src/server.py`
**Purpose:** Flask HTTP server for Cloud Run deployment

**Endpoints:**
- `GET /` - Service information
- `GET /health` - Health check (returns 200 if healthy)
- `POST /sync` - Trigger data sync

**Features:**
- Error handling
- JSON responses
- Execution time tracking
- Proper HTTP status codes

---

### 2. Deployment Scripts (`deploy/`)

All scripts are executable and include colored output and error handling.

#### `deploy/setup-secrets.sh`
**Purpose:** Store credentials in Google Cloud Secret Manager

**What it does:**
1. Reads from your `.env` file
2. Creates secrets in Secret Manager
3. Enables Secret Manager API
4. Supports updates to existing secrets

**Usage:**
```bash
./deploy/setup-secrets.sh
```

#### `deploy/build-and-push.sh`
**Purpose:** Build Docker image and push to Artifact Registry

**What it does:**
1. Configures Docker authentication
2. Builds the Docker image
3. Tags with project/region/repo
4. Pushes to Artifact Registry

**Usage:**
```bash
./deploy/build-and-push.sh
```

**Environment variables:**
- `GCP_PROJECT_ID` (required)
- `GCP_REGION` (default: us-central1)
- `ARTIFACT_REGISTRY_REPO` (default: people-exporter)
- `IMAGE_TAG` (default: latest)

#### `deploy/deploy-cloud-run.sh`
**Purpose:** Deploy service to Cloud Run

**What it does:**
1. Deploys container to Cloud Run
2. Configures resource limits (CPU, memory, timeout)
3. Mounts secrets as environment variables
4. Disables public access (auth required)
5. Configures scaling (min/max instances)

**Usage:**
```bash
./deploy/deploy-cloud-run.sh
```

**Configuration:**
- CPU: 1 vCPU
- Memory: 512Mi
- Timeout: 3600s (60 minutes)
- Min Instances: 0 (scales to zero)
- Max Instances: 1
- Concurrency: 1

#### `deploy/setup-scheduler.sh`
**Purpose:** Create Cloud Scheduler cron job

**What it does:**
1. Creates service account for Cloud Scheduler
2. Grants Cloud Run invoker permissions
3. Creates scheduled job with OIDC auth
4. Configures retry policy

**Usage:**
```bash
./deploy/setup-scheduler.sh
```

**Configuration:**
- Schedule: `0 2 * * *` (2 AM daily)
- Time Zone: America/Los_Angeles
- Max Retries: 2
- Backoff: 30s to 300s

#### `deploy/test-endpoints.sh`
**Purpose:** Test all Cloud Run endpoints

**What it does:**
1. Gets service URL from Cloud Run
2. Obtains authentication token
3. Tests `/`, `/health`, `/sync` endpoints
4. Displays formatted JSON responses

**Usage:**
```bash
./deploy/test-endpoints.sh
```

#### `deploy/cloud-run-service.yaml`
**Purpose:** Cloud Run service definition (YAML format)

**Use case:** Alternative deployment method using `gcloud run services replace`

---

### 3. Documentation

#### `GCP_DEPLOYMENT.md` (Comprehensive Guide)
**Sections:**
- Architecture overview with diagrams
- Prerequisites and setup
- Step-by-step deployment
- Testing procedures
- Monitoring and troubleshooting
- Cost management
- Security best practices
- FAQ

**Target audience:** First-time deployers, operations teams

#### `QUICKSTART_GCP.md` (Quick Reference)
**Content:**
- Minimal steps to deploy
- Essential commands
- Quick troubleshooting
- Next steps

**Target audience:** Experienced users, quick reference

#### `ARCHITECTURE.md` (Technical Deep-Dive)
**Content:**
- Detailed architecture diagrams
- Data flow explanations
- Component specifications
- Security model
- Cost breakdown
- Comparison with alternatives
- Future enhancements

**Target audience:** Architects, technical decision-makers

#### `GCP_OPTIONS_COMPARISON.md` (Decision Guide)
**Content:**
- Comparison of all GCP deployment options
- Decision matrix
- Pros/cons of each option
- Why Cloud Run Service was chosen
- Alternative scenarios

**Target audience:** Technical leads, decision-makers

---

### 4. Updated Files

#### `src/server.py` ✨ NEW
- Flask HTTP server implementation
- Health check endpoint
- Sync trigger endpoint

#### `Dockerfile` ✨ UPDATED
**Changes:**
- Added `PORT` environment variable
- Added `EXPOSE 8080`
- Changed CMD to `python -m src.server`
- Comments explain batch vs. HTTP mode

#### `requirements.txt` ✨ UPDATED
**Added:**
```
flask==3.0.0
```

#### `docker-compose.yml` ✨ UPDATED
**Changes:**
- Split into two services:
  - `people-exporter` - Batch mode (run once)
  - `people-exporter-server` - HTTP server mode
- Added health check for server mode
- Added port mapping for local testing

#### `README.md` ✨ UPDATED
**Added:**
- GCP deployment section (prominent)
- Quick start commands
- Links to detailed guides
- Endpoint documentation

#### `run-server-local.sh` ✨ NEW
**Purpose:** Run HTTP server locally for testing

**Usage:**
```bash
./run-server-local.sh
```

Then visit:
- http://localhost:8080/ - Service info
- http://localhost:8080/health - Health check
- http://localhost:8080/sync - Trigger sync (POST)

---

## 🚀 Deployment Workflow

### One-Time Setup (5 minutes)

```bash
# 1. Set environment variables
export GCP_PROJECT_ID="your-project-id"
export GCP_REGION="us-central1"

# 2. Create Artifact Registry repository
gcloud artifacts repositories create people-exporter \
    --repository-format=docker \
    --location=$GCP_REGION
```

### Deploy (10 minutes)

```bash
# 3. Store secrets
./deploy/setup-secrets.sh

# 4. Build and push image
./deploy/build-and-push.sh

# 5. Deploy to Cloud Run
./deploy/deploy-cloud-run.sh

# 6. Setup cron job
./deploy/setup-scheduler.sh

# 7. Test
./deploy/test-endpoints.sh
```

### Updates (2 minutes)

```bash
# Rebuild and redeploy
./deploy/build-and-push.sh
./deploy/deploy-cloud-run.sh
```

---

## 🧪 Testing

### Local Testing

```bash
# Start HTTP server locally
./run-server-local.sh

# In another terminal
curl http://localhost:8080/health
curl -X POST http://localhost:8080/sync
```

### Cloud Testing

```bash
# Test all endpoints
./deploy/test-endpoints.sh

# Or manually
SERVICE_URL=$(gcloud run services describe people-data-exporter \
    --region=$GCP_REGION --format='value(status.url)')

curl -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
    $SERVICE_URL/health
```

---

## 📊 What Gets Deployed

### GCP Resources Created

1. **Cloud Run Service**: `people-data-exporter`
   - Region: us-central1 (or specified)
   - No public access (auth required)
   - Auto-scaling (0-1 instances)

2. **Cloud Scheduler Job**: `people-data-exporter-daily`
   - Schedule: Daily at 2 AM
   - Target: POST /sync endpoint
   - Auth: OIDC token

3. **Service Account**: `cloud-scheduler-invoker@[project].iam.gserviceaccount.com`
   - Role: `roles/run.invoker`

4. **Secrets in Secret Manager**:
   - `KEYCLOAK_BASE_URL`
   - `KEYCLOAK_REALM`
   - `KEYCLOAK_CLIENT_ID`
   - `KEYCLOAK_CLIENT_SECRET`
   - `GLEAN_API_URL`
   - `GLEAN_API_TOKEN`
   - `GLEAN_DATASOURCE`

5. **Docker Image**: `[region]-docker.pkg.dev/[project]/people-exporter/people-data-exporter:latest`

---

## 💰 Cost Estimate

| Resource | Monthly Cost |
|----------|-------------|
| Cloud Run | $0.50 - $5.00 |
| Secret Manager | $0.42 |
| Cloud Scheduler | $0.10 |
| Artifact Registry | $0.10 |
| Cloud Logging | Free (50GB free tier) |
| **Total** | **~$1-6/month** |

---

## 🔒 Security Features

- ✅ Secrets encrypted in Secret Manager
- ✅ No public access (OIDC authentication)
- ✅ Service accounts with minimal permissions
- ✅ Automatic credential rotation support
- ✅ Audit logging via Cloud Logging
- ✅ HTTPS only

---

## 📞 Support & Documentation

| Document | Purpose | Audience |
|----------|---------|----------|
| `QUICKSTART_GCP.md` | Get started fast | Developers |
| `GCP_DEPLOYMENT.md` | Complete guide | Ops teams |
| `ARCHITECTURE.md` | Technical details | Architects |
| `GCP_OPTIONS_COMPARISON.md` | Decision guide | Tech leads |
| This file | File inventory | Everyone |

---

## ✅ Checklist

Before deployment:
- [ ] GCP project created
- [ ] Billing enabled
- [ ] `gcloud` CLI installed
- [ ] Docker installed
- [ ] `.env` file configured
- [ ] Environment variables exported

After deployment:
- [ ] All scripts executed successfully
- [ ] Health check returns 200
- [ ] Manual sync test passes
- [ ] Scheduler job created
- [ ] Logs accessible
- [ ] Documentation reviewed

---

## 🎯 Next Steps

1. **Deploy to production**
   - Follow `QUICKSTART_GCP.md`
   - Run all deployment scripts
   - Test thoroughly

2. **Set up monitoring**
   - Configure Cloud Monitoring alerts
   - Set up budget alerts
   - Review logs regularly

3. **Customize**
   - Adjust cron schedule if needed
   - Tune resource limits
   - Configure additional environment variables

4. **Maintain**
   - Update secrets regularly
   - Monitor costs
   - Review logs for errors
   - Keep Docker image updated

---

## 🎉 Summary

You now have a **production-ready, cloud-native deployment** for the People Data Exporter!

**Key Features:**
- ✅ Fully automated deployment
- ✅ Health check endpoint for monitoring
- ✅ Daily cron job with automatic retries
- ✅ Secure secret management
- ✅ Scales to zero (cost-effective)
- ✅ Comprehensive documentation
- ✅ Easy to test and debug

**Total deployment time:** ~15 minutes  
**Monthly cost:** ~$1-6  
**Maintenance:** Minimal (managed services)

Ready to deploy? Start with `QUICKSTART_GCP.md`! 🚀

