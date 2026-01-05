# OpenAPI Specification - People Data Exporter

This directory contains the OpenAPI 3.0 specification for the People Data Exporter HTTP API.

## Files

- `openapi.yaml` - OpenAPI spec in YAML format (recommended)
- `openapi.json` - OpenAPI spec in JSON format

## API Overview

The People Data Exporter provides a simple HTTP API with three endpoints:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/` | GET | Service information |
| `/health` | GET | Health check |
| `/sync` | POST | Trigger data sync |

## Viewing the API Documentation

### Option 1: Swagger UI (Online)

1. Visit: https://editor.swagger.io/
2. Copy contents of `openapi.yaml` and paste into the editor
3. View interactive documentation with "Try it out" functionality

### Option 2: Swagger UI (Local)

```bash
# Using Docker
docker run -p 8081:8080 \
    -e SWAGGER_JSON=/openapi.yaml \
    -v $(pwd)/openapi.yaml:/openapi.yaml \
    swaggerapi/swagger-ui

# Visit: http://localhost:8081
```

### Option 3: Redoc (Local)

```bash
# Using npx
npx @redocly/cli preview-docs openapi.yaml

# Or with Docker
docker run -p 8081:80 \
    -e SPEC_URL=openapi.yaml \
    -v $(pwd)/openapi.yaml:/usr/share/nginx/html/openapi.yaml \
    redocly/redoc
```

### Option 4: Postman

1. Open Postman
2. Import → Link/File → Select `openapi.yaml`
3. View documentation and generate requests

## Example API Calls

### Health Check

```bash
# GCP Cloud Run (with authentication)
curl -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
    https://people-data-exporter-xxxxx-uc.a.run.app/health
```

**Response:**
```json
{
  "status": "healthy",
  "service": "people-data-exporter",
  "timestamp": "2025-01-23T10:30:00.000000"
}
```

### Trigger Sync

```bash
# GCP Cloud Run (with authentication)
curl -X POST \
    -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
    https://people-data-exporter-xxxxx-uc.a.run.app/sync
```

**Response (Success):**
```json
{
  "status": "success",
  "message": "Data sync completed successfully",
  "start_time": "2025-01-23T10:30:00.000000",
  "end_time": "2025-01-23T10:35:00.000000",
  "duration_seconds": 300
}
```

**Response (Error):**
```json
{
  "status": "error",
  "error_type": "sync_error",
  "message": "Failed to authenticate with Keycloak API",
  "timestamp": "2025-01-23T10:30:00.000000"
}
```

### Service Info

```bash
# GCP Cloud Run (with authentication)
curl -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
    https://people-data-exporter-xxxxx-uc.a.run.app/
```

**Response:**
```json
{
  "service": "people-data-exporter",
  "version": "1.0.0",
  "endpoints": {
    "health": "/health",
    "sync": "/sync (POST)"
  }
}
```

## Authentication

### GCP Cloud Run

Uses OIDC token-based authentication:

```bash
# Get token
TOKEN=$(gcloud auth print-identity-token)

# Make request
curl -H "Authorization: Bearer $TOKEN" \
    https://your-service-url/health
```

## Generating Client SDKs

### Python Client

```bash
# Install generator
pip install openapi-generator-cli

# Generate Python client
openapi-generator-cli generate \
    -i openapi.yaml \
    -g python \
    -o ./client/python
```

### TypeScript/JavaScript Client

```bash
npx @openapitools/openapi-generator-cli generate \
    -i openapi.yaml \
    -g typescript-axios \
    -o ./client/typescript
```

### Go Client

```bash
openapi-generator-cli generate \
    -i openapi.yaml \
    -g go \
    -o ./client/go
```

## Validation

Validate the OpenAPI spec:

```bash
# Using Redocly CLI
npx @redocly/cli lint openapi.yaml

# Using Swagger CLI
npm install -g @apidevtools/swagger-cli
swagger-cli validate openapi.yaml
```

## Testing with newman (Postman CLI)

```bash
# Install newman
npm install -g newman

# Import spec and run tests
newman run openapi.json
```

## API Monitoring

### Set up health check monitoring:

```bash
gcloud monitoring uptime-checks create https health-check \
    --resource-type=url \
    --host=people-data-exporter-xxxxx-uc.a.run.app \
    --port=443 \
    --path=/health
```

## Integration with API Gateway

### GCP API Gateway

1. Upload `openapi.yaml` to API Gateway
2. Configure authentication and rate limiting
3. Deploy to production

## Versioning

The API follows semantic versioning:
- **Major version** (1.x.x): Breaking changes
- **Minor version** (x.1.x): New features, backward compatible
- **Patch version** (x.x.1): Bug fixes

Current version: **1.0.0**

## Support

For issues or questions:
- Review the API specification
- Check deployment documentation
- Test with provided examples
- Verify authentication tokens

## Related Documentation

- [GCP Deployment Guide](../GCP_DEPLOYMENT.md)
- [Quick Start Guide](../QUICKSTART_GCP.md)
- [API Testing Script](../deploy/test-endpoints.sh)
- [Server Implementation](../src/server.py)

