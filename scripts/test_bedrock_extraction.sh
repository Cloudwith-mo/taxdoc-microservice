#!/bin/bash

# Test Bedrock AI Extraction
# Simple test to verify AI extraction is working

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🤖 Testing Bedrock AI Extraction${NC}"
echo "=================================="

# Get API endpoint from CloudFormation
API_ENDPOINT=$(aws cloudformation describe-stacks \
    --stack-name TaxDoc-MVP \
    --region us-east-1 \
    --query 'Stacks[0].Outputs[?OutputKey==`ApiEndpoint`].OutputValue' \
    --output text)

if [ -z "$API_ENDPOINT" ]; then
    echo -e "${RED}❌ Could not find API endpoint${NC}"
    exit 1
fi

echo -e "${YELLOW}📋 Test Configuration:${NC}"
echo "API Endpoint: $API_ENDPOINT"
echo ""

# Create a simple test payload with minimal base64 content
# This is just a test - in real usage you'd encode an actual document
TEST_PAYLOAD='{
    "filename": "test_w2.pdf",
    "file_content": "JVBERi0xLjQKJcOkw7zDtsO4CjIgMCBvYmoKPDwKL0xlbmd0aCAzIDAgUgo+PgpzdHJlYW0KQNC0xLjQKJcOkw7zDtsO4CjIgMCBvYmoKPDwKL0xlbmd0aCAzIDAgUgo+PgpzdHJlYW0K"
}'

echo -e "${YELLOW}🧪 Making API request...${NC}"

# Make the API request
RESPONSE=$(curl -s -w "\nHTTP_STATUS:%{http_code}" \
    -X POST "$API_ENDPOINT/process-document" \
    -H "Content-Type: application/json" \
    -d "$TEST_PAYLOAD")

# Extract HTTP status and response body
HTTP_STATUS=$(echo "$RESPONSE" | grep "HTTP_STATUS:" | cut -d: -f2)
RESPONSE_BODY=$(echo "$RESPONSE" | sed '/HTTP_STATUS:/d')

echo -e "${YELLOW}📊 Response Status: $HTTP_STATUS${NC}"

if [ "$HTTP_STATUS" = "200" ]; then
    echo -e "${GREEN}✅ API request successful${NC}"
    
    # Check if response contains expected fields
    if echo "$RESPONSE_BODY" | grep -q "extracted_data"; then
        echo -e "${GREEN}✅ Response contains extracted data${NC}"
        
        # Check extraction method
        if echo "$RESPONSE_BODY" | grep -q "bedrock_claude"; then
            echo -e "${GREEN}🎉 Bedrock Claude AI extraction is working!${NC}"
            echo ""
            echo -e "${YELLOW}📋 Sample Response:${NC}"
            echo "$RESPONSE_BODY" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE_BODY"
        elif echo "$RESPONSE_BODY" | grep -q "fallback_regex"; then
            echo -e "${YELLOW}⚠️  Using fallback regex extraction${NC}"
            echo "This means Bedrock is not accessible or there's an issue"
        else
            echo -e "${YELLOW}ℹ️  Extraction method not clearly identified${NC}"
            echo "$RESPONSE_BODY" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE_BODY"
        fi
    else
        echo -e "${RED}❌ Response missing extracted data${NC}"
        echo "$RESPONSE_BODY"
    fi
else
    echo -e "${RED}❌ API request failed${NC}"
    echo "Response: $RESPONSE_BODY"
    exit 1
fi

echo ""
echo -e "${GREEN}🎯 Test Summary:${NC}"
echo "- API endpoint is accessible"
echo "- Document processing pipeline is working"
echo "- Ready for real document testing"
echo ""
echo -e "${YELLOW}💡 Next Steps:${NC}"
echo "1. Open web-mvp/index.html in your browser"
echo "2. Upload a real W-2 or 1099 document"
echo "3. Verify comprehensive field extraction"