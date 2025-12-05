# Salesforce Health Check API

## Overview

A dedicated API endpoint to verify Salesforce connection and diagnose connection issues. This endpoint tests the actual API connectivity by performing a simple SOQL query.

## Endpoint

```
GET /api/v1/salesforce/health
```

**Authentication:** Not required (public endpoint for health checking)

## Features

- ✅ Tests actual Salesforce API connectivity
- ✅ Provides detailed error messages for troubleshooting
- ✅ Returns instance URL and API version when connected
- ✅ No authentication required for quick health checks
- ✅ Performs a simple SOQL query to verify API access

## Usage

### Using cURL

```bash
curl http://localhost:8000/api/v1/salesforce/health
```

### Using Browser

Simply navigate to:
```
http://localhost:8000/api/v1/salesforce/health
```

### Using Python

```python
import requests

response = requests.get('http://localhost:8000/api/v1/salesforce/health')
health_status = response.json()

if health_status['connected']:
    print("✅ Salesforce is connected!")
    print(f"Instance: {health_status['details']['instance_url']}")
    print(f"API Version: {health_status['details']['api_version']}")
else:
    print("❌ Salesforce connection failed!")
    print(f"Error: {health_status['message']}")
```

### Using JavaScript/Fetch

```javascript
fetch('http://localhost:8000/api/v1/salesforce/health')
  .then(response => response.json())
  .then(data => {
    if (data.connected) {
      console.log('✅ Salesforce is connected!');
      console.log('Instance:', data.details.instance_url);
      console.log('API Version:', data.details.api_version);
    } else {
      console.error('❌ Salesforce connection failed!');
      console.error('Error:', data.message);
    }
  });
```

## Response Format

### Success Response (Connected)

```json
{
  "connected": true,
  "status": "connected",
  "message": "Salesforce connection is healthy",
  "details": {
    "instance_url": "https://your-instance.salesforce.com",
    "api_version": "58.0",
    "session_active": true,
    "query_test": "passed"
  },
  "timestamp": "2025-12-05T17:10:22.123456"
}
```

### Error Response (Connection Failed)

```json
{
  "connected": false,
  "status": "disconnected",
  "message": "Salesforce connection not established. Please verify credentials.",
  "error": "Connection object is None",
  "timestamp": "2025-12-05T17:10:22.123456"
}
```

### Error Response (API Call Failed)

```json
{
  "connected": false,
  "status": "error",
  "message": "Connection exists but API call failed: INVALID_SESSION_ID: Session expired or invalid",
  "error": "INVALID_SESSION_ID: Session expired or invalid",
  "error_type": "SalesforceExpiredSession",
  "timestamp": "2025-12-05T17:10:22.123456"
}
```

## Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `connected` | boolean | Whether Salesforce is successfully connected |
| `status` | string | Connection status: "connected", "disconnected", or "error" |
| `message` | string | Human-readable status message |
| `details` | object | Additional connection details (when connected) |
| `details.instance_url` | string | Your Salesforce instance URL |
| `details.api_version` | string | Salesforce API version being used |
| `details.session_active` | boolean | Whether the session is active |
| `details.query_test` | string | Result of the test query |
| `error` | string | Error message (when connection fails) |
| `error_type` | string | Type of exception (when connection fails) |
| `timestamp` | string | ISO 8601 timestamp of the health check |

## Troubleshooting

### 1. "Connection object is None"

**Cause:** Failed to create Salesforce connection during initialization.

**Solution:**
- Verify your `.env` file contains all required credentials:
  ```env
  SALESFORCE_USERNAME=your-username@example.com
  SALESFORCE_PASSWORD=your-password
  SALESFORCE_SECURITY_TOKEN=your-security-token
  SALESFORCE_DOMAIN=login  # or 'test' for sandbox
  ```
- For custom domains (e.g., sandbox), use format: `yourorg--sandbox.sandbox.my`
- Restart the backend server after updating credentials

### 2. "INVALID_LOGIN: Invalid username, password, security token"

**Cause:** Incorrect credentials or security token.

**Solution:**
- Verify username and password are correct
- Reset your security token in Salesforce:
  - Go to: Setup → My Personal Information → Reset My Security Token
  - Check your email for the new token
  - Update `SALESFORCE_SECURITY_TOKEN` in `.env`

### 3. "INVALID_SESSION_ID: Session expired or invalid"

**Cause:** Session has expired or credentials changed.

**Solution:**
- Restart the backend server to create a new session
- Verify credentials haven't changed in Salesforce

### 4. Custom Domain Issues

**Cause:** Incorrect domain format for custom/sandbox instances.

**Solution:**
- For production orgs: Use `SALESFORCE_DOMAIN=login`
- For sandbox orgs: Use `SALESFORCE_DOMAIN=test`
- For custom domains: Use format `yourorg--sandbox.sandbox.my` (without `https://`)

## Monitoring & Integration

### Continuous Monitoring

You can add this endpoint to your monitoring systems:

```bash
# Health check with status code
curl -f http://localhost:8000/api/v1/salesforce/health || echo "Salesforce is down!"
```

### Docker Health Check

Add to your `docker-compose.yml`:

```yaml
services:
  backend:
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/salesforce/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

### Kubernetes Liveness Probe

```yaml
livenessProbe:
  httpGet:
    path: /api/v1/salesforce/health
    port: 8000
  initialDelaySeconds: 30
  periodSeconds: 30
```

## Implementation Details

The health check performs the following steps:

1. **Connection Check**: Verifies the Salesforce connection object exists
2. **API Test**: Executes a simple SOQL query: `SELECT Id FROM User LIMIT 1`
3. **Response**: Returns detailed status including instance URL and API version

This ensures that:
- Credentials are valid
- Network connectivity is working
- API is enabled and accessible
- Session is active and not expired

## Related Files

- **API Route**: `backend/app/api/routes.py` - The health check endpoint
- **Service**: `backend/app/services/salesforce_service.py` - The `check_connection()` method
- **Config**: `backend/app/core/config.py` - Environment variable configuration

## FAQ

**Q: Do I need authentication to call this endpoint?**  
A: No, this is a public health check endpoint for quick diagnostics.

**Q: How often should I call this endpoint?**  
A: For monitoring, every 30-60 seconds is reasonable. For debugging, call it as needed.

**Q: Does this endpoint count against my Salesforce API limits?**  
A: Yes, each call makes one simple SOQL query that counts against your daily API limit, but the impact is minimal (1 API call per health check).

**Q: What if my Salesforce APIs are enabled but the call still fails?**  
A: Check the error message in the response. Common issues include:
  - Invalid credentials
  - Expired security token
  - Incorrect domain configuration
  - Network/firewall issues
  - API access not enabled for your user profile

**Q: Can I use this in production?**  
A: Yes, but consider adding rate limiting to prevent abuse since it's a public endpoint.
