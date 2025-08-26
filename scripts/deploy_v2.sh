#!/bin/bash

# TaxDoc Pro v2.0 Deployment Script
# This script deploys the enhanced version with user accounts, payments, and premium features

set -e

ENVIRONMENT=${1:-prod}
STRIPE_SECRET_KEY=${2:-""}
STRIPE_WEBHOOK_SECRET=${3:-""}

echo "🚀 Deploying TaxDoc Pro v2.0 to $ENVIRONMENT environment..."

# Validate required parameters
if [ -z "$STRIPE_SECRET_KEY" ]; then
    echo "❌ Error: Stripe secret key is required"
    echo "Usage: ./deploy_v2.sh <environment> <stripe_secret_key> <stripe_webhook_secret>"
    exit 1
fi

if [ -z "$STRIPE_WEBHOOK_SECRET" ]; then
    echo "❌ Error: Stripe webhook secret is required"
    echo "Usage: ./deploy_v2.sh <environment> <stripe_secret_key> <stripe_webhook_secret>"
    exit 1
fi

# Set variables
STACK_NAME="DrDoc-v2-${ENVIRONMENT}"
REGION="us-east-1"
LAMBDA_PACKAGE="v2-lambda-package.zip"

echo "📦 Packaging Lambda functions..."

# Create temporary directory for packaging
mkdir -p temp_package
cd temp_package

# Copy Lambda handlers
cp ../src/handlers/stripe_handler.py .
cp ../src/handlers/enhanced_chatbot_handler.py .

# Install dependencies
pip install stripe boto3 -t .

# Create deployment package
zip -r ../${LAMBDA_PACKAGE} .
cd ..
rm -rf temp_package

echo "☁️ Deploying CloudFormation stack..."

# Deploy the CloudFormation stack
aws cloudformation deploy \
    --template-file infrastructure/v2-template.yaml \
    --stack-name $STACK_NAME \
    --parameter-overrides \
        Environment=$ENVIRONMENT \
        StripeSecretKey=$STRIPE_SECRET_KEY \
        StripeWebhookSecret=$STRIPE_WEBHOOK_SECRET \
    --capabilities CAPABILITY_NAMED_IAM \
    --region $REGION

echo "📋 Getting stack outputs..."

# Get stack outputs
USER_POOL_ID=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --region $REGION \
    --query 'Stacks[0].Outputs[?OutputKey==`UserPoolId`].OutputValue' \
    --output text)

USER_POOL_CLIENT_ID=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --region $REGION \
    --query 'Stacks[0].Outputs[?OutputKey==`UserPoolClientId`].OutputValue' \
    --output text)

API_URL=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --region $REGION \
    --query 'Stacks[0].Outputs[?OutputKey==`ApiGatewayUrl`].OutputValue' \
    --output text)

echo "🔧 Updating Lambda function code..."

# Update Lambda functions with actual code
STRIPE_FUNCTION_NAME="DrDoc-StripeHandler-${ENVIRONMENT}"
CHATBOT_FUNCTION_NAME="DrDoc-EnhancedChatbot-${ENVIRONMENT}"

aws lambda update-function-code \
    --function-name $STRIPE_FUNCTION_NAME \
    --zip-file fileb://${LAMBDA_PACKAGE} \
    --region $REGION

aws lambda update-function-code \
    --function-name $CHATBOT_FUNCTION_NAME \
    --zip-file fileb://${LAMBDA_PACKAGE} \
    --region $REGION

echo "🌐 Building and deploying frontend..."

# Navigate to web app directory
cd web-app

# Create environment file
cat > .env.production << EOF
REACT_APP_USER_POOL_ID=$USER_POOL_ID
REACT_APP_USER_POOL_CLIENT_ID=$USER_POOL_CLIENT_ID
REACT_APP_AWS_REGION=$REGION
REACT_APP_API_BASE_URL=$API_URL
REACT_APP_STRIPE_PUBLISHABLE_KEY=pk_test_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
REACT_APP_ENABLE_PAYMENTS=true
REACT_APP_ENABLE_SENTIMENT_ANALYSIS=true
REACT_APP_ENABLE_PREMIUM_FEATURES=true
EOF

# Install dependencies
npm install

# Build the application
npm run build

# Deploy to S3
BUCKET_NAME="taxdoc-web-app-v2-${ENVIRONMENT}"

# Create S3 bucket if it doesn't exist
aws s3 mb s3://$BUCKET_NAME --region $REGION 2>/dev/null || true

# Configure bucket for static website hosting
aws s3 website s3://$BUCKET_NAME \
    --index-document index.html \
    --error-document index.html

# Set bucket policy for public read access
cat > bucket-policy.json << EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "PublicReadGetObject",
            "Effect": "Allow",
            "Principal": "*",
            "Action": "s3:GetObject",
            "Resource": "arn:aws:s3:::$BUCKET_NAME/*"
        }
    ]
}
EOF

aws s3api put-bucket-policy \
    --bucket $BUCKET_NAME \
    --policy file://bucket-policy.json

# Upload build files
aws s3 sync build/ s3://$BUCKET_NAME --delete

# Clean up
rm bucket-policy.json
cd ..
rm $LAMBDA_PACKAGE

echo "✅ Deployment completed successfully!"
echo ""
echo "🌐 Frontend URL: http://$BUCKET_NAME.s3-website-$REGION.amazonaws.com"
echo "🔗 API URL: $API_URL"
echo "👥 User Pool ID: $USER_POOL_ID"
echo "📱 User Pool Client ID: $USER_POOL_CLIENT_ID"
echo ""
echo "📝 Next Steps:"
echo "1. Update your Stripe webhook endpoint to: $API_URL/payment/webhook"
echo "2. Update the REACT_APP_STRIPE_PUBLISHABLE_KEY in .env.production with your actual Stripe publishable key"
echo "3. Test the authentication flow"
echo "4. Test payment integration"
echo "5. Verify sentiment analysis is working"
echo ""
echo "🎉 TaxDoc Pro v2.0 is now live with enhanced features!"