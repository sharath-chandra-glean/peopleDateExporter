# Keycloak to Glean Field Mapping Guide

This document provides detailed information about how data is transformed from Keycloak to Glean.

## Core Field Mappings

### Direct Mappings

| Keycloak | Glean | Transform | Required |
|----------|-------|-----------|----------|
| `email` | `email` | None | Yes |
| `firstName` | `firstName` | None | No |
| `lastName` | `lastName` | None | No |
| `id` | `id` | None | No |

### Computed Fields

| Keycloak | Glean | Transform | Notes |
|----------|-------|-----------|-------|
| `enabled` (boolean) | `status` (enum) | `true` → `"CURRENT"`<br>`false` → `"FORMER"` | Always set |
| `createdTimestamp` (number) | `startDate` (date) | Unix timestamp (ms) → `YYYY-MM-DD` | Optional |

## Attributes Mapping

Keycloak stores custom user attributes in the `attributes` object. Each attribute can be:
- A string value
- An array of strings (we extract the first element)

### Supported Attributes

```javascript
// Keycloak attributes object
{
  "attributes": {
    "department": ["Sales"],           // → "Sales"
    "title": ["Senior Engineer"],      // → "Senior Engineer"
    "businessUnit": ["North America"], // → "North America"
    "phoneNumber": ["+1-555-0123"],    // → "+1-555-0123"
    "managerEmail": ["mgr@company.com"], // → "mgr@company.com"
    "bio": ["Employee bio text"],      // → "Employee bio text"
    "photoUrl": ["https://..."]        // → "https://..."
  }
}
```

## Complete Examples

### Example 1: Basic User

**Keycloak Input:**
```json
{
  "id": "5916b604-2a91-41fe-89f6-df8d6c7ac384",
  "username": "andriy.mysyk@glean.com",
  "firstName": "Andriy",
  "lastName": "Mysyk",
  "email": "andriy.mysyk@glean.com",
  "emailVerified": true,
  "createdTimestamp": 1752259262653,
  "enabled": true,
  "totp": false,
  "disableableCredentialTypes": [],
  "requiredActions": [],
  "notBefore": 0,
  "access": {
    "manage": false
  }
}
```

**Glean Output:**
```json
{
  "email": "andriy.mysyk@glean.com",
  "firstName": "Andriy",
  "lastName": "Mysyk",
  "id": "5916b604-2a91-41fe-89f6-df8d6c7ac384",
  "status": "CURRENT",
  "startDate": "2025-05-11"
}
```

### Example 2: User with Attributes

**Keycloak Input:**
```json
{
  "id": "5797cc81-da1c-442e-b010-b5a04149c314",
  "username": "awaneendra.tiwari@sasandbox.com",
  "firstName": "Awaneendra",
  "lastName": "Tiwari",
  "email": "awaneendra.tiwari@sasandbox.com",
  "emailVerified": true,
  "attributes": {
    "department": ["Sales"],
    "title": ["Sales Manager"],
    "phoneNumber": ["+1-555-0199"],
    "businessUnit": ["APAC"],
    "managerEmail": ["director@sasandbox.com"]
  },
  "createdTimestamp": 1753366940778,
  "enabled": true,
  "totp": false,
  "disableableCredentialTypes": [],
  "requiredActions": [],
  "notBefore": 0,
  "access": {
    "manage": false
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
  "businessUnit": "APAC",
  "phoneNumber": "+1-555-0199",
  "managerEmail": "director@sasandbox.com",
  "status": "CURRENT",
  "startDate": "2025-01-23"
}
```

### Example 3: Disabled User

**Keycloak Input:**
```json
{
  "id": "4620df2f-f9fd-4a44-b913-e266f934447b",
  "username": "aaditya.hg@glean.com",
  "firstName": "Aaditya H",
  "lastName": "Gururaj",
  "email": "aaditya.hg@glean.com",
  "emailVerified": true,
  "createdTimestamp": 1753083959551,
  "enabled": false,
  "totp": false,
  "disableableCredentialTypes": [],
  "requiredActions": [],
  "notBefore": 0,
  "access": {
    "manage": false
  }
}
```

**Glean Output:**
```json
{
  "email": "aaditya.hg@glean.com",
  "firstName": "Aaditya H",
  "lastName": "Gururaj",
  "id": "4620df2f-f9fd-4a44-b913-e266f934447b",
  "status": "FORMER",
  "startDate": "2025-01-20"
}
```

## Ignored Keycloak Fields

The following Keycloak fields are **not** mapped to Glean (as they're not relevant):

- `username` (unless you want to add custom handling)
- `emailVerified`
- `totp`
- `disableableCredentialTypes`
- `requiredActions`
- `notBefore`
- `access`

## Adding Custom Attributes

To add more custom attributes from Keycloak to Glean, you can:

1. **Set attributes in Keycloak** using the admin console or API
2. **Update the code** in `src/clients/glean_client.py` to map additional attributes

### Example: Adding Location

If you want to map location data:

1. In Keycloak, add attributes:
```json
{
  "attributes": {
    "city": ["San Francisco"],
    "state": ["CA"],
    "country": ["USA"]
  }
}
```

2. In `glean_client.py`, add to `format_user_for_glean()`:
```python
if "city" in attributes and attributes["city"]:
    city_value = attributes["city"]
    if isinstance(city_value, list) and city_value:
        if "structuredLocation" not in employee_data:
            employee_data["structuredLocation"] = {}
        employee_data["structuredLocation"]["city"] = city_value[0]
```

## API Payload Formats

### Individual Index API Call

```http
POST /api/index/v1/indexemployee
Content-Type: application/json
Authorization: Bearer <token>

{
  "datasource": "keycloak",
  "employee": {
    "email": "user@example.com",
    "firstName": "John",
    "lastName": "Doe",
    ...
  },
  "version": 0
}
```

### Bulk Index API Call

```http
POST /api/index/v1/bulkindexemployees
Content-Type: application/json
Authorization: Bearer <token>

{
  "employees": [
    {
      "email": "user1@example.com",
      "firstName": "John",
      ...
    },
    {
      "email": "user2@example.com",
      "firstName": "Jane",
      ...
    }
  ],
  "isFirstPage": true,
  "isLastPage": true,
  "disableStaleDataDeletionCheck": false
}
```

**Parameters:**
- `employees`: Array of employee objects
- `uploadId`: Auto-generated UUID v4 identifier for the upload session
- `isFirstPage`: Set to `true` for first page of multi-page uploads
- `isLastPage`: Set to `true` for last page of multi-page uploads
- `forceRestartUpload`: Force restart of an existing upload session
- `disableStaleDataDeletionCheck`: Prevent deletion of employees not in this upload

## Testing Field Mappings

Use dry-run mode to see the exact data that would be sent to Glean:

```bash
DRY_RUN=true LOG_LEVEL=DEBUG python -m src.main
```

This will log sample user data without actually pushing to Glean.

