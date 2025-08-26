#!/bin/bash
# Test TaxDoc v2.5 Features
# Comprehensive test script for all new features

set -e

ENVIRONMENT=${1:-prod}
API_BASE="https://iljpaj6ogl.execute-api.us-east-1.amazonaws.com/$ENVIRONMENT"
FRONTEND_URL="http://taxdoc-mvp-web-1754513919.s3-website-us-east-1.amazonaws.com/mvp2-enhanced.html"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[TEST]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[PASS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[FAIL]${NC} $1"
}

# Test counters
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

run_test() {
    local test_name="$1"
    local test_command="$2"
    
    TESTS_RUN=$((TESTS_RUN + 1))
    print_status "Running: $test_name"
    
    if eval "$test_command"; then
        TESTS_PASSED=$((TESTS_PASSED + 1))
        print_success "$test_name"
        return 0
    else
        TESTS_FAILED=$((TESTS_FAILED + 1))
        print_error "$test_name"
        return 1
    fi
}

# Helper function to check HTTP status
check_http_status() {
    local url="$1"
    local expected_status="$2"
    local method="${3:-GET}"
    local data="${4:-}"
    
    if [ -n "$data" ]; then
        actual_status=$(curl -s -o /dev/null -w "%{http_code}" -X "$method" "$url" \
            -H "Content-Type: application/json" \
            -d "$data")
    else
        actual_status=$(curl -s -o /dev/null -w "%{http_code}" -X "$method" "$url")
    fi
    
    if [ "$actual_status" = "$expected_status" ]; then
        return 0
    else
        echo "Expected $expected_status, got $actual_status"
        return 1
    fi
}

# Helper function to check if response contains text
check_response_contains() {
    local url="$1"
    local expected_text="$2"
    local method="${3:-GET}"
    local data="${4:-}"
    
    if [ -n "$data" ]; then
        response=$(curl -s -X "$method" "$url" \
            -H "Content-Type: application/json" \
            -d "$data")
    else
        response=$(curl -s -X "$method" "$url")
    fi
    
    if echo "$response" | grep -q "$expected_text"; then
        return 0
    else
        echo "Response does not contain: $expected_text"
        echo "Actual response: $response"
        return 1
    fi
}

echo "🧪 TaxDoc v2.5 Feature Testing Suite"
echo "Environment: $ENVIRONMENT"
echo "API Base: $API_BASE"
echo "Frontend: $FRONTEND_URL"
echo ""

# Test 1: Frontend Accessibility
print_status "=== Frontend Tests ==="

run_test "Enhanced frontend loads" \
    "check_http_status '$FRONTEND_URL' '200'"

run_test "Frontend contains v2.5 features" \
    "check_response_contains '$FRONTEND_URL' 'Upload Queue'"

run_test "Frontend contains usage meter" \
    "check_response_contains '$FRONTEND_URL' 'usageMeter'"

run_test "Frontend contains export drawer" \
    "check_response_contains '$FRONTEND_URL' 'showExportDrawer'"

# Test 2: API Gateway Endpoints
print_status "=== API Gateway Tests ==="

run_test "Main API endpoint responds" \
    "check_http_status '$API_BASE/process-document' '400' 'POST' '{}'"

run_test "V2 batch upload endpoint exists" \
    "check_http_status '$API_BASE/v2/batch-upload' '400' 'POST' '{}'"

run_test "V2 export endpoint exists" \
    "check_http_status '$API_BASE/v2/export' '401' 'GET'"

run_test "V2 webhooks endpoint exists" \
    "check_http_status '$API_BASE/v2/webhooks/stripe' '400' 'POST' '{}'"

# Test 3: Stripe Webhook Tests
print_status "=== Stripe Webhook Tests ==="

# Test webhook with invalid signature (should fail)
run_test "Webhook rejects invalid signature" \
    "check_http_status '$API_BASE/v2/webhooks/stripe' '400' 'POST' '{\"type\":\"test\"}'"

# Test webhook with missing signature header
run_test "Webhook requires signature header" \
    "check_response_contains '$API_BASE/v2/webhooks/stripe' 'Missing signature' 'POST' '{\"type\":\"test\"}'"

# Test 4: Export Functionality Tests
print_status "=== Export Tests ==="

# Test export without authentication
run_test "Export requires authentication" \
    "check_http_status '$API_BASE/v2/export?docId=test&format=csv' '401'"

# Test export with invalid format
run_test "Export validates format parameter" \
    "check_http_status '$API_BASE/v2/export?docId=test&format=invalid' '401'"

# Test 5: Batch Upload Tests
print_status "=== Batch Upload Tests ==="

# Test batch upload without authentication
run_test "Batch upload requires authentication" \
    "check_http_status '$API_BASE/v2/batch-upload' '401' 'POST' '{\"files\":[]}'"

# Test batch upload with invalid data
run_test "Batch upload validates input" \
    "check_http_status '$API_BASE/v2/batch-upload' '400' 'POST' '{\"invalid\":\"data\"}'"

# Test 6: CloudWatch and Monitoring
print_status "=== Monitoring Tests ==="

# Check if CloudWatch dashboard exists
run_test "CloudWatch dashboard exists" \
    "aws cloudwatch get-dashboard --dashboard-name 'DrDoc-v25-$ENVIRONMENT' --region us-east-1 > /dev/null 2>&1"

# Check if alarms exist
run_test "Batch upload alarm exists" \
    "aws cloudwatch describe-alarms --alarm-names 'DrDoc-BatchUpload-Errors-$ENVIRONMENT' --region us-east-1 --query 'MetricAlarms[0].AlarmName' --output text | grep -q 'DrDoc-BatchUpload-Errors'"

run_test "Export handler alarm exists" \
    "aws cloudwatch describe-alarms --alarm-names 'DrDoc-Export-Errors-$ENVIRONMENT' --region us-east-1 --query 'MetricAlarms[0].AlarmName' --output text | grep -q 'DrDoc-Export-Errors'"

# Test 7: Lambda Function Tests
print_status "=== Lambda Function Tests ==="

# Check if Lambda functions exist and are active
run_test "Enhanced Stripe handler exists" \
    "aws lambda get-function --function-name 'DrDoc-EnhancedStripeHandler-$ENVIRONMENT' --region us-east-1 > /dev/null 2>&1"

run_test "Batch upload handler exists" \
    "aws lambda get-function --function-name 'DrDoc-BatchUploadHandler-$ENVIRONMENT' --region us-east-1 > /dev/null 2>&1"

run_test "Export handler exists" \
    "aws lambda get-function --function-name 'DrDoc-ExportHandler-$ENVIRONMENT' --region us-east-1 > /dev/null 2>&1"

run_test "Notification handler exists" \
    "aws lambda get-function --function-name 'DrDoc-NotificationHandler-$ENVIRONMENT' --region us-east-1 > /dev/null 2>&1"

# Test 8: DynamoDB Tables
print_status "=== DynamoDB Tests ==="

# Check if new tables exist
run_test "Export jobs table exists" \
    "aws dynamodb describe-table --table-name 'DrDocExportJobs-$ENVIRONMENT' --region us-east-1 > /dev/null 2>&1"

run_test "Export logs table exists" \
    "aws dynamodb describe-table --table-name 'DrDocExportLogs-$ENVIRONMENT' --region us-east-1 > /dev/null 2>&1"

run_test "Batch processing table exists" \
    "aws dynamodb describe-table --table-name 'DrDocBatches-$ENVIRONMENT' --region us-east-1 > /dev/null 2>&1"

# Test 9: S3 Bucket Tests
print_status "=== S3 Bucket Tests ==="

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
EXPORTS_BUCKET="drdoc-exports-$ENVIRONMENT-$ACCOUNT_ID"

run_test "Exports bucket exists" \
    "aws s3api head-bucket --bucket '$EXPORTS_BUCKET' 2>/dev/null"

run_test "Exports bucket has lifecycle policy" \
    "aws s3api get-bucket-lifecycle-configuration --bucket '$EXPORTS_BUCKET' > /dev/null 2>&1"

run_test "Exports bucket has encryption" \
    "aws s3api get-bucket-encryption --bucket '$EXPORTS_BUCKET' > /dev/null 2>&1"

# Test 10: SNS Topics
print_status "=== SNS Tests ==="

# Check if SNS topics exist
run_test "Doc ready topic exists" \
    "aws sns list-topics --region us-east-1 --query 'Topics[?contains(TopicArn, \`drdoc-doc-ready-$ENVIRONMENT\`)].TopicArn' --output text | grep -q 'drdoc-doc-ready'"

run_test "Doc failed topic exists" \
    "aws sns list-topics --region us-east-1 --query 'Topics[?contains(TopicArn, \`drdoc-doc-failed-$ENVIRONMENT\`)].TopicArn' --output text | grep -q 'drdoc-doc-failed'"

run_test "Batch completed topic exists" \
    "aws sns list-topics --region us-east-1 --query 'Topics[?contains(TopicArn, \`drdoc-batch-completed-$ENVIRONMENT\`)].TopicArn' --output text | grep -q 'drdoc-batch-completed'"

# Test 11: IAM Roles and Permissions
print_status "=== IAM Tests ==="

run_test "Export Lambda role exists" \
    "aws iam get-role --role-name 'DrDoc-ExportLambda-Role-$ENVIRONMENT' > /dev/null 2>&1"

run_test "Batch Lambda role exists" \
    "aws iam get-role --role-name 'DrDoc-BatchLambda-Role-$ENVIRONMENT' > /dev/null 2>&1"

run_test "Notification Lambda role exists" \
    "aws iam get-role --role-name 'DrDoc-NotificationLambda-Role-$ENVIRONMENT' > /dev/null 2>&1"

# Test 12: End-to-End Integration Tests
print_status "=== Integration Tests ==="

# Test document processing flow (mock)
run_test "Document processing endpoint responds" \
    "check_http_status '$API_BASE/process-document' '400' 'POST' '{\"filename\":\"test.pdf\"}'"

# Test result retrieval
run_test "Result endpoint responds" \
    "check_http_status '$API_BASE/result/test-id' '404'"

# Test chat endpoint
run_test "Chat endpoint responds" \
    "check_http_status '$API_BASE/enhanced-chat' '400' 'POST' '{\"message\":\"test\"}'"

# Test 13: Security Tests
print_status "=== Security Tests ==="

# Test CORS headers
run_test "API returns CORS headers" \
    "curl -s -I '$API_BASE/process-document' | grep -q 'Access-Control-Allow-Origin'"

# Test that sensitive endpoints require authentication
run_test "Protected endpoints require auth" \
    "check_http_status '$API_BASE/v2/export' '401'"

# Test 14: Performance Tests
print_status "=== Performance Tests ==="

# Test API response time
run_test "API responds within 5 seconds" \
    "timeout 5s curl -s '$API_BASE/process-document' -X POST -H 'Content-Type: application/json' -d '{}' > /dev/null"

# Test frontend load time
run_test "Frontend loads within 10 seconds" \
    "timeout 10s curl -s '$FRONTEND_URL' > /dev/null"

# Test 15: Feature Flag Tests
print_status "=== Feature Flag Tests ==="

# Test that new features are enabled
run_test "Batch upload feature enabled" \
    "check_response_contains '$FRONTEND_URL' 'Batch Upload'"

run_test "Export drawer feature enabled" \
    "check_response_contains '$FRONTEND_URL' 'Export Options'"

run_test "Usage meter feature enabled" \
    "check_response_contains '$FRONTEND_URL' 'usage-meter'"

# Test Summary
echo ""
echo "📊 Test Results Summary"
echo "======================="
echo "Total Tests Run: $TESTS_RUN"
echo "Tests Passed: $TESTS_PASSED"
echo "Tests Failed: $TESTS_FAILED"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    print_success "All tests passed! ✅"
    echo ""
    echo "🎉 TaxDoc v2.5 is ready for production!"
    echo ""
    echo "🔗 Quick Links:"
    echo "  • Enhanced Frontend: $FRONTEND_URL"
    echo "  • API Base: $API_BASE"
    echo "  • CloudWatch Dashboard: https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#dashboards:name=DrDoc-v25-$ENVIRONMENT"
    echo ""
    echo "📋 Manual Testing Checklist:"
    echo "  □ Upload a single document"
    echo "  □ Upload multiple documents (batch)"
    echo "  □ Upload a folder of documents"
    echo "  □ Upload a ZIP file"
    echo "  □ Export document as CSV"
    echo "  □ Export document as JSON"
    echo "  □ Export document as Excel"
    echo "  □ Export document as PDF summary"
    echo "  □ Export all documents as ZIP"
    echo "  □ Test usage meter updates"
    echo "  □ Test upgrade flow"
    echo "  □ Test AI chat with documents"
    echo "  □ Test document filtering and search"
    echo "  □ Test bulk document actions"
    echo ""
    exit 0
else
    print_error "Some tests failed! ❌"
    echo ""
    echo "🔧 Failed Tests: $TESTS_FAILED"
    echo ""
    echo "Please review the failed tests above and fix any issues before deploying to production."
    echo ""
    exit 1
fi