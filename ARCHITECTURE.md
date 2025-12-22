# GCP Architecture Diagram

## Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Google Cloud Platform                        │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    Cloud Scheduler                           │   │
│  │                                                              │   │
│  │  Job: people-data-exporter-daily                            │   │
│  │  Schedule: 0 2 * * * (Daily at 2 AM)                        │   │
│  │  Target: POST /sync                                          │   │
│  │  Auth: OIDC Token                                            │   │
│  └────────────────────┬────────────────────────────────────────┘   │
│                       │                                              │
│                       │ 1. Triggers daily at 2 AM                   │
│                       │    with OIDC authentication                  │
│                       │                                              │
│                       ▼                                              │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                     Cloud Run Service                        │   │
│  │              people-data-exporter                            │   │
│  │                                                              │   │
│  │  ┌────────────────────────────────────────────────────┐    │   │
│  │  │         Flask HTTP Server (Port 8080)              │    │   │
│  │  │                                                     │    │   │
│  │  │  GET  /          → Service Info                    │    │   │
│  │  │  GET  /health    → Health Check (200 OK)           │    │   │
│  │  │  POST /sync      → Trigger Data Sync               │    │   │
│  │  │                                                     │    │   │
│  │  └────────────────┬────────────────────────────────┬──┘    │   │
│  │                   │                                 │       │   │
│  │                   │ 2. Executes sync                │       │   │
│  │                   ▼                                 │       │   │
│  │  ┌────────────────────────────────────────────┐    │       │   │
│  │  │     PeopleDataExporter Class               │    │       │   │
│  │  │                                            │    │       │   │
│  │  │  • KeycloakClient                          │    │       │   │
│  │  │  • GleanClient                             │    │       │   │
│  │  │  • sync_users()                            │    │       │   │
│  │  │  • sync_groups()                           │    │       │   │
│  │  └────────┬──────────────────────┬────────────┘    │       │   │
│  │           │                      │                  │       │   │
│  │           │ 3. Fetch users       │ 4. Push users    │       │   │
│  │           │    & groups          │    & teams       │       │   │
│  │           │                      │                  │       │   │
│  │  Resources:                      │                  │       │   │
│  │  • CPU: 1 vCPU                   │                  │       │   │
│  │  • Memory: 512 Mi                │                  │       │   │
│  │  • Timeout: 3600s (60 min)       │                  │       │   │
│  │  • Min Instances: 0 (scales to 0)│                  │       │   │
│  │  • Max Instances: 1              │                  │       │   │
│  │  • Concurrency: 1                │                  │       │   │
│  └────────────┬──────────────────────┬──────────────────┘       │   │
│               │                      │                          │   │
│               │                      │ 5. Returns                │   │
│               │                      │    success/failure        │   │
│               │                      ▼                          │   │
│  ┌────────────┴─────────────────────────────────────────────┐  │   │
│  │                  Secret Manager                           │  │   │
│  │                                                            │  │   │
│  │  • KEYCLOAK_BASE_URL                                      │  │   │
│  │  • KEYCLOAK_REALM                                         │  │   │
│  │  • KEYCLOAK_CLIENT_ID                                     │  │   │
│  │  • KEYCLOAK_CLIENT_SECRET                                 │  │   │
│  │  • GLEAN_API_URL                                          │  │   │
│  │  • GLEAN_API_TOKEN                                        │  │   │
│  │  • GLEAN_DATASOURCE                                       │  │   │
│  └────────────────────────────────────────────────────────────┘  │   │
│                                                                   │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │              Artifact Registry                              │  │
│  │                                                             │  │
│  │  Repository: people-exporter                                │  │
│  │  Image: people-data-exporter:latest                         │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                   │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │                 Cloud Logging                               │  │
│  │                                                             │  │
│  │  • Cloud Run logs                                           │  │
│  │  • Cloud Scheduler logs                                     │  │
│  │  • Application logs (INFO/ERROR/DEBUG)                      │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                   │
└───────────────────────────────────────────────────────────────────┘
         │                                    │
         │ 3. Fetch users/groups              │ 4. Push formatted data
         │                                    │
         ▼                                    ▼
┌──────────────────────┐           ┌──────────────────────┐
│   Keycloak Server    │           │    Glean API         │
│                      │           │                      │
│  Admin API:          │           │  People API:         │
│  • Get Users         │           │  • Bulk Index        │
│  • Get Groups        │           │    Employees         │
│  • Get Members       │           │  • Index Teams       │
│                      │           │                      │
│  Auth: OAuth2        │           │  Auth: Bearer Token  │
│  Client Credentials  │           │                      │
└──────────────────────┘           └──────────────────────┘
```

## Data Flow

### 1. Scheduled Trigger
- Cloud Scheduler wakes up at configured time (default: 2 AM)
- Sends POST request to `/sync` endpoint with OIDC token
- Cloud Run service authenticates the request

### 2. Service Activation
- Cloud Run scales from 0 to 1 instance (if idle)
- Flask server receives the POST request
- Creates `PeopleDataExporter` instance

### 3. Data Fetching (Keycloak)
- Authenticates with Keycloak using client credentials
- Fetches all users (or limited by MAX_USERS)
- Fetches all groups and their members
- Transforms data according to field mapping

### 4. Data Pushing (Glean)
- Formats users as Glean employees
- Formats groups as Glean teams
- Pushes data using bulk or individual indexing
- Handles retries and errors

### 5. Response & Cleanup
- Returns HTTP 200 with success details or HTTP 500 on failure
- Logs execution time and statistics
- Cloud Run scales back to 0 after completion

## Component Details

### Cloud Run Configuration

| Setting | Value | Purpose |
|---------|-------|---------|
| Min Instances | 0 | Scale to zero for cost savings |
| Max Instances | 1 | Only one sync at a time |
| CPU | 1 vCPU | Sufficient for API calls |
| Memory | 512 Mi | Handles typical user loads |
| Timeout | 3600s | Up to 60 minutes for large datasets |
| Concurrency | 1 | Process one sync at a time |
| Port | 8080 | Standard HTTP port |

### Security Model

```
┌─────────────────────────────────────────────────────────┐
│                  Authentication Flow                     │
│                                                          │
│  Cloud Scheduler                                         │
│         │                                                │
│         │ 1. Request identity token                      │
│         ▼                                                │
│  Google IAM                                              │
│         │                                                │
│         │ 2. Issue OIDC token                            │
│         ▼                                                │
│  Cloud Run Service                                       │
│         │                                                │
│         │ 3. Validate token                              │
│         ▼                                                │
│  Service Account: cloud-scheduler-invoker                │
│  Role: roles/run.invoker                                 │
│         │                                                │
│         │ 4. Grant access to secrets                     │
│         ▼                                                │
│  Secret Manager                                          │
│  Role: roles/secretmanager.secretAccessor                │
│         │                                                │
│         │ 5. Retrieve secrets                            │
│         ▼                                                │
│  Environment Variables (injected at runtime)             │
└─────────────────────────────────────────────────────────┘
```

### Cost Breakdown

| Component | Monthly Cost | Notes |
|-----------|-------------|-------|
| Cloud Run | $0.50-$5.00 | Pay per use, mostly free tier |
| Secret Manager | $0.42 | $0.06 × 7 secrets |
| Cloud Scheduler | $0.10 | $0.10 per job |
| Artifact Registry | $0.10 | Storage for Docker image |
| Cloud Logging | Free | First 50 GB/month free |
| **Total** | **~$1-6/month** | Very cost-effective |

### Monitoring

- **Cloud Run Metrics**: Request count, latency, error rate
- **Cloud Scheduler**: Job execution history, success/failure
- **Application Logs**: Structured logs in Cloud Logging
- **Health Checks**: `/health` endpoint returns service status
- **Alerts**: Can be configured for failures or high error rates

## Deployment Process

```
┌─────────────────────────┐
│  1. setup-secrets.sh    │  Store credentials in Secret Manager
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│  2. build-and-push.sh   │  Build Docker image → Artifact Registry
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│  3. deploy-cloud-run.sh │  Deploy service with secrets
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│  4. setup-scheduler.sh  │  Create cron job with auth
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│  5. test-endpoints.sh   │  Verify all endpoints work
└─────────────────────────┘
```

## Advantages of This Architecture

### ✅ Cost-Effective
- Scales to zero when idle
- Pay only for actual execution time
- Free tier covers most usage

### ✅ Reliable
- Managed services (no infrastructure to maintain)
- Automatic retries on Cloud Scheduler
- Built-in health checks and monitoring

### ✅ Secure
- Secrets stored in Secret Manager (encrypted)
- No public access (authentication required)
- Service accounts with minimal permissions
- OIDC token-based authentication

### ✅ Scalable
- Can handle growing user datasets
- Adjustable timeout (up to 60 minutes)
- Can increase memory/CPU if needed

### ✅ Maintainable
- Simple deployment scripts
- Easy to update (rebuild and redeploy)
- Comprehensive logging
- Clear separation of concerns

## Comparison with Alternatives

| Solution | Cost | Complexity | Max Runtime | Scale to Zero |
|----------|------|------------|-------------|---------------|
| **Cloud Run** ⭐ | $ | Low | 60 min | Yes |
| Cloud Functions | $$ | Low | 9-60 min | Yes |
| Cloud Run Jobs | $ | Medium | 24 hours | Yes |
| GKE CronJob | $$$ | High | Unlimited | No |
| Compute Engine | $$$$ | High | Unlimited | No |

## Future Enhancements

Possible improvements to this architecture:

1. **Cloud Run Jobs**: For syncs > 60 minutes
2. **Pub/Sub**: For event-driven syncs (not just cron)
3. **Cloud Monitoring Dashboards**: Custom dashboards
4. **Cloud Alerting**: Email/SMS on failures
5. **Multi-region**: Deploy to multiple regions for redundancy
6. **CI/CD**: Cloud Build for automated deployments
7. **Terraform**: Infrastructure as Code for reproducible deployments

