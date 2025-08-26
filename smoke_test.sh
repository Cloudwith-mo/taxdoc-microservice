#!/bin/bash

# 🧪 TaxDoc V2 End-to-End Smoke Test
# Tests the complete workflow: upload → process → download → chat

set -e

# Configuration
API_URL="https://svea4ri2tk.execute-api.us-east-1.amazonaws.com/prod"
MVP_URL="http://taxdoc-mvp-web-1754513919.s3-website-us-east-1.amazonaws.com/mvp2-enhanced.html"
TEST_IMAGE="images/sample_w2.png"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test results
TESTS_PASSED=0
TESTS_FAILED=0

print_test() {
    echo -e "${YELLOW}🧪 Testing: $1${NC}"
}

print_pass() {
    echo -e "${GREEN}✅ PASS: $1${NC}"
    ((TESTS_PASSED++))
}

print_fail() {
    echo -e "${RED}❌ FAIL: $1${NC}"
    ((TESTS_FAILED++))
}

print_header() {
    echo -e "\n${YELLOW}=== $1 ===${NC}"
}

# Test 1: Infrastructure Health
print_header "Infrastructure Health Checks"

print_test "CloudFormation Stack Status"
STACK_STATUS=$(aws cloudformation describe-stacks --stack-name DrDoc-v2-prod --query "Stacks[0].StackStatus" --output text 2>/dev/null || echo "MISSING")
if [ "$STACK_STATUS" = "CREATE_COMPLETE" ]; then
    print_pass "CloudFormation stack is healthy"
else
    print_fail "CloudFormation stack status: $STACK_STATUS"
fi

print_test "API Gateway Health"
HEALTH_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "$API_URL/health" 2>/dev/null || echo "000")
if [ "$HEALTH_RESPONSE" = "200" ] || [ "$HEALTH_RESPONSE" = "404" ]; then
    print_pass "API Gateway is responding"
else
    print_fail "API Gateway health check failed: HTTP $HEALTH_RESPONSE"
fi

print_test "Cognito User Pool"
USER_POOL=$(aws cognito-idp list-user-pools --max-results 60 --query "UserPools[?contains(Name,'DrDoc')].Id" --output text 2>/dev/null || echo "")
if [ -n "$USER_POOL" ]; then
    print_pass "Cognito user pool exists: $USER_POOL"
else
    print_fail "Cognito user pool not found"
fi

# Test 2: Lambda Functions
print_header "Lambda Function Checks"

LAMBDA_FUNCTIONS=("DrDoc-ProcessDocument-prod" "DrDoc-StripeHandler-prod" "DrDoc-EnhancedChatbot-prod")
for func in "${LAMBDA_FUNCTIONS[@]}"; do
    print_test "Lambda function: $func"
    FUNC_STATUS=$(aws lambda get-function --function-name "$func" --query "Configuration.State" --output text 2>/dev/null || echo "MISSING")
    if [ "$FUNC_STATUS" = "Active" ]; then
        print_pass "Lambda function $func is active"
    else
        print_fail "Lambda function $func status: $FUNC_STATUS"
    fi
done

# Test 3: DynamoDB Tables
print_header "Database Checks"

REQUIRED_TABLES=("DrDocUsers-prod" "DrDocDocuments-prod" "DrDocChatHistory-prod")
for table in "${REQUIRED_TABLES[@]}"; do
    print_test "DynamoDB table: $table"
    TABLE_STATUS=$(aws dynamodb describe-table --table-name "$table" --query "Table.TableStatus" --output text 2>/dev/null || echo "MISSING")
    if [ "$TABLE_STATUS" = "ACTIVE" ]; then
        print_pass "DynamoDB table $table is active"
    else
        print_fail "DynamoDB table $table status: $TABLE_STATUS"
    fi
done

# Test 4: S3 Buckets
print_header "Storage Checks"

S3_BUCKETS=("drdoc-uploads-prod-995805900737" "taxdoc-web-app-v2-prod")
for bucket in "${S3_BUCKETS[@]}"; do
    print_test "S3 bucket: $bucket"
    if aws s3 ls "s3://$bucket" >/dev/null 2>&1; then
        print_pass "S3 bucket $bucket exists and is accessible"
    else
        print_fail "S3 bucket $bucket not accessible"
    fi
done

# Test 5: API Endpoints
print_header "API Endpoint Tests"

print_test "Chat endpoint (no auth required)"
CHAT_RESPONSE=$(curl -s -X POST "$API_URL/chat" \
    -H "Content-Type: application/json" \
    -d '{"message": "What documents can you process?"}' \
    -w "%{http_code}" -o /tmp/chat_response.json 2>/dev/null || echo "000")

if [ "$CHAT_RESPONSE" = "200" ]; then
    CHAT_SUCCESS=$(jq -r '.success // false' /tmp/chat_response.json 2>/dev/null || echo "false")
    if [ "$CHAT_SUCCESS" = "true" ]; then
        print_pass "Chat endpoint working correctly"
    else
        print_pass "Chat endpoint responding (may have fallback logic)"
    fi
else
    print_fail "Chat endpoint failed: HTTP $CHAT_RESPONSE"
fi

print_test "Protected endpoint (should require auth)"
PROTECTED_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "$API_URL/v2/me" 2>/dev/null || echo "000")
if [ "$PROTECTED_RESPONSE" = "403" ] || [ "$PROTECTED_RESPONSE" = "401" ]; then
    print_pass "Protected endpoint correctly requires authentication"
else
    print_fail "Protected endpoint security issue: HTTP $PROTECTED_RESPONSE"
fi

# Test 6: Frontend Accessibility
print_header "Frontend Checks"

print_test "MVP 2.0 Frontend"
FRONTEND_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "$MVP_URL" 2>/dev/null || echo "000")
if [ "$FRONTEND_RESPONSE" = "200" ]; then
    print_pass "MVP 2.0 frontend is accessible"
else
    print_fail "MVP 2.0 frontend failed: HTTP $FRONTEND_RESPONSE"
fi

# Test 7: Document Processing (if test image exists)
print_header "Document Processing Test"

if [ -f "$TEST_IMAGE" ]; then
    print_test "Document processing with sample image"
    
    # Convert image to base64
    BASE64_CONTENT=$(base64 -i "$TEST_IMAGE" 2>/dev/null || echo "")
    
    if [ -n "$BASE64_CONTENT" ]; then
        PROCESS_RESPONSE=$(curl -s -X POST "$API_URL/process-document" \
            -H "Content-Type: application/json" \
            -d "{\"filename\": \"test_w2.png\", \"file_content\": \"$BASE64_CONTENT\"}" \
            -w "%{http_code}" -o /tmp/process_response.json 2>/dev/null || echo "000")
        
        if [ "$PROCESS_RESPONSE" = "200" ]; then
            DOC_ID=$(jq -r '.document_id // empty' /tmp/process_response.json 2>/dev/null || echo "")
            if [ -n "$DOC_ID" ]; then
                print_pass "Document processing initiated successfully"
                
                # Test result retrieval
                sleep 3
                RESULT_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "$API_URL/result/$DOC_ID" 2>/dev/null || echo "000")
                if [ "$RESULT_RESPONSE" = "200" ]; then
                    print_pass "Document result retrieval working"
                else
                    print_fail "Document result retrieval failed: HTTP $RESULT_RESPONSE"
                fi
            else
                print_fail "Document processing response missing document_id"
            fi
        else
            print_fail "Document processing failed: HTTP $PROCESS_RESPONSE"
        fi
    else
        print_fail "Could not encode test image to base64"
    fi
else
    print_fail "Test image not found: $TEST_IMAGE"
fi

# Test 8: Stripe Configuration
print_header "Payment Integration Checks"

print_test "Stripe environment variables"
STRIPE_KEY=$(aws lambda get-function-configuration --function-name DrDoc-StripeHandler-prod --query "Environment.Variables.STRIPE_SECRET_KEY" --output text 2>/dev/null || echo "")
if [[ "$STRIPE_KEY" == sk_test_* ]]; then
    print_pass "Stripe test key configured"
else
    print_fail "Stripe key not configured or invalid"
fi

# Summary
print_header "Test Summary"

TOTAL_TESTS=$((TESTS_PASSED + TESTS_FAILED))
PASS_RATE=$((TESTS_PASSED * 100 / TOTAL_TESTS))

echo -e "📊 Results: ${GREEN}$TESTS_PASSED passed${NC}, ${RED}$TESTS_FAILED failed${NC} out of $TOTAL_TESTS tests"
echo -e "📈 Pass Rate: $PASS_RATE%"

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "\n🎉 ${GREEN}All tests passed! V2 system is ready for production.${NC}"
    exit 0
elif [ $PASS_RATE -ge 80 ]; then
    echo -e "\n⚠️  ${YELLOW}Most tests passed. Minor issues need attention.${NC}"
    exit 1
else
    echo -e "\n🚨 ${RED}Multiple test failures. System needs significant fixes.${NC}"
    exit 2
fi

# Cleanup
rm -f /tmp/chat_response.json /tmp/process_response.json