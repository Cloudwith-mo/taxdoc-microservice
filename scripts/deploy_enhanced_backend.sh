#!/bin/bash

# Deploy Enhanced Dr.Doc Backend Pipeline
# Usage: ./deploy_enhanced_backend.sh [environment]

set -e

ENVIRONMENT=${1:-dev}
STACK_NAME="DrDoc-Enhanced-${ENVIRONMENT}"
REGION="us-east-1"

echo "🚀 Deploying Enhanced Dr.Doc Backend Pipeline to ${ENVIRONMENT}"

# Check if AWS CLI is configured
if ! aws sts get-caller-identity > /dev/null 2>&1; then
    echo "❌ AWS CLI not configured. Please run 'aws configure'"
    exit 1
fi

# Check if SAM CLI is installed
if ! command -v sam &> /dev/null; then
    echo "❌ SAM CLI not found. Please install AWS SAM CLI"
    exit 1
fi

# Build the application
echo "📦 Building SAM application..."
sam build --template-file infrastructure/template.yaml

# Deploy the stack
echo "🚀 Deploying stack: ${STACK_NAME}"
sam deploy \
    --template-file .aws-sam/build/template.yaml \
    --stack-name "${STACK_NAME}" \
    --parameter-overrides Environment="${ENVIRONMENT}" \
    --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM \
    --region "${REGION}" \
    --no-confirm-changeset \
    --resolve-s3

# Get stack outputs
echo "📋 Getting stack outputs..."
API_ENDPOINT=$(aws cloudformation describe-stacks \
    --stack-name "${STACK_NAME}" \
    --region "${REGION}" \
    --query 'Stacks[0].Outputs[?OutputKey==`ApiEndpoint`].OutputValue' \
    --output text)

UPLOAD_BUCKET=$(aws cloudformation describe-stacks \
    --stack-name "${STACK_NAME}" \
    --region "${REGION}" \
    --query 'Stacks[0].Outputs[?OutputKey==`UploadBucket`].OutputValue' \
    --output text)

echo "✅ Deployment completed successfully!"
echo ""
echo "📊 Stack Information:"
echo "   Stack Name: ${STACK_NAME}"
echo "   Environment: ${ENVIRONMENT}"
echo "   Region: ${REGION}"
echo ""
echo "🔗 API Endpoints:"
echo "   Base URL: ${API_ENDPOINT}"
echo "   Process Document: ${API_ENDPOINT}/process-document"
echo "   Get Result: ${API_ENDPOINT}/result/{doc_id}"
echo "   Download Excel: ${API_ENDPOINT}/download-excel/{doc_id}"
echo ""
echo "📁 Resources:"
echo "   Upload Bucket: ${UPLOAD_BUCKET}"
echo ""
echo "🧪 Test the API:"
echo "   curl -X POST \"${API_ENDPOINT}/process-document\" \\"
echo "        -H \"Content-Type: application/json\" \\"
echo "        -d '{\"filename\": \"test.pdf\", \"file_content\": \"<base64_content>\"}'"
echo ""
echo "📈 Monitor in CloudWatch:"
echo "   Namespace: DrDoc/Processing"
echo "   Metrics: ProcessingTime, ConfidenceScore, LayerUsage, ProcessingErrors"