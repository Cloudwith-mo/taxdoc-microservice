#!/bin/bash

# Quick TaxDoc Pro v2.0 Deployment
set -e

echo "🚀 TaxDoc Pro v2.0 Quick Deployment"
echo "=================================="

# Check if Stripe keys are provided
if [ -z "$1" ] || [ -z "$2" ]; then
    echo "❌ Missing Stripe credentials"
    echo ""
    echo "Usage: ./quick_deploy_v2.sh <stripe_secret_key> <stripe_webhook_secret>"
    echo ""
    echo "Example:"
    echo "./quick_deploy_v2.sh sk_test_xxxxx whsec_xxxxx"
    echo ""
    echo "📋 Get your keys from:"
    echo "1. Stripe Dashboard > Developers > API keys"
    echo "2. Create webhook first to get webhook secret"
    exit 1
fi

STRIPE_SECRET_KEY=$1
STRIPE_WEBHOOK_SECRET=$2
ENVIRONMENT="prod"
STACK_NAME="DrDoc-v2-${ENVIRONMENT}"

echo "🔧 Deploying infrastructure..."

# Deploy CloudFormation stack
aws cloudformation deploy \
    --template-file infrastructure/v2-template.yaml \
    --stack-name $STACK_NAME \
    --parameter-overrides \
        Environment=$ENVIRONMENT \
        StripeSecretKey=$STRIPE_SECRET_KEY \
        StripeWebhookSecret=$STRIPE_WEBHOOK_SECRET \
    --capabilities CAPABILITY_NAMED_IAM \
    --region us-east-1

# Get outputs
echo "📋 Getting deployment info..."
USER_POOL_ID=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --query 'Stacks[0].Outputs[?OutputKey==`UserPoolId`].OutputValue' --output text)
CLIENT_ID=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --query 'Stacks[0].Outputs[?OutputKey==`UserPoolClientId`].OutputValue' --output text)
API_URL=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --query 'Stacks[0].Outputs[?OutputKey==`ApiGatewayUrl`].OutputValue' --output text)

echo "✅ Deployment complete!"
echo ""
echo "📝 Your v2.0 Configuration:"
echo "=========================="
echo "User Pool ID: $USER_POOL_ID"
echo "Client ID: $CLIENT_ID"  
echo "API URL: $API_URL"
echo ""
echo "🔗 Next: Configure Stripe webhook to:"
echo "$API_URL/payment/webhook"