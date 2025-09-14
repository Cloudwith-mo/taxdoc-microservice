#!/bin/bash

# DocumentGPT Quick Setup Script
# This script sets up AWS Cognito for DocumentGPT

set -e  # Exit on error

echo "🚀 DocumentGPT Setup Script"
echo "=========================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo -e "${RED}❌ AWS CLI is not installed. Please install it first.${NC}"
    echo "Visit: https://aws.amazon.com/cli/"
    exit 1
fi

# Check AWS credentials
if ! aws sts get-caller-identity &> /dev/null; then
    echo -e "${RED}❌ AWS credentials not configured. Run 'aws configure' first.${NC}"
    exit 1
fi

# Configuration
POOL_NAME="DocumentGPT-Users"
CLIENT_NAME="DocumentGPT-Web"
DOMAIN_PREFIX="documentgpt-$(date +%s)"
REGION="us-east-1"
BUCKET_NAME="documentgpt-uploads-$(date +%s)"

echo "Configuration:"
echo "  Region: $REGION"
echo "  User Pool Name: $POOL_NAME"
echo "  Domain Prefix: $DOMAIN_PREFIX"
echo "  S3 Bucket: $BUCKET_NAME"
echo ""

read -p "Continue with setup? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Setup cancelled."
    exit 1
fi

echo ""
echo "Step 1: Creating Cognito User Pool..."
echo "--------------------------------------"

USER_POOL_RESPONSE=$(aws cognito-idp create-user-pool \
  --pool-name "$POOL_NAME" \
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
  --region $REGION \
  --output json)

USER_POOL_ID=$(echo $USER_POOL_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['UserPool']['Id'])")
USER_POOL_ARN=$(echo $USER_POOL_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['UserPool']['Arn'])")

echo -e "${GREEN}✓ User Pool created: $USER_POOL_ID${NC}"

echo ""
echo "Step 2: Creating App Client..."
echo "-------------------------------"

# Get current origin for callback URLs
if [ -z "$DEPLOYMENT_URL" ]; then
    DEPLOYMENT_URL="http://localhost:3000"
fi

CLIENT_RESPONSE=$(aws cognito-idp create-user-pool-client \
  --user-pool-id $USER_POOL_ID \
  --client-name "$CLIENT_NAME" \
  --no-generate-secret \
  --explicit-auth-flows \
    ALLOW_USER_PASSWORD_AUTH \
    ALLOW_REFRESH_TOKEN_AUTH \
    ALLOW_USER_SRP_AUTH \
  --supported-identity-providers COGNITO \
  --callback-urls \
    "http://localhost:3000/documentgpt.html" \
    "http://localhost:3000/public/documentgpt.html" \
    "${DEPLOYMENT_URL}/documentgpt.html" \
  --logout-urls \
    "http://localhost:3000/documentgpt.html" \
    "http://localhost:3000/public/documentgpt.html" \
    "${DEPLOYMENT_URL}/documentgpt.html" \
  --allowed-o-auth-flows code implicit \
  --allowed-o-auth-scopes openid email profile \
  --allowed-o-auth-flows-user-pool-client \
  --region $REGION \
  --output json)

CLIENT_ID=$(echo $CLIENT_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['UserPoolClient']['ClientId'])")

echo -e "${GREEN}✓ App Client created: $CLIENT_ID${NC}"

echo ""
echo "Step 3: Creating Cognito Domain..."
echo "-----------------------------------"

aws cognito-idp create-user-pool-domain \
  --user-pool-id $USER_POOL_ID \
  --domain $DOMAIN_PREFIX \
  --region $REGION

COGNITO_DOMAIN="https://${DOMAIN_PREFIX}.auth.${REGION}.amazoncognito.com"

echo -e "${GREEN}✓ Domain created: $COGNITO_DOMAIN${NC}"

echo ""
echo "Step 4: Creating S3 Bucket for uploads..."
echo "------------------------------------------"

aws s3 mb s3://$BUCKET_NAME --region $REGION 2>/dev/null || echo "Bucket might already exist"

# Set CORS configuration for the bucket
cat > /tmp/cors.json << EOF
{
  "CORSRules": [
    {
      "AllowedHeaders": ["*"],
      "AllowedMethods": ["GET", "PUT", "POST", "DELETE", "HEAD"],
      "AllowedOrigins": ["*"],
      "ExposeHeaders": ["ETag"],
      "MaxAgeSeconds": 3000
    }
  ]
}
EOF

aws s3api put-bucket-cors --bucket $BUCKET_NAME --cors-configuration file:///tmp/cors.json --region $REGION

echo -e "${GREEN}✓ S3 bucket created: $BUCKET_NAME${NC}"

echo ""
echo "Step 5: Updating HTML configuration..."
echo "---------------------------------------"

# Update the documentgpt.html file with the new configuration
HTML_FILE="/workspace/web-app/public/documentgpt.html"

if [ -f "$HTML_FILE" ]; then
    # Create backup
    cp $HTML_FILE ${HTML_FILE}.backup
    
    # Update configuration using sed
    sed -i "s|https://YOUR-DOMAIN.auth.us-east-1.amazoncognito.com|$COGNITO_DOMAIN|g" $HTML_FILE
    sed -i "s|YOUR-CLIENT-ID|$CLIENT_ID|g" $HTML_FILE
    
    echo -e "${GREEN}✓ HTML file updated${NC}"
else
    echo -e "${YELLOW}⚠ HTML file not found at $HTML_FILE${NC}"
fi

echo ""
echo "Step 6: Creating test user..."
echo "------------------------------"

TEST_EMAIL="test@documentgpt.com"
TEST_PASSWORD="TestPass123!"

aws cognito-idp admin-create-user \
  --user-pool-id $USER_POOL_ID \
  --username $TEST_EMAIL \
  --user-attributes Name=email,Value=$TEST_EMAIL Name=email_verified,Value=true \
  --message-action SUPPRESS \
  --temporary-password $TEST_PASSWORD \
  --region $REGION 2>/dev/null || echo "User might already exist"

aws cognito-idp admin-set-user-password \
  --user-pool-id $USER_POOL_ID \
  --username $TEST_EMAIL \
  --password $TEST_PASSWORD \
  --permanent \
  --region $REGION 2>/dev/null || echo "Password might already be set"

echo -e "${GREEN}✓ Test user created${NC}"
echo "  Email: $TEST_EMAIL"
echo "  Password: $TEST_PASSWORD"

echo ""
echo "=========================================="
echo -e "${GREEN}✅ Setup Complete!${NC}"
echo "=========================================="
echo ""
echo "Configuration Summary:"
echo "----------------------"
echo "User Pool ID: $USER_POOL_ID"
echo "Client ID: $CLIENT_ID"
echo "Cognito Domain: $COGNITO_DOMAIN"
echo "S3 Bucket: $BUCKET_NAME"
echo ""
echo "Test Credentials:"
echo "-----------------"
echo "Email: $TEST_EMAIL"
echo "Password: $TEST_PASSWORD"
echo ""
echo "Next Steps:"
echo "-----------"
echo "1. Start local server:"
echo "   cd /workspace/web-app"
echo "   python3 -m http.server 3000"
echo ""
echo "2. Open browser:"
echo "   http://localhost:3000/public/documentgpt.html"
echo ""
echo "3. Click 'Sign In' and use the test credentials"
echo ""

# Save configuration to file
cat > /workspace/documentgpt-config.env << EOF
# DocumentGPT Configuration
# Generated: $(date)

COGNITO_USER_POOL_ID=$USER_POOL_ID
COGNITO_CLIENT_ID=$CLIENT_ID
COGNITO_DOMAIN=$COGNITO_DOMAIN
S3_BUCKET_NAME=$BUCKET_NAME
AWS_REGION=$REGION

# Test Credentials
TEST_EMAIL=$TEST_EMAIL
TEST_PASSWORD=$TEST_PASSWORD

# API Gateway (update this with your actual API)
API_GATEWAY_URL=https://iljpaj6ogl.execute-api.us-east-1.amazonaws.com/prod
EOF

echo "Configuration saved to: /workspace/documentgpt-config.env"
echo ""
echo -e "${YELLOW}⚠ Important: Update your Lambda functions with the S3 bucket name${NC}"
echo ""