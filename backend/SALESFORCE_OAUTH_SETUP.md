# Salesforce OAuth 2.0 Setup Guide

## Overview

This guide explains how to set up OAuth 2.0 authentication with Salesforce using **Client ID** and **Client Secret**. This is the **recommended and more secure** method compared to username/password/security token.

---

## 🎯 Why OAuth 2.0?

✅ **More Secure** - No need to expose passwords or security tokens  
✅ **No Security Token Issues** - Avoid token reset/expiration problems  
✅ **Better for Production** - Industry standard for API authentication  
✅ **Granular Permissions** - Control exactly what permissions the app has  
✅ **Easier Maintenance** - Tokens can be refreshed without password changes  

---

## 📋 Step-by-Step Setup

### Step 1: Create a Connected App in Salesforce

1. **Log in to Salesforce** (as an admin)

2. **Navigate to Setup**
   - Click the gear icon ⚙️ in the top right
   - Select "Setup"

3. **Go to App Manager**
   - In Setup, use Quick Find and search for "App Manager"
   - Click "App Manager" under Apps

4. **Create New Connected App**
   - Click "New Connected App" button
   - Fill in the following:

#### Basic Information
```
Connected App Name: Customer360 Copilot
API Name: Customer360_Copilot (auto-generated)
Contact Email: your-email@company.com
```

#### API (Enable OAuth Settings)
- ✅ Check "Enable OAuth Settings"

**Callback URL:**
```
https://login.salesforce.com/services/oauth2/callback
```
For sandbox:
```
https://test.salesforce.com/services/oauth2/callback
```

**Selected OAuth Scopes** - Add these scopes:
- ✅ `Access and manage your data (api)`
- ✅ `Perform requests on your behalf at any time (refresh_token, offline_access)`
- ✅ `Access unique user identifiers (openid)`

#### Additional Settings
- ✅ Check "Require Secret for Web Server Flow"
- ✅ Check "Require Secret for Refresh Token Flow"
- ✅ Check "Enable Client Credentials Flow" (if available - for client_credentials grant)

5. **Save** the Connected App

6. **Wait 2-10 minutes** for Salesforce to propagate the changes

---

### Step 2: Get Your Client ID and Client Secret

1. **Go back to App Manager**
   - Find your "Customer360 Copilot" app
   - Click the dropdown arrow ▼ next to it
   - Select "View"

2. **Manage Consumer Details**
   - Click "Manage Consumer Details" button
   - You may need to verify your identity

3. **Copy Credentials**
   - **Consumer Key** = This is your `SALESFORCE_CLIENT_ID`
   - **Consumer Secret** = This is your `SALESFORCE_CLIENT_SECRET`

⚠️ **Important:** Save these securely - you'll need them for your `.env` file!

---

### Step 3: Configure Permissions (Important!)

#### Option A: OAuth 2.0 Password Grant (Easier - Recommended)

This method uses your username/password + client credentials.

**Permissions Required:**
- The Connected App needs to be accessible to your user profile
- Your user needs API access enabled

**Steps:**
1. In App Manager, find your Connected App
2. Click dropdown → "Manage"
3. Scroll to "OAuth Policies"
4. **Permitted Users:** Select "Admin approved users are pre-authorized"
5. Click "Save"
6. Scroll down to "Profiles" or "Permission Sets"
7. Click "Manage Profiles" or "Manage Permission Sets"
8. Add your user's profile (e.g., "System Administrator")
9. Save

#### Option B: OAuth 2.0 Client Credentials Grant (More Advanced)

This method doesn't require username/password, only client credentials.

**Requirements:**
- Salesforce Enterprise Edition or higher
- **Important:** Client Credentials flow requires special setup with JWT Bearer tokens
- Not recommended for beginners

---

### Step 4: Configure Your `.env` File

Create or update your `.env` file with the following:

#### Method 1: OAuth Password Grant (Recommended)
```env
# Salesforce OAuth 2.0 Configuration
SALESFORCE_CLIENT_ID=your_consumer_key_here
SALESFORCE_CLIENT_SECRET=your_consumer_secret_here
SALESFORCE_USERNAME=your-username@company.com
SALESFORCE_PASSWORD=your-password
SALESFORCE_SECURITY_TOKEN=your-security-token
SALESFORCE_DOMAIN=login  # or 'test' for sandbox

# Other required settings
GOOGLE_API_KEY=your-google-api-key
JWT_SECRET_KEY=your-jwt-secret-key
```

#### Method 2: OAuth Only (If client credentials flow is set up)
```env
# Salesforce OAuth 2.0 Configuration (No password needed)
SALESFORCE_CLIENT_ID=your_consumer_key_here
SALESFORCE_CLIENT_SECRET=your_consumer_secret_here
SALESFORCE_DOMAIN=login  # or 'test' for sandbox

# Other required settings
GOOGLE_API_KEY=your-google-api-key
JWT_SECRET_KEY=your-jwt-secret-key
```

#### Method 3: Traditional Username/Password (Fallback)
```env
# Salesforce Traditional Authentication
SALESFORCE_USERNAME=your-username@company.com
SALESFORCE_PASSWORD=your-password
SALESFORCE_SECURITY_TOKEN=your-security-token
SALESFORCE_DOMAIN=login  # or 'test' for sandbox

# Other required settings
GOOGLE_API_KEY=your-google-api-key
JWT_SECRET_KEY=your-jwt-secret-key
```

---

### Step 5: Test the Connection

1. **Restart your backend server:**
   ```bash
   cd backend
   python -m uvicorn app.main:app --reload --port 8000
   ```

2. **Check the startup logs:**
   - You should see: `🔐 Attempting Salesforce connection using OAuth 2.0...`
   - If successful: `✅ OAuth token obtained successfully`

3. **Test the health check endpoint:**
   ```bash
   curl http://localhost:8000/api/v1/salesforce/health
   ```

   Or use the test script:
   ```bash
   python test_sf_health.py
   ```

---

## 🔍 Authentication Flow Details

### OAuth 2.0 Password Grant Flow (What We Use)

```
1. Your App sends request to Salesforce:
   POST https://login.salesforce.com/services/oauth2/token
   {
     grant_type: "password",
     client_id: "your_client_id",
     client_secret: "your_client_secret",
     username: "user@company.com",
     password: "password+security_token"
   }

2. Salesforce validates and returns:
   {
     access_token: "00D...",
     instance_url: "https://yourinstance.salesforce.com",
     token_type: "Bearer",
     ...
   }

3. Your App uses access_token for all API calls
```

---

## 🐛 Troubleshooting

### Error: "invalid_client_id"
**Cause:** Client ID is incorrect or Connected App not found

**Solution:**
- Double-check your `SALESFORCE_CLIENT_ID` matches the Consumer Key exactly
- Make sure the Connected App is saved and deployed
- Wait 2-10 minutes after creating the Connected App

### Error: "invalid_client"
**Cause:** Client Secret is incorrect

**Solution:**
- Verify your `SALESFORCE_CLIENT_SECRET` matches the Consumer Secret
- Check for extra spaces or characters when copying
- You may need to regenerate the secret if it was previously reset

### Error: "invalid_grant"
**Cause:** Username, password, or security token is incorrect

**Solution:**
- Verify username and password are correct
- Make sure you're concatenating password + security token
- Reset security token if needed
- For sandbox, make sure username includes the sandbox name (e.g., `user@company.com.sandbox`)

### Error: "unsupported_grant_type"
**Cause:** The grant type is not enabled for your Connected App

**Solution:**
- Go to Connected App settings
- Make sure "Enable OAuth Settings" is checked
- For password grant: Ensure your user has access to the Connected App
- For client credentials: Enable "Enable Client Credentials Flow" (requires special setup)

### Error: "user hasn't approved this consumer"
**Cause:** User doesn't have permission to use the Connected App

**Solution:**
- Go to Connected App → Manage
- Set "Permitted Users" to "Admin approved users are pre-authorized"
- Add your user's profile to the allowed profiles
- Or set "Permitted Users" to "All users may self-authorize"

---

## 🔒 Security Best Practices

1. **Never commit `.env` to git**
   ```bash
   # Add to .gitignore
   .env
   .env.*
   ```

2. **Rotate secrets regularly**
   - Regenerate Client Secret every 90 days
   - Update password periodically

3. **Use minimum required permissions**
   - Only grant scopes your app actually needs
   - Use Profile/Permission Set restrictions

4. **Store secrets securely**
   - Use environment variables, not hardcoded values
   - Consider using secret management services (AWS Secrets Manager, Azure Key Vault, etc.)

5. **Monitor API usage**
   - Set up monitoring for unusual API activity
   - Use Salesforce Event Monitoring

---

## 📚 Additional Resources

- [Salesforce OAuth 2.0 Documentation](https://help.salesforce.com/s/articleView?id=sf.remoteaccess_oauth_flows.htm)
- [Connected Apps Documentation](https://help.salesforce.com/s/articleView?id=sf.connected_app_overview.htm)
- [OAuth 2.0 Username-Password Flow](https://help.salesforce.com/s/articleView?id=sf.remoteaccess_oauth_username_password_flow.htm)

---

## 🎉 Success Indicators

When properly configured, you should see:

**In Backend Logs:**
```
🔐 Attempting Salesforce connection using OAuth 2.0...
   Using OAuth 2.0 Password Grant to https://login.salesforce.com/services/oauth2/token
✅ OAuth token obtained successfully
   Instance URL: https://yourinstance.salesforce.com
```

**In Health Check Response:**
```json
{
  "connected": true,
  "status": "connected",
  "message": "Salesforce connection is healthy",
  "details": {
    "instance_url": "https://yourinstance.salesforce.com",
    "api_version": "58.0",
    "session_active": true,
    "query_test": "passed"
  }
}
```

---

## ❓ Need Help?

If you're still having issues:

1. Check the backend logs for detailed error messages
2. Run the health check: `curl http://localhost:8000/api/v1/salesforce/health`
3. Verify all credentials in `.env` are correct
4. Make sure the Connected App has been saved and waited 2-10 minutes
5. Confirm your user profile has access to the Connected App
