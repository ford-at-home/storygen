#!/bin/bash
# Production smoke tests for StoryGen deployment

set -euo pipefail

# Configuration
ENDPOINT=${1:-"https://storygen.example.com"}
TIMEOUT=30
MAX_RETRIES=3

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Test results
PASSED=0
FAILED=0

# Functions
log_test() {
    echo -e "\n🧪 Testing: $1"
}

log_pass() {
    echo -e "${GREEN}✓ PASSED:${NC} $1"
    ((PASSED++))
}

log_fail() {
    echo -e "${RED}✗ FAILED:${NC} $1"
    ((FAILED++))
}

retry_curl() {
    local url=$1
    local expected_status=$2
    local retry_count=0
    
    while [[ $retry_count -lt $MAX_RETRIES ]]; do
        local status=$(curl -s -o /dev/null -w "%{http_code}" --max-time $TIMEOUT "$url")
        
        if [[ $status -eq $expected_status ]]; then
            return 0
        fi
        
        ((retry_count++))
        if [[ $retry_count -lt $MAX_RETRIES ]]; then
            sleep 5
        fi
    done
    
    return 1
}

# Test 1: Health Check
log_test "Health Check Endpoint"
if retry_curl "$ENDPOINT/health" 200; then
    log_pass "Health check returned 200"
else
    log_fail "Health check failed"
fi

# Test 2: API Root
log_test "API Root Endpoint"
if retry_curl "$ENDPOINT/" 200; then
    log_pass "API root returned 200"
else
    log_fail "API root failed"
fi

# Test 3: Styles Endpoint
log_test "Styles Endpoint"
response=$(curl -s --max-time $TIMEOUT "$ENDPOINT/api/styles")
if [[ $(echo "$response" | jq -r '.styles | length' 2>/dev/null || echo "0") -gt 0 ]]; then
    log_pass "Styles endpoint returned valid data"
else
    log_fail "Styles endpoint returned invalid data"
fi

# Test 4: Story Generation
log_test "Story Generation Endpoint"
story_response=$(curl -s -X POST \
    --max-time $TIMEOUT \
    -H "Content-Type: application/json" \
    -d '{"core_idea": "Test story for smoke test", "style": "short_post"}' \
    "$ENDPOINT/api/generate-story")

if [[ $(echo "$story_response" | jq -r '.story' 2>/dev/null | wc -c) -gt 100 ]]; then
    log_pass "Story generation returned valid response"
else
    log_fail "Story generation failed or returned invalid data"
fi

# Test 5: Static Assets
log_test "Static Assets"
if retry_curl "$ENDPOINT/static/css/main.css" 200; then
    log_pass "Static assets are accessible"
else
    log_fail "Static assets are not accessible"
fi

# Test 6: Error Handling
log_test "404 Error Handling"
error_response=$(curl -s --max-time $TIMEOUT "$ENDPOINT/api/nonexistent")
if [[ $(echo "$error_response" | jq -r '.error' 2>/dev/null) != "null" ]]; then
    log_pass "404 error handling works correctly"
else
    log_fail "404 error handling failed"
fi

# Test 7: CORS Headers
log_test "CORS Headers"
cors_headers=$(curl -s -I --max-time $TIMEOUT \
    -H "Origin: https://example.com" \
    "$ENDPOINT/api/styles" | grep -i "access-control-allow-origin" || echo "")

if [[ -n "$cors_headers" ]]; then
    log_pass "CORS headers are present"
else
    log_fail "CORS headers are missing"
fi

# Test 8: Security Headers
log_test "Security Headers"
security_headers=$(curl -s -I --max-time $TIMEOUT "$ENDPOINT/")
required_headers=("X-Content-Type-Options" "X-Frame-Options" "X-XSS-Protection")
all_present=true

for header in "${required_headers[@]}"; do
    if ! echo "$security_headers" | grep -qi "$header"; then
        all_present=false
        log_fail "Missing security header: $header"
    fi
done

if $all_present; then
    log_pass "All security headers present"
fi

# Test 9: Response Times
log_test "Response Time Performance"
start_time=$(date +%s%N)
curl -s -o /dev/null "$ENDPOINT/health"
end_time=$(date +%s%N)
response_time=$(( (end_time - start_time) / 1000000 ))

if [[ $response_time -lt 1000 ]]; then
    log_pass "Health check response time: ${response_time}ms"
else
    log_fail "Health check response time too slow: ${response_time}ms"
fi

# Test 10: SSL Certificate
log_test "SSL Certificate"
cert_info=$(echo | openssl s_client -connect "${ENDPOINT#https://}:443" -servername "${ENDPOINT#https://}" 2>/dev/null | openssl x509 -noout -dates 2>/dev/null)

if [[ -n "$cert_info" ]]; then
    log_pass "SSL certificate is valid"
else
    log_fail "SSL certificate check failed"
fi

# Summary
echo -e "\n📊 Test Summary:"
echo -e "${GREEN}Passed:${NC} $PASSED"
echo -e "${RED}Failed:${NC} $FAILED"

if [[ $FAILED -eq 0 ]]; then
    echo -e "\n${GREEN}✅ All smoke tests passed!${NC}"
    exit 0
else
    echo -e "\n${RED}❌ Some tests failed!${NC}"
    exit 1
fi