#!/bin/bash

# TaxDoc V1 MVP Deployment Script
# Deploys the minimal viable product for tax document extraction

set -e

# Configuration
STACK_NAME="TaxDoc-MVP"
ENVIRONMENT="mvp"
REGION="us-east-1"
TEMPLATE_FILE="infrastructure/tax-mvp-template.yaml"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 TaxDoc V1 MVP Deployment${NC}"
echo "=================================="

# Check if Claude API key is provided
if [ -z "$CLAUDE_API_KEY" ]; then
    echo -e "${RED}Error: CLAUDE_API_KEY environment variable is required${NC}"
    echo "Please set your Claude API key:"
    echo "export CLAUDE_API_KEY='your-api-key-here'"
    exit 1
fi

# Check if AWS CLI is configured
if ! aws sts get-caller-identity > /dev/null 2>&1; then
    echo -e "${RED}Error: AWS CLI not configured${NC}"
    echo "Please run 'aws configure' first"
    exit 1
fi

echo -e "${YELLOW}📋 Deployment Configuration:${NC}"
echo "Stack Name: $STACK_NAME"
echo "Environment: $ENVIRONMENT"
echo "Region: $REGION"
echo "Template: $TEMPLATE_FILE"
echo ""

# Create deployment package
echo -e "${YELLOW}📦 Creating deployment package...${NC}"
cd src
zip -r ../tax-mvp-deployment.zip . -x "*.pyc" "*/__pycache__/*" "*/.*"
cd ..

# Deploy CloudFormation stack
echo -e "${YELLOW}☁️ Deploying CloudFormation stack...${NC}"
aws cloudformation deploy \
    --template-file $TEMPLATE_FILE \
    --stack-name $STACK_NAME \
    --parameter-overrides \
        Environment=$ENVIRONMENT \
        ClaudeApiKey=$CLAUDE_API_KEY \
    --capabilities CAPABILITY_IAM \
    --region $REGION

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Stack deployed successfully!${NC}"
else
    echo -e "${RED}❌ Stack deployment failed${NC}"
    exit 1
fi

# Get stack outputs
echo -e "${YELLOW}📊 Getting deployment information...${NC}"
API_ENDPOINT=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --region $REGION \
    --query 'Stacks[0].Outputs[?OutputKey==`ApiEndpoint`].OutputValue' \
    --output text)

BUCKET_NAME=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --region $REGION \
    --query 'Stacks[0].Outputs[?OutputKey==`BucketName`].OutputValue' \
    --output text)

FUNCTION_NAME=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --region $REGION \
    --query 'Stacks[0].Outputs[?OutputKey==`FunctionName`].OutputValue' \
    --output text)

# Update web interface with API endpoint
echo -e "${YELLOW}🌐 Updating web interface...${NC}"
sed -i.bak "s|https://your-api-gateway-url.amazonaws.com/prod/process-document|${API_ENDPOINT}/process-document|g" web-mvp/index.html

echo ""
echo -e "${GREEN}🎉 TaxDoc V1 MVP Deployed Successfully!${NC}"
echo "=========================================="
echo ""
echo -e "${YELLOW}📋 Deployment Details:${NC}"
echo "API Endpoint: $API_ENDPOINT"
echo "S3 Bucket: $BUCKET_NAME"
echo "Lambda Function: $FUNCTION_NAME"
echo ""
echo -e "${YELLOW}🌐 Frontend:${NC}"
echo "Open web-mvp/index.html in your browser to test"
echo ""
echo -e "${YELLOW}🧪 Test the API:${NC}"
echo "curl -X POST $API_ENDPOINT/process-document \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -d '{\"filename\": \"test.pdf\", \"file_content\": \"base64-content\"}'"
echo ""
echo -e "${YELLOW}📝 Next Steps:${NC}"
echo "1. Test with sample W-2 and 1099 documents"
echo "2. Monitor CloudWatch logs for any issues"
echo "3. Gather user feedback for V2 enhancements"
echo ""
echo -e "${GREEN}✨ Ready to process tax documents!${NC}"

# Clean up
rm -f tax-mvp-deployment.zip