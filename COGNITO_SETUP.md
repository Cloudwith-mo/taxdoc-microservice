# Cognito Setup for ParsePilot

## Quick Setup (5 minutes)

### 1. Create User Pool
```bash
aws cognito-idp create-user-pool \
  --pool-name "ParsePilot-Users" \
  --policies '{
    "PasswordPolicy": {
      "MinimumLength": 8,
      "RequireUppercase": false,
      "RequireLowercase": false,
      "RequireNumbers": false,
      "RequireSymbols": false
    }
  }' \
  --auto-verified-attributes email \
  --username-attributes email
```

### 2. Create App Client
```bash
aws cognito-idp create-user-pool-client \
  --user-pool-id us-east-1_XXXXXXXXX \
  --client-name "ParsePilot-Web" \
  --generate-secret \
  --explicit-auth-flows ALLOW_USER_PASSWORD_AUTH ALLOW_REFRESH_TOKEN_AUTH \
  --supported-identity-providers COGNITO \
  --callback-urls "https://app.parsepilot.com/mvp2-enhanced.html" \
  --logout-urls "https://app.parsepilot.com/mvp2-enhanced.html" \
  --allowed-o-auth-flows code implicit \
  --allowed-o-auth-scopes openid email profile \
  --allowed-o-auth-flows-user-pool-client
```

### 3. Create Hosted UI Domain
```bash
aws cognito-idp create-user-pool-domain \
  --user-pool-id us-east-1_XXXXXXXXX \
  --domain parsepilot
```

### 4. Update Frontend Config
Replace in `mvp2-enhanced.html`:

```javascript
const cfg = {
    domain: "https://parsepilot.auth.us-east-1.amazoncognito.com",
    clientId: "YOUR_APP_CLIENT_ID",
    redirectUri: "https://app.parsepilot.com/mvp2-enhanced.html",
    logoutUri: "https://app.parsepilot.com/mvp2-enhanced.html",
    scope: "openid profile email"
};
```

### 5. Update API CORS
Add to all Lambda responses:
```javascript
headers: {
    'Access-Control-Allow-Origin': 'https://app.parsepilot.com',
    'Access-Control-Allow-Headers': 'Content-Type,Authorization',
    'Access-Control-Allow-Methods': 'GET,POST,PATCH,OPTIONS'
}
```

## Test Flow
1. Visit https://app.parsepilot.com/mvp2-enhanced.html
2. Click user dropdown → "Sign In"
3. Register/login via Cognito Hosted UI
4. Redirected back with JWT token
5. Upload document → appears in "My Documents"
6. Ask chatbot about extracted data → gets real answers
7. Analytics show live counts

## Environment Variables
```bash
export COGNITO_USER_POOL_ID="us-east-1_XXXXXXXXX"
export COGNITO_CLIENT_ID="7234567890abcdef"
export COGNITO_DOMAIN="parsepilot.auth.us-east-1.amazoncognito.com"
```

## What This Fixes
- ✅ Chatbot reads same data as Docs tab (JWT + userId)
- ✅ Persistent docs after login (Cognito sub vs ANON)
- ✅ Analytics show live data (auth headers)
- ✅ Secure API access (Bearer tokens)
- ✅ User sessions with refresh tokens