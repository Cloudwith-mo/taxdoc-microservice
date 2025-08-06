#!/bin/bash

# Deploy TaxDoc MVP
set -e

ENVIRONMENT=${1:-mvp}
REGION=${2:-us-east-1}

echo "🚀 Deploying TaxDoc MVP to $ENVIRONMENT environment"

# Build and deploy
sam build -t infrastructure/mvp-template.yaml
sam deploy \
  --template-file .aws-sam/build/template.yaml \
  --stack-name "TaxDoc-MVP-$ENVIRONMENT" \
  --parameter-overrides Environment=$ENVIRONMENT \
  --capabilities CAPABILITY_IAM \
  --region $REGION \
  --no-confirm-changeset

# Get outputs
API_ENDPOINT=$(aws cloudformation describe-stacks \
  --stack-name "TaxDoc-MVP-$ENVIRONMENT" \
  --region $REGION \
  --query 'Stacks[0].Outputs[?OutputKey==`ApiEndpoint`].OutputValue' \
  --output text)

echo "✅ Deployment complete!"
echo "📡 API Endpoint: $API_ENDPOINT"
echo "🌐 Update frontend API_ENDPOINT to: $API_ENDPOINT/process-tax-form"