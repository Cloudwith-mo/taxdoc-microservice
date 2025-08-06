#!/bin/bash

# Deploy TaxDoc Enhanced with AI features
set -e

ENVIRONMENT=${1:-enhanced}
REGION=${2:-us-east-1}

echo "🚀 Deploying TaxDoc Enhanced to $ENVIRONMENT environment"

# Build and deploy
sam build -t infrastructure/enhanced-template.yaml
sam deploy \
  --template-file .aws-sam/build/template.yaml \
  --stack-name "TaxDoc-Enhanced-$ENVIRONMENT" \
  --parameter-overrides Environment=$ENVIRONMENT \
  --capabilities CAPABILITY_IAM \
  --region $REGION \
  --resolve-s3

# Get outputs
API_ENDPOINT=$(aws cloudformation describe-stacks \
  --stack-name "TaxDoc-Enhanced-$ENVIRONMENT" \
  --region $REGION \
  --query 'Stacks[0].Outputs[?OutputKey==`ApiEndpoint`].OutputValue' \
  --output text)

DASHBOARD_URL=$(aws cloudformation describe-stacks \
  --stack-name "TaxDoc-Enhanced-$ENVIRONMENT" \
  --region $REGION \
  --query 'Stacks[0].Outputs[?OutputKey==`DashboardUrl`].OutputValue' \
  --output text)

echo "✅ Enhanced deployment complete!"
echo "📡 API Endpoint: $API_ENDPOINT"
echo "📊 Dashboard: $DASHBOARD_URL"
echo "🌐 Update frontend API_ENDPOINT to: $API_ENDPOINT"