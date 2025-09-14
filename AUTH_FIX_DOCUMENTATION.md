# Authentication Fix Documentation

## Problem Summary
The application was receiving `401 Unauthorized` errors when trying to call the API Gateway endpoints (`/presign`, `/upload-url`) because:
1. The Authorization header with JWT token was not being sent with requests
2. The API Gateway has a Lambda authorizer that requires authentication
3. Users were not being prompted to sign in before attempting uploads

## Solution Implemented

### 1. Enhanced Authentication Module
Added/updated authentication handling in multiple frontend files:

#### Files Modified:
- `/workspace/web-app/s3-upload-frontend.html` - Added complete auth module with token management
- `/workspace/web-app/public/documentgpt.html` - Enhanced error handling and auth checks
- `/workspace/web-app/public/test-auth.html` - Created test page for debugging auth issues

### 2. Key Changes

#### A. Token Management
```javascript
const auth = (() => {
    const LS = {
        idToken: 'taxdoc_id_token',
        accessToken: 'taxdoc_access_token',
        refreshToken: 'taxdoc_refresh_token',
        user: 'taxdoc_user',
        username: 'taxdoc_username'
    };

    function getAuthHeaders() {
        const token = get(LS.accessToken) || get(LS.idToken);
        return token ? { 'Authorization': `Bearer ${token}` } : {};
    }
    
    // ... rest of auth module
})();
```

#### B. Pre-Upload Authentication Check
```javascript
async function processDocument(file) {
    // Check authentication first
    if (!auth.isAuthenticated()) {
        showMessage('error', '🔐 Please sign in to upload documents');
        if (confirm('Would you like to sign in now?')) {
            auth.signIn();
        }
        return;
    }
    // ... continue with upload
}
```

#### C. Enhanced Error Handling
```javascript
if (error.message.includes('401') || error.message.includes('Authentication')) {
    errorMessage = `🔐 Authentication Required\n\n${error.message}`;
    // Prompt to sign in
    if (confirm('Would you like to sign in now?')) {
        auth.signIn();
    }
}
```

#### D. Visual Authentication Status
- Added banner at top of page when not authenticated
- Clear messaging about authentication requirements
- One-click sign-in links

### 3. API Endpoints Configuration

The API Gateway expects authorization headers for these endpoints:
- `GET /upload-url` - Get presigned URL for S3 upload
- `GET /presign` - Legacy alias for upload-url
- `GET /presign1` - Another legacy alias
- `POST /process` - Process uploaded document

All requests to these endpoints now include:
```javascript
headers: {
    'Content-Type': 'application/json',
    ...auth.getAuthHeaders()  // Adds 'Authorization': 'Bearer <token>'
}
```

## Deployment Instructions

### 1. Deploy Frontend Changes
```bash
# Copy updated files to S3 (or your hosting location)
aws s3 cp /workspace/web-app/public/documentgpt.html s3://your-frontend-bucket/
aws s3 cp /workspace/web-app/s3-upload-frontend.html s3://your-frontend-bucket/
aws s3 cp /workspace/web-app/public/test-auth.html s3://your-frontend-bucket/

# Invalidate CloudFront cache if using CDN
aws cloudfront create-invalidation --distribution-id YOUR_DIST_ID --paths "/*"
```

### 2. Update Cognito Configuration
Ensure your Cognito User Pool client has the correct redirect URIs:
```javascript
// Add these redirect URIs in Cognito console:
https://yourdomain.com/documentgpt.html
https://yourdomain.com/s3-upload-frontend.html
https://yourdomain.com/test-auth.html
```

### 3. Environment Variables
Update the frontend files with your actual values:
```javascript
const API_BASE = 'https://YOUR-API-ID.execute-api.us-east-1.amazonaws.com/prod';
const COGNITO_CONFIG = {
    domain: "YOUR-DOMAIN.auth.us-east-1.amazoncognito.com",
    clientId: "YOUR-CLIENT-ID",
    redirectUri: window.location.origin + window.location.pathname,
    scope: "openid email profile"
};
```

## Testing the Fix

### 1. Use the Test Page
Navigate to `/test-auth.html` to:
- Check authentication status
- Test API endpoints with/without auth
- View token information
- Sign in/out

### 2. Manual Testing Steps
1. Open the application in an incognito/private browser window
2. Try to upload a document without signing in
3. You should see a prompt to sign in
4. Click "Sign In" and authenticate with Cognito
5. After redirect, try uploading again - should work

### 3. Verify Auth Headers
In browser DevTools Network tab:
1. Look for requests to `/upload-url` or `/presign`
2. Check Request Headers
3. Should see: `Authorization: Bearer eyJ...` (JWT token)

## Troubleshooting

### Issue: Still getting 401 errors
**Solutions:**
1. Clear browser cache and localStorage
2. Sign out and sign in again
3. Check token expiration (tokens expire after 1 hour by default)
4. Verify Cognito client ID and domain are correct

### Issue: "Missing Authorization" error
**Solutions:**
1. Ensure tokens are being stored in localStorage
2. Check browser console for any JavaScript errors
3. Verify auth.getAuthHeaders() is returning the token

### Issue: Redirect loop after sign in
**Solutions:**
1. Check Cognito redirect URI configuration
2. Ensure the redirect URI matches exactly (including trailing slashes)
3. Verify the application is properly handling the URL hash parameters

## Alternative Solutions

### Option 1: Make Endpoints Public (Not Recommended)
Remove authorization requirement from API Gateway for upload endpoints. This is not recommended for production as it allows anyone to upload files.

### Option 2: Use API Keys
Instead of Cognito JWT tokens, use API keys for authentication. Less secure but simpler to implement.

### Option 3: Server-Side Proxy
Create a backend service that handles authentication and proxies requests to S3. More complex but provides better security.

## Security Considerations

1. **Token Storage**: Tokens are stored in localStorage. Consider using sessionStorage for more sensitive applications.
2. **Token Expiration**: Implement token refresh logic to handle expired tokens gracefully.
3. **CORS**: Ensure CORS is properly configured on both API Gateway and S3 bucket.
4. **HTTPS**: Always use HTTPS in production to protect tokens in transit.

## Support

For issues or questions:
- Check browser console for detailed error messages
- Use the test page to diagnose authentication issues
- Review CloudWatch logs for Lambda function errors
- Contact support with specific error messages and screenshots