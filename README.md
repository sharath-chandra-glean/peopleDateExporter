# People Data Exporter

A Python-based application that synchronizes user and group data from Keycloak to Glean's People API. This tool is designed to run in Docker for easy deployment on any cloud platform.

## Features

- 🔐 Fetches users and groups from Keycloak Admin API
- 📤 Pushes formatted data to Glean People API
- 🗺️ Intelligent field mapping from Keycloak to Glean
- 🐳 Fully Dockerized for cloud deployment
- ⚙️ Environment-based configuration
- 📊 Comprehensive logging
- 🔄 Automatic retry logic for API calls
- 🧪 Dry-run mode for testing
- 🔀 Support for both bulk and individual indexing

## Project Structure

```
peopleDataExporter/
├── src/
│   ├── __init__.py
│   ├── main.py                    # Main orchestration script
│   ├── clients/
│   │   ├── __init__.py
│   │   ├── keycloak_client.py     # Keycloak API client
│   │   └── glean_client.py        # Glean API client
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py            # Configuration management
│   └── utils/
│       ├── __init__.py
│       └── logger.py              # Logging setup
├── Dockerfile                      # Docker container definition
├── docker-compose.yml             # Docker Compose configuration
├── requirements.txt               # Python dependencies
├── env.template                   # Environment variables template
└── README.md                      # This file
```

## Prerequisites

- Docker and Docker Compose (for containerized deployment)
- OR Python 3.11+ (for local development)
- Keycloak instance with admin API access
- Glean API access with appropriate permissions

## Configuration

### Environment Variables

Copy `env.template` to `.env` and configure the following variables:

#### Keycloak Configuration
- `KEYCLOAK_BASE_URL`: Keycloak server URL (e.g., `https://keycloak.example.com`)
- `KEYCLOAK_REALM`: Keycloak realm name
- `KEYCLOAK_CLIENT_ID`: Client ID for authentication
- `KEYCLOAK_CLIENT_SECRET`: Client secret for authentication
- `KEYCLOAK_TIMEOUT`: Request timeout in seconds (default: 30)

#### Glean Configuration
- `GLEAN_API_URL`: Glean API base URL (e.g., `https://api.glean.com`)
- `GLEAN_API_TOKEN`: API token for authentication
- `GLEAN_DATASOURCE`: Datasource identifier for Glean
- `GLEAN_TIMEOUT`: Request timeout in seconds (default: 30)
- `GLEAN_USE_BULK_INDEX`: Use bulk indexing API (`true`) or individual indexing API (`false`) (default: true)
- `GLEAN_DISABLE_STALE_DATA_DELETION`: Prevent Glean from automatically deleting employees not in the upload (`true`/`false`, default: false)

#### Application Configuration
- `LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `DRY_RUN`: Enable dry-run mode without pushing to Glean (true/false)
- `MAX_USERS`: Optional limit on number of users to sync (useful for testing)

### Keycloak Setup

1. Create a client in Keycloak with `Service Account Roles` enabled
2. Assign the following roles to the service account:
   - `view-users`
   - `view-realm`
   - `query-groups`
   - `query-users`

### Glean Setup

1. Obtain an API token from Glean with people indexing permissions
2. Create a datasource identifier for your Keycloak integration

## Field Mapping

The application automatically maps Keycloak user fields to Glean employee fields:

### Core Fields

| Keycloak Field | Glean Employee Field | Notes |
|----------------|---------------------|-------|
| `email` | `email` | Required |
| `firstName` | `firstName` | |
| `lastName` | `lastName` | |
| `id` | `id` | Keycloak user ID |
| `enabled` | `status` | `true` → `CURRENT`, `false` → `FORMER` |
| `createdTimestamp` | `startDate` | Converted from Unix timestamp to YYYY-MM-DD |

### Attributes Mapping

Keycloak custom attributes are extracted and mapped to Glean fields:

| Keycloak Attribute | Glean Employee Field | Type |
|-------------------|---------------------|------|
| `attributes.department` | `department` | String or first item of array |
| `attributes.title` | `title` | String or first item of array |
| `attributes.businessUnit` | `businessUnit` | String or first item of array |
| `attributes.phoneNumber` | `phoneNumber` | String or first item of array |
| `attributes.managerEmail` | `managerEmail` | String or first item of array |
| `attributes.bio` | `bio` | String or first item of array |
| `attributes.photoUrl` | `photoUrl` | String or first item of array |

### Example Mapping

**Keycloak Input:**
```json
{
  "id": "5797cc81-da1c-442e-b010-b5a04149c314",
  "username": "awaneendra.tiwari@sasandbox.com",
  "firstName": "Awaneendra",
  "lastName": "Tiwari",
  "email": "awaneendra.tiwari@sasandbox.com",
  "emailVerified": true,
  "enabled": true,
  "createdTimestamp": 1753366940778,
  "attributes": {
    "department": ["Sales"],
    "title": ["Sales Manager"],
    "phoneNumber": ["+1-555-0123"]
  }
}
```

**Glean Output:**
```json
{
  "email": "awaneendra.tiwari@sasandbox.com",
  "firstName": "Awaneendra",
  "lastName": "Tiwari",
  "id": "5797cc81-da1c-442e-b010-b5a04149c314",
  "department": "Sales",
  "title": "Sales Manager",
  "phoneNumber": "+1-555-0123",
  "status": "CURRENT",
  "startDate": "2025-01-23"
}
```

### Handling Missing Data

- Fields not present in Keycloak are omitted from the Glean payload
- Empty or null values are not sent to Glean
- Array attributes extract the first element
- Unmapped Keycloak fields are ignored

## Usage

### Using Docker (Recommended)

1. **Configure environment**:
   ```bash
   cp env.template .env
   # Edit .env with your configuration
   ```

2. **Build the Docker image**:
   ```bash
   docker-compose build
   ```

3. **Run the sync**:
   ```bash
   docker-compose up
   ```

4. **One-time run** (container removes after execution):
   ```bash
   docker-compose run --rm people-exporter
   ```

### Using Docker without Compose

```bash
# Build
docker build -t people-data-exporter .

# Run with env file
docker run --env-file .env people-data-exporter

# Run with individual environment variables
docker run \
  -e KEYCLOAK_BASE_URL=https://keycloak.example.com \
  -e KEYCLOAK_REALM=master \
  -e KEYCLOAK_CLIENT_ID=people-exporter \
  -e KEYCLOAK_CLIENT_SECRET=your-secret \
  -e GLEAN_API_URL=https://api.glean.com \
  -e GLEAN_API_TOKEN=your-token \
  -e GLEAN_DATASOURCE=keycloak \
  people-data-exporter
```

### Local Development

1. **Create virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set environment variables**:
   ```bash
   export $(cat .env | xargs)  # On Unix
   # Or source .env manually on Windows
   ```

4. **Run the script**:
   ```bash
   python -m src.main
   ```

## Indexing Modes

### Bulk Indexing (Default)

Bulk indexing pushes all users in a single API call using the `/api/index/v1/bulkindexemployees` endpoint, which is faster and more efficient for large datasets:

```bash
GLEAN_USE_BULK_INDEX=true docker-compose up
```

**Features:**
- Single API call for all employees
- Pagination support for very large datasets
- Option to disable stale data deletion
- Automatic generation of upload session IDs (UUID v4)
- Automatic handling of upload sessions

**Stale Data Deletion:**
By default, Glean will remove employees from its system that are not included in your upload. To prevent this behavior (useful for incremental syncs):

```bash
GLEAN_DISABLE_STALE_DATA_DELETION=true docker-compose up
```

### Individual Indexing

Individual indexing pushes users one at a time using the individual employee index API (`/api/index/v1/indexemployee`). This is useful when:
- You need more granular control over each user
- You want to continue syncing even if some users fail
- You're dealing with API rate limits

```bash
GLEAN_USE_BULK_INDEX=false docker-compose up
```

When using individual indexing, the tool provides detailed progress reporting and continues even if some users fail to index.

## Dry Run Mode

Test the integration without pushing data to Glean:

```bash
# Using Docker Compose
DRY_RUN=true docker-compose up

# Using Docker
docker run --env-file .env -e DRY_RUN=true people-data-exporter

# Local
DRY_RUN=true python -m src.main
```

## Cloud Deployment

### Google Cloud Platform (Recommended) ⭐

**Complete GCP deployment with Cloud Run + Cloud Scheduler**

The easiest and most cost-effective way to deploy this project. Includes:
- ✅ HTTP endpoints for health checks and sync triggers
- ✅ Daily automated cron jobs
- ✅ Secure secret management
- ✅ Auto-scaling (scales to zero)
- ✅ ~$1-6/month cost

**Quick Start:**

```bash
# 1. Set your GCP project
export GCP_PROJECT_ID="your-project-id"

# 2. Run deployment scripts
./deploy/setup-secrets.sh        # Store credentials
./deploy/build-and-push.sh       # Build & push Docker image
./deploy/deploy-cloud-run.sh     # Deploy service
./deploy/setup-scheduler.sh      # Setup daily cron

# 3. Test
./deploy/test-endpoints.sh

# 4. Grant IAM permissions
gcloud run services add-iam-policy-binding people-data-exporter \
  --region=us-central1 \
  --member="user:your-email@example.com" \
  --role="roles/run.invoker"
```

📖 **Full Guide:** [GCP_DEPLOYMENT.md](./GCP_DEPLOYMENT.md)  
🚀 **Quick Start:** [QUICKSTART_GCP.md](./QUICKSTART_GCP.md)

**Endpoints:**
- `GET /health` - Health check for monitoring (optional auth)
- `POST /sync` - Trigger data sync manually or via cron (**requires auth** 🔒)
- `GET /` - Service information

**Authentication:**
All sync operations require:
- ✅ Valid Google Cloud identity token
- ✅ Cloud Run Invoker permission (`roles/run.invoker`)

📖 **Authentication Guide:** [AUTHENTICATION.md](./AUTHENTICATION.md)

---

### Other Cloud Platforms

<details>
<summary><b>Kubernetes</b></summary>

Example Kubernetes CronJob:

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: people-data-exporter
spec:
  schedule: "0 2 * * *"
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: exporter
            image: your-registry/people-data-exporter:latest
            envFrom:
            - secretRef:
                name: people-exporter-secrets
          restartPolicy: OnFailure
```
</details>

<details>
<summary><b>Azure Container Instances</b></summary>

```bash
az container create \
  --resource-group myResourceGroup \
  --name people-data-exporter \
  --image your-registry/people-data-exporter:latest \
  --environment-variables $(cat .env)
```
</details>

## Logging

The application provides detailed logging at multiple levels:

- **INFO**: General progress and statistics
- **DEBUG**: Detailed API calls and data samples
- **WARNING**: Non-critical issues
- **ERROR**: Failures and exceptions

Set `LOG_LEVEL` environment variable to control verbosity.

## Error Handling

- Automatic retry with exponential backoff for transient failures
- Graceful handling of partial data
- Detailed error logging with stack traces
- Non-zero exit codes on failure for CI/CD integration

## Security Best Practices

- Store sensitive credentials in secret management systems (AWS Secrets Manager, Azure Key Vault, etc.)
- Use read-only service accounts where possible
- Rotate API tokens regularly
- Enable audit logging in both Keycloak and Glean
- Run containers as non-root user (already configured)

## Troubleshooting

### Authentication Failures
- Verify Keycloak client credentials
- Check service account has required roles
- Ensure realm name is correct

### API Errors
- Check network connectivity to both services
- Verify API endpoints are accessible
- Review rate limits and quotas

### Data Issues
- Use dry-run mode to inspect formatted data
- Check log output for warnings about missing fields
- Verify user email addresses are populated in Keycloak

## Development

### Adding New Features

1. Create feature modules in appropriate directories
2. Update configuration in `settings.py` if needed
3. Add tests in `tests/` directory (create if needed)
4. Update this README

### Code Style

- Follow PEP 8 guidelines
- Use type hints for function signatures
- Document functions with docstrings
- Keep functions focused and single-purpose

## License

[Add your license here]

## Support

For issues and questions:
- Check logs with `LOG_LEVEL=DEBUG`
- Review Keycloak and Glean documentation
- Open an issue in the repository

## Changelog

### Version 1.0.0
- Initial release
- Keycloak user and group sync
- Glean People API integration
- Docker support
- Configurable via environment variables

