#!/bin/bash

# Complete Dr.Doc System Deployment
# Usage: ./deploy_complete_system.sh [environment] [notification_email]

set -e

ENVIRONMENT=${1:-prod}
NOTIFICATION_EMAIL=${2:-admin@example.com}
REGION="us-east-1"

echo "🚀 Deploying Complete Dr.Doc System to ${ENVIRONMENT}"

# Step 1: Deploy main backend
echo "📦 Step 1: Deploying enhanced backend..."
sam build --template-file infrastructure/template.yaml
sam deploy \
    --stack-name "DrDoc-Enhanced-Final-${ENVIRONMENT}" \
    --parameter-overrides Environment="${ENVIRONMENT}" \
    --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM \
    --region "${REGION}" \
    --no-confirm-changeset \
    --resolve-s3

# Step 2: Deploy monitoring
echo "📊 Step 2: Deploying monitoring stack..."
aws cloudformation deploy \
    --template-file infrastructure/monitoring.yaml \
    --stack-name "DrDoc-Monitoring-${ENVIRONMENT}" \
    --parameter-overrides \
        Environment="${ENVIRONMENT}" \
        StackName="DrDoc-Enhanced-Final-${ENVIRONMENT}" \
        NotificationEmail="${NOTIFICATION_EMAIL}" \
    --capabilities CAPABILITY_IAM \
    --region "${REGION}"

# Step 3: Get outputs
echo "📋 Step 3: Getting deployment outputs..."
API_ENDPOINT=$(aws cloudformation describe-stacks \
    --stack-name "DrDoc-Enhanced-Final-${ENVIRONMENT}" \
    --region "${REGION}" \
    --query 'Stacks[0].Outputs[?OutputKey==`ApiEndpoint`].OutputValue' \
    --output text)

API_KEY=$(aws cloudformation describe-stacks \
    --stack-name "DrDoc-Enhanced-Final-${ENVIRONMENT}" \
    --region "${REGION}" \
    --query 'Stacks[0].Outputs[?OutputKey==`ApiKey`].OutputValue' \
    --output text)

UPLOAD_BUCKET=$(aws cloudformation describe-stacks \
    --stack-name "DrDoc-Enhanced-Final-${ENVIRONMENT}" \
    --region "${REGION}" \
    --query 'Stacks[0].Outputs[?OutputKey==`UploadBucket`].OutputValue' \
    --output text)

# Step 4: Deploy frontend
echo "🌐 Step 4: Deploying frontend..."
cd web-app

# Update environment file
cat > .env.production << EOF
REACT_APP_API_BASE=${API_ENDPOINT}
REACT_APP_API_KEY=${API_KEY}
EOF

# Build and deploy
npm run build
aws s3 sync build/ s3://taxdoc-web-app-prod-1754284862/ --delete

cd ..

echo "✅ Deployment completed successfully!"
echo ""
echo "📊 System Information:"
echo "   Environment: ${ENVIRONMENT}"
echo "   Region: ${REGION}"
echo ""
echo "🔗 Endpoints:"
echo "   API Base: ${API_ENDPOINT}"
echo "   Frontend: http://taxdoc-web-app-prod-1754284862.s3-website-us-east-1.amazonaws.com/"
echo ""
echo "🔑 API Key: ${API_KEY}"
echo ""
echo "📁 Resources:"
echo "   Upload Bucket: ${UPLOAD_BUCKET}"
echo ""
echo "📈 Monitoring:"
echo "   Dashboard: https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#dashboards"
echo "   Alerts: ${NOTIFICATION_EMAIL}"
echo ""
echo "🧪 Test the system:"
echo "   curl -X POST \"${API_ENDPOINT}/process-document\" \\"
echo "        -H \"Content-Type: application/json\" \\"
echo "        -H \"x-api-key: ${API_KEY}\" \\"
echo "        -d '{\"filename\": \"test.pdf\", \"file_content\": \"<base64_content>\"}'"