# People Data Exporter

A Python-based application that synchronizes user and group data from Keycloak to Glean's People API. This tool is designed to run in Docker for easy deployment on any cloud platform.

## Features

- 🔐 Fetches users and groups from Keycloak Admin API
- 📤 Pushes formatted data to Glean People API
- 🐳 Fully Dockerized for cloud deployment
- ⚙️ Environment-based configuration
- 📊 Comprehensive logging
- 🔄 Automatic retry logic for API calls
- 🧪 Dry-run mode for testing

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

Bulk indexing pushes all users in a single API call, which is faster and more efficient for large datasets:

```bash
GLEAN_USE_BULK_INDEX=true docker-compose up
```

### Individual Indexing

Individual indexing pushes users one at a time using the individual employee index API. This is useful when:
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

### Kubernetes

Example Kubernetes CronJob:

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: people-data-exporter
spec:
  schedule: "0 2 * * *"  # Run daily at 2 AM
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

### AWS ECS

1. Push Docker image to ECR
2. Create task definition with environment variables
3. Schedule task using EventBridge

### Google Cloud Run

```bash
gcloud run jobs create people-data-exporter \
  --image gcr.io/your-project/people-data-exporter \
  --set-env-vars-file .env \
  --region us-central1
```

### Azure Container Instances

```bash
az container create \
  --resource-group myResourceGroup \
  --name people-data-exporter \
  --image your-registry/people-data-exporter:latest \
  --environment-variables $(cat .env)
```

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

