# DocumentGPT Setup Guide

## 🚨 Current Issues and Solutions

### Issue 1: 401 Missing Authorization Error
**Problem**: The upload fails with "Presign failed: 401 Missing Authorization"
**Cause**: The API Gateway is not properly configured to handle authentication or the Lambda function is missing proper permissions.

### Issue 2: Cognito Domain Not Found
**Problem**: The Cognito domain `documentgpt-io-17575657.auth.us-east-1.amazoncognito.com` doesn't exist
**Cause**: The Cognito User Pool hasn't been created or the domain is misconfigured.

## 📋 Complete Setup Instructions

### Step 1: Create AWS Cognito User Pool

```bash
# Create User Pool
aws cognito-idp create-user-pool \
  --pool-name "DocumentGPT-Users" \
  --policies '{
    "PasswordPolicy": {
      "MinimumLength": 8,
      "RequireUppercase": true,
      "RequireLowercase": true,
      "RequireNumbers": true,
      "RequireSymbols": false
    }
  }' \
  --auto-verified-attributes email \
  --username-attributes email \
  --mfa-configuration OFF \
  --account-recovery-setting '{
    "RecoveryMechanisms": [
      {
        "Priority": 1,
        "Name": "verified_email"
      }
    ]
  }' \
  --region us-east-1
```

Save the `UserPoolId` from the response.

### Step 2: Create App Client

```bash
# Replace YOUR_USER_POOL_ID with the actual ID from Step 1
aws cognito-idp create-user-pool-client \
  --user-pool-id YOUR_USER_POOL_ID \
  --client-name "DocumentGPT-Web" \
  --no-generate-secret \
  --explicit-auth-flows \
    ALLOW_USER_PASSWORD_AUTH \
    ALLOW_REFRESH_TOKEN_AUTH \
    ALLOW_USER_SRP_AUTH \
  --supported-identity-providers COGNITO \
  --callback-urls \
    "http://localhost:3000/documentgpt.html" \
    "https://yourdomain.com/documentgpt.html" \
  --logout-urls \
    "http://localhost:3000/documentgpt.html" \
    "https://yourdomain.com/documentgpt.html" \
  --allowed-o-auth-flows code implicit \
  --allowed-o-auth-scopes openid email profile \
  --allowed-o-auth-flows-user-pool-client \
  --region us-east-1
```

Save the `ClientId` from the response.

### Step 3: Create Cognito Domain

```bash
# Choose a unique domain prefix (e.g., documentgpt-yourcompany)
aws cognito-idp create-user-pool-domain \
  --user-pool-id YOUR_USER_POOL_ID \
  --domain documentgpt-yourcompany \
  --region us-east-1
```

Your domain will be: `https://documentgpt-yourcompany.auth.us-east-1.amazoncognito.com`

### Step 4: Update the HTML Configuration

Edit `/workspace/web-app/public/documentgpt.html` and update the configuration:

```javascript
const COGNITO_CONFIG = {
    domain: "https://documentgpt-yourcompany.auth.us-east-1.amazoncognito.com",
    clientId: "YOUR_CLIENT_ID_FROM_STEP_2",
    redirectUri: window.location.origin + window.location.pathname,
    logoutUri: window.location.origin + window.location.pathname,
    scope: "openid email profile offline_access"
};
```

### Step 5: Fix API Gateway Authentication

#### Option A: Public API (Quick Fix - Not Recommended for Production)
Update your Lambda functions to not require authentication for testing:

```javascript
// In your Lambda handler
exports.handler = async (event) => {
    // Add CORS headers
    const headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,Authorization',
        'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
    };
    
    // Handle OPTIONS request
    if (event.httpMethod === 'OPTIONS') {
        return {
            statusCode: 200,
            headers,
            body: ''
        };
    }
    
    // Your existing logic here...
    
    return {
        statusCode: 200,
        headers,
        body: JSON.stringify(result)
    };
};
```

#### Option B: Secure API with Cognito (Recommended)

1. **Add Cognito Authorizer to API Gateway**:
```bash
# Create authorizer
aws apigateway create-authorizer \
  --rest-api-id YOUR_API_ID \
  --name DocumentGPT-Authorizer \
  --type COGNITO_USER_POOLS \
  --provider-arns arn:aws:cognito-idp:us-east-1:YOUR_ACCOUNT:userpool/YOUR_USER_POOL_ID \
  --identity-source method.request.header.Authorization \
  --region us-east-1
```

2. **Update API Methods to Use Authorizer**:
```bash
# For each method that needs protection
aws apigateway update-method \
  --rest-api-id YOUR_API_ID \
  --resource-id YOUR_RESOURCE_ID \
  --http-method POST \
  --patch-operations \
    op=replace,path=/authorizationType,value=COGNITO_USER_POOLS \
    op=replace,path=/authorizerId,value=YOUR_AUTHORIZER_ID \
  --region us-east-1
```

3. **Deploy API Changes**:
```bash
aws apigateway create-deployment \
  --rest-api-id YOUR_API_ID \
  --stage-name prod \
  --region us-east-1
```

### Step 6: Update Lambda Functions

Create or update the upload URL handler:

```javascript
// upload_url_handler.js
exports.handler = async (event) => {
    const headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,Authorization',
        'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
    };
    
    if (event.httpMethod === 'OPTIONS') {
        return { statusCode: 200, headers, body: '' };
    }
    
    try {
        const body = JSON.parse(event.body || '{}');
        const { filename, contentType } = body;
        
        // Generate a unique document ID
        const documentId = `doc_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
        
        // Create S3 presigned URL
        const AWS = require('aws-sdk');
        const s3 = new AWS.S3();
        
        const params = {
            Bucket: 'your-document-bucket',
            Key: `uploads/${documentId}/${filename}`,
            Expires: 300, // 5 minutes
            ContentType: contentType
        };
        
        const uploadUrl = await s3.getSignedUrlPromise('putObject', params);
        
        return {
            statusCode: 200,
            headers,
            body: JSON.stringify({
                uploadUrl,
                documentId
            })
        };
    } catch (error) {
        console.error('Error:', error);
        return {
            statusCode: 500,
            headers,
            body: JSON.stringify({ error: error.message })
        };
    }
};
```

### Step 7: Test the Setup

1. **Test Cognito Sign Up**:
```bash
aws cognito-idp sign-up \
  --client-id YOUR_CLIENT_ID \
  --username test@example.com \
  --password TestPass123! \
  --user-attributes Name=email,Value=test@example.com \
  --region us-east-1
```

2. **Confirm User** (if email verification is disabled):
```bash
aws cognito-idp admin-confirm-sign-up \
  --user-pool-id YOUR_USER_POOL_ID \
  --username test@example.com \
  --region us-east-1
```

3. **Test Authentication**:
```bash
aws cognito-idp initiate-auth \
  --client-id YOUR_CLIENT_ID \
  --auth-flow USER_PASSWORD_AUTH \
  --auth-parameters USERNAME=test@example.com,PASSWORD=TestPass123! \
  --region us-east-1
```

### Step 8: Deploy the Frontend

1. **Local Testing**:
```bash
cd /workspace/web-app
python3 -m http.server 3000
# Open http://localhost:3000/public/documentgpt.html
```

2. **Deploy to S3/CloudFront**:
```bash
# Create S3 bucket for hosting
aws s3 mb s3://documentgpt-frontend --region us-east-1

# Enable static website hosting
aws s3 website s3://documentgpt-frontend \
  --index-document documentgpt.html \
  --error-document error.html

# Upload files
aws s3 sync /workspace/web-app/public/ s3://documentgpt-frontend/ \
  --acl public-read

# The website will be available at:
# http://documentgpt-frontend.s3-website-us-east-1.amazonaws.com
```

## 🔧 Environment Variables

Create a `.env` file for local development:

```bash
# Cognito Configuration
COGNITO_USER_POOL_ID=us-east-1_XXXXXXXXX
COGNITO_CLIENT_ID=your-client-id-here
COGNITO_DOMAIN=documentgpt-yourcompany

# API Configuration
API_GATEWAY_URL=https://your-api-id.execute-api.us-east-1.amazonaws.com/prod

# S3 Configuration
S3_BUCKET_NAME=documentgpt-uploads
AWS_REGION=us-east-1
```

## 🚀 Quick Start Script

Save this as `setup-documentgpt.sh`:

```bash
#!/bin/bash

echo "🚀 Setting up DocumentGPT..."

# Configuration
POOL_NAME="DocumentGPT-Users"
CLIENT_NAME="DocumentGPT-Web"
DOMAIN_PREFIX="documentgpt-$(date +%s)"
REGION="us-east-1"

# Create User Pool
echo "Creating Cognito User Pool..."
USER_POOL_ID=$(aws cognito-idp create-user-pool \
  --pool-name "$POOL_NAME" \
  --auto-verified-attributes email \
  --username-attributes email \
  --region $REGION \
  --query 'UserPool.Id' \
  --output text)

echo "User Pool ID: $USER_POOL_ID"

# Create App Client
echo "Creating App Client..."
CLIENT_ID=$(aws cognito-idp create-user-pool-client \
  --user-pool-id $USER_POOL_ID \
  --client-name "$CLIENT_NAME" \
  --no-generate-secret \
  --explicit-auth-flows ALLOW_USER_PASSWORD_AUTH ALLOW_REFRESH_TOKEN_AUTH \
  --region $REGION \
  --query 'UserPoolClient.ClientId' \
  --output text)

echo "Client ID: $CLIENT_ID"

# Create Domain
echo "Creating Cognito Domain..."
aws cognito-idp create-user-pool-domain \
  --user-pool-id $USER_POOL_ID \
  --domain $DOMAIN_PREFIX \
  --region $REGION

COGNITO_DOMAIN="https://${DOMAIN_PREFIX}.auth.${REGION}.amazoncognito.com"
echo "Cognito Domain: $COGNITO_DOMAIN"

# Output configuration
echo ""
echo "✅ Setup Complete! Update your documentgpt.html with:"
echo ""
echo "const COGNITO_CONFIG = {"
echo "    domain: \"$COGNITO_DOMAIN\","
echo "    clientId: \"$CLIENT_ID\","
echo "    redirectUri: window.location.origin + window.location.pathname,"
echo "    logoutUri: window.location.origin + window.location.pathname,"
echo "    scope: \"openid email profile offline_access\""
echo "};"
```

Make it executable and run:
```bash
chmod +x setup-documentgpt.sh
./setup-documentgpt.sh
```

## 📝 Troubleshooting

### Issue: "This site can't be reached"
- **Solution**: The Cognito domain hasn't been created. Run the setup script above.

### Issue: "401 Missing Authorization"
- **Solution**: 
  1. Check if the API Gateway has CORS enabled
  2. Verify the Lambda function has proper IAM permissions
  3. Ensure the Authorization header is being sent with requests

### Issue: "Failed to load resource"
- **Solution**: Check browser console for CORS errors. Update API Gateway to allow your domain.

## 🔒 Security Best Practices

1. **Use HTTPS**: Always use HTTPS in production
2. **Restrict CORS**: Only allow your specific domains
3. **Enable MFA**: Enable multi-factor authentication for users
4. **Rotate Secrets**: Regularly rotate API keys and secrets
5. **Monitor Usage**: Set up CloudWatch alarms for unusual activity

## 📧 Support

If you continue to experience issues:
1. Check CloudWatch logs for Lambda functions
2. Verify IAM roles and permissions
3. Test with Postman or curl to isolate frontend issues
4. Contact AWS support for infrastructure issues