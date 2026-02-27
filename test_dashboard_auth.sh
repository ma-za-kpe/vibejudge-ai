#!/bin/bash

# Test Dashboard Authentication Fix
# This script verifies that the dashboard correctly validates API keys

API_BASE_URL="https://2nu0j4n648.execute-api.us-east-1.amazonaws.com/dev/api/v1"
VALID_KEY="419a05e9dd8b005e567c02c6ad0333bc8bba8c50d3bdc06e21d98380301e53e6"
INVALID_KEY="TOTALLY_INVALID_KEY_123"

echo "=========================================="
echo "Dashboard Authentication Test"
echo "=========================================="
echo ""

echo "Test 1: Backend rejects invalid API key"
echo "----------------------------------------"
response=$(curl -s -H "X-API-Key: $INVALID_KEY" "$API_BASE_URL/hackathons")
if echo "$response" | grep -q "Invalid API key"; then
    echo "✅ PASS: Invalid key rejected"
else
    echo "❌ FAIL: Invalid key not rejected"
    echo "Response: $response"
fi
echo ""

echo "Test 2: Backend accepts valid API key"
echo "----------------------------------------"
response=$(curl -s -H "X-API-Key: $VALID_KEY" "$API_BASE_URL/hackathons")
if echo "$response" | grep -q "hackathons"; then
    echo "✅ PASS: Valid key accepted"
else
    echo "❌ FAIL: Valid key not accepted"
    echo "Response: $response"
fi
echo ""

echo "Test 3: Dashboard is accessible"
echo "----------------------------------------"
response=$(curl -s -o /dev/null -w "%{http_code}" http://vibejudge-alb-prod-1135403146.us-east-1.elb.amazonaws.com)
if [ "$response" = "200" ]; then
    echo "✅ PASS: Dashboard returns 200"
else
    echo "❌ FAIL: Dashboard returned $response"
fi
echo ""

echo "=========================================="
echo "Manual Testing Instructions"
echo "=========================================="
echo ""
echo "1. Open: http://vibejudge-alb-prod-1135403146.us-east-1.elb.amazonaws.com"
echo ""
echo "2. Test INVALID key (should FAIL):"
echo "   API Key: $INVALID_KEY"
echo "   Base URL: $API_BASE_URL"
echo "   Expected: 'Invalid API key' error"
echo ""
echo "3. Test VALID key (should SUCCEED):"
echo "   API Key: $VALID_KEY"
echo "   Base URL: $API_BASE_URL"
echo "   Expected: Login successful, dashboard loads"
echo ""
echo "=========================================="
