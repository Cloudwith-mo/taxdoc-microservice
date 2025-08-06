#!/bin/bash

# Enable AI Extraction for TaxDoc MVP
# This script sets up Claude API key and redeploys with AI enabled

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🤖 Enabling AI Extraction for TaxDoc MVP${NC}"
echo "=============================================="

# Check if Claude API key is provided
if [ -z "$1" ]; then
    echo -e "${RED}Error: Claude API key required${NC}"
    echo "Usage: $0 <claude-api-key>"
    echo ""
    echo "To get a Claude API key:"
    echo "1. Visit https://console.anthropic.com/"
    echo "2. Create an account and get API access"
    echo "3. Generate an API key"
    echo ""
    echo "Example: $0 sk-ant-api03-your-key-here"
    exit 1
fi

CLAUDE_API_KEY="$1"
STACK_NAME="TaxDoc-MVP"
ENVIRONMENT="mvp"
REGION="us-east-1"

echo -e "${YELLOW}🔑 Setting up Claude API key...${NC}"
export CLAUDE_API_KEY="$CLAUDE_API_KEY"

echo -e "${YELLOW}☁️ Redeploying with AI extraction enabled...${NC}"

# Deploy with Claude API key
sam deploy \
    --template-file infrastructure/tax-mvp-template.yaml \
    --stack-name $STACK_NAME \
    --parameter-overrides \
        Environment=$ENVIRONMENT \
        ClaudeApiKey=$CLAUDE_API_KEY \
    --capabilities CAPABILITY_IAM \
    --region $REGION \
    --resolve-s3

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ AI extraction enabled successfully!${NC}"
    
    # Get API endpoint
    API_ENDPOINT=$(aws cloudformation describe-stacks \
        --stack-name $STACK_NAME \
        --region $REGION \
        --query 'Stacks[0].Outputs[?OutputKey==`ApiEndpoint`].OutputValue' \
        --output text)
    
    echo ""
    echo -e "${GREEN}🎉 TaxDoc MVP with AI Extraction Ready!${NC}"
    echo "========================================"
    echo ""
    echo -e "${YELLOW}📋 System Status:${NC}"
    echo "✅ Claude AI: ENABLED"
    echo "✅ Comprehensive W-2 extraction: ALL FIELDS"
    echo "✅ API Endpoint: $API_ENDPOINT"
    echo ""
    echo -e "${YELLOW}🧪 Test with comprehensive extraction:${NC}"
    echo "Open web-mvp/index.html and upload a W-2 form"
    echo "You should now see ALL W-2 fields extracted with high accuracy"
    echo ""
    echo -e "${GREEN}✨ Ready for full AI-powered document processing!${NC}"
else
    echo -e "${RED}❌ Deployment failed${NC}"
    exit 1
fi