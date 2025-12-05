# Quick Start Guide - Salesforce Health Check

## Files Modified/Created

### ✅ Modified Files
1. **`backend/app/services/salesforce_service.py`**
   - Added `check_connection()` method for health checking

2. **`backend/app/api/routes.py`**
   - Added `/api/v1/salesforce/health` endpoint

### 📄 New Documentation Files
1. **`backend/SALESFORCE_HEALTH_CHECK.md`** - Full documentation
2. **`backend/test_sf_health.py`** - Test script

---

## Quick Test (3 Steps)

### Step 1: Ensure `.env` file exists with Salesforce credentials

⚠️ **The application now supports TWO authentication methods:**

#### ✅ **Method 1: OAuth 2.0 (RECOMMENDED)**
This is more secure and doesn't have security token issues.

**Setup Required:**
1. Create a Connected App in Salesforce (takes 5-10 minutes)
2. Get your Client ID and Client Secret
3. See **[SALESFORCE_OAUTH_SETUP.md](file:///c:/Projects/Ashok/Customer360-copilot/customer360-copilot/backend/SALESFORCE_OAUTH_SETUP.md)** for detailed instructions

Create `backend/.env` file with:
```env
# OAuth 2.0 Configuration
SALESFORCE_CLIENT_ID=your-consumer-key-from-connected-app
SALESFORCE_CLIENT_SECRET=your-consumer-secret-from-connected-app
SALESFORCE_USERNAME=your-username@example.com
SALESFORCE_PASSWORD=your-password
SALESFORCE_SECURITY_TOKEN=your-security-token
SALESFORCE_DOMAIN=login  # or 'test' for sandbox

# Required settings
GOOGLE_API_KEY=your-google-api-key
JWT_SECRET_KEY=your-secret-key-here
```

#### 🔄 **Method 2: Traditional Username/Password (Fallback)**
Use this if you can't set up OAuth right now.

Create `backend/.env` file with:
```env
# Traditional Authentication
SALESFORCE_USERNAME=your-username@example.com
SALESFORCE_PASSWORD=your-password
SALESFORCE_SECURITY_TOKEN=your-security-token
SALESFORCE_DOMAIN=login  # or 'test' for sandbox

# Required settings
GOOGLE_API_KEY=your-google-api-key
JWT_SECRET_KEY=your-secret-key-here
```

💡 **Tip:** Copy `.env.template` to `.env` and fill in your values!

### Step 2: Start the backend server

```bash
cd backend
python -m uvicorn app.main:app --reload --port 8000
```

### Step 3: Test the health check endpoint

**Option A - Using Browser:**
```
http://localhost:8000/api/v1/salesforce/health
```

**Option B - Using cURL:**
```bash
curl http://localhost:8000/api/v1/salesforce/health
```

**Option C - Using the test script:**
```bash
cd backend
python test_sf_health.py
```

---

## Expected Responses

### ✅ Success (When SF is connected)
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
  }
}
```

### ❌ Failure (When credentials are wrong)
```json
{
  "connected": false,
  "status": "error",
  "message": "Connection exists but API call failed: ...",
  "error": "INVALID_LOGIN: Invalid credentials"
}
```

### ⚠️ Not Configured (When .env is missing/incomplete)
```json
{
  "connected": false,
  "status": "disconnected",
  "message": "Salesforce connection not established. Please verify credentials.",
  "error": "Connection object is None"
}
```

---

## Common Issues & Fixes

| Issue | Cause | Fix |
|-------|-------|-----|
| `INVALID_LOGIN` | Wrong username/password/token | Reset security token & update `.env` |
| `Connection object is None` | Missing `.env` file | Create `.env` with all required fields |
| `Connection refused` | Backend not running | Start server with `uvicorn` command |
| Custom domain error | Wrong domain format | Use domain without `https://` prefix |

---

## Integration Example (Frontend)

```javascript
// Check Salesforce health before making API calls
async function checkSalesforceHealth() {
  try {
    const response = await fetch('http://localhost:8000/api/v1/salesforce/health');
    const health = await response.json();
    
    if (health.connected) {
      console.log('✅ Salesforce is ready');
      return true;
    } else {
      console.error('❌ Salesforce error:', health.message);
      // Show error to user
      showError(`Salesforce connection failed: ${health.message}`);
      return false;
    }
  } catch (error) {
    console.error('❌ Backend unreachable:', error);
    return false;
  }
}

// Use it before making SF API calls
if (await checkSalesforceHealth()) {
  // Safe to make Salesforce API calls
  const caseData = await fetchCaseData(caseId);
}
```

---

## Need More Help?

- See **`SALESFORCE_HEALTH_CHECK.md`** for complete documentation
- Run **`python test_sf_health.py`** for diagnostic information
- Check backend logs for detailed error messages
