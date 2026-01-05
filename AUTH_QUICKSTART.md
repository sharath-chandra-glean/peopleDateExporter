# Quick Authentication Setup Guide

This guide provides quick commands to set up authentication for your Cloud Run deployment.

## Prerequisites

- Cloud Run service deployed
- `gcloud` CLI installed and authenticated
- Project ID set

## 1. Grant Yourself Access

```bash
# Get your email
YOUR_EMAIL=$(gcloud config get-value account)

# Grant Cloud Run Invoker permission
gcloud run services add-iam-policy-binding people-data-exporter \
  --region=us-central1 \
  --member="user:${YOUR_EMAIL}" \
  --role="roles/run.invoker"
```

## 2. Test Your Access

```bash
# Get service URL
SERVICE_URL=$(gcloud run services describe people-data-exporter \
  --region=us-central1 \
  --format="value(status.url)")

# Get your identity token
TOKEN=$(gcloud auth print-identity-token)

# Test sync endpoint
curl -X POST \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  ${SERVICE_URL}/sync
```

## 3. Grant Access to Others

### For Individual Users

```bash
gcloud run services add-iam-policy-binding people-data-exporter \
  --region=us-central1 \
  --member="user:alice@example.com" \
  --role="roles/run.invoker"
```

### For a Google Group

```bash
gcloud run services add-iam-policy-binding people-data-exporter \
  --region=us-central1 \
  --member="group:admins@example.com" \
  --role="roles/run.invoker"
```

### For a Service Account

```bash
gcloud run services add-iam-policy-binding people-data-exporter \
  --region=us-central1 \
  --member="serviceAccount:my-sa@project-id.iam.gserviceaccount.com" \
  --role="roles/run.invoker"
```

## 4. Setup Cloud Scheduler with Auth

```bash
# Create service account for scheduler
gcloud iam service-accounts create sync-scheduler \
  --display-name="Cloud Scheduler for People Sync"

# Grant Cloud Run Invoker permission to service account
gcloud run services add-iam-policy-binding people-data-exporter \
  --region=us-central1 \
  --member="serviceAccount:sync-scheduler@${GCP_PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/run.invoker"

# Create Cloud Scheduler job with OIDC authentication
gcloud scheduler jobs create http daily-people-sync \
  --schedule="0 2 * * *" \
  --uri="${SERVICE_URL}/sync" \
  --http-method=POST \
  --location=us-central1 \
  --oidc-service-account-email="sync-scheduler@${GCP_PROJECT_ID}.iam.gserviceaccount.com" \
  --oidc-token-audience="${SERVICE_URL}"
```

## 5. Verify Permissions

### List who has access
```bash
gcloud run services get-iam-policy people-data-exporter \
  --region=us-central1 \
  --format=json
```

### Test from command line
```bash
# Using test script
./deploy/test-auth.sh ${SERVICE_URL}
```

## 6. Revoke Access

### Remove user access
```bash
gcloud run services remove-iam-policy-binding people-data-exporter \
  --region=us-central1 \
  --member="user:alice@example.com" \
  --role="roles/run.invoker"
```

### Remove service account access
```bash
gcloud run services remove-iam-policy-binding people-data-exporter \
  --region=us-central1 \
  --member="serviceAccount:my-sa@project-id.iam.gserviceaccount.com" \
  --role="roles/run.invoker"
```

## Common Scenarios

### Allow All Project Members
```bash
gcloud run services add-iam-policy-binding people-data-exporter \
  --region=us-central1 \
  --member="domain:example.com" \
  --role="roles/run.invoker"
```

### Allow Only From Specific VPC
Use VPC Service Controls (advanced - see GCP documentation)

### Allow Anonymous Access (NOT RECOMMENDED)
```bash
# Warning: This allows anyone on the internet to trigger syncs!
gcloud run services add-iam-policy-binding people-data-exporter \
  --region=us-central1 \
  --member="allUsers" \
  --role="roles/run.invoker"
```

## Troubleshooting

### "Permission denied" error
```bash
# Check if you have permission
gcloud run services get-iam-policy people-data-exporter \
  --region=us-central1 \
  | grep $(gcloud config get-value account)

# If not listed, add yourself:
gcloud run services add-iam-policy-binding people-data-exporter \
  --region=us-central1 \
  --member="user:$(gcloud config get-value account)" \
  --role="roles/run.invoker"
```

### Token expired
```bash
# Get fresh token
TOKEN=$(gcloud auth print-identity-token)
```

### Can't get identity token
```bash
# Re-authenticate
gcloud auth login
gcloud auth application-default login

# Try again
TOKEN=$(gcloud auth print-identity-token)
```

## Security Tips

1. **Never share tokens** - They're like passwords
2. **Use service accounts** for automation, not personal accounts
3. **Grant minimal permissions** - Only `run.invoker`, not broader roles
4. **Audit regularly** - Check who has access monthly
5. **Use groups** - Easier to manage than individual users
6. **Enable Cloud Audit Logs** - Track who's calling your service

## Next Steps

- Read full guide: [AUTHENTICATION.md](./AUTHENTICATION.md)
- Setup monitoring: Track failed auth attempts
- Configure alerts: Get notified of unauthorized access
- Review logs regularly: `gcloud logging read`

