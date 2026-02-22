#!/bin/bash

# VibeJudge API - Complete Endpoint Test Script
# Tests all 20 endpoints against production

set -e

BASE_URL="https://2nu0j4n648.execute-api.us-east-1.amazonaws.com/dev"
TEST_REPO="https://github.com/ma-za-kpe/vibejudge-ai"

echo "=========================================="
echo "VibeJudge API - Complete Endpoint Testing"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

PASSED=0
FAILED=0

test_endpoint() {
    local name="$1"
    local method="$2"
    local endpoint="$3"
    local data="$4"
    local api_key="$5"

    echo -n "Testing: $name ... "

    if [ "$method" = "GET" ]; then
        if [ -n "$api_key" ]; then
            response=$(curl -s -w "\n%{http_code}" -H "X-API-Key: $api_key" "$BASE_URL$endpoint")
        else
            response=$(curl -s -w "\n%{http_code}" "$BASE_URL$endpoint")
        fi
    else
        if [ -n "$api_key" ]; then
            response=$(curl -s -w "\n%{http_code}" -X "$method" -H "Content-Type: application/json" -H "X-API-Key: $api_key" -d "$data" "$BASE_URL$endpoint")
        else
            response=$(curl -s -w "\n%{http_code}" -X "$method" -H "Content-Type: application/json" -d "$data" "$BASE_URL$endpoint")
        fi
    fi

    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')

    if [ "$http_code" -ge 200 ] && [ "$http_code" -lt 300 ]; then
        echo -e "${GREEN}✓ PASS${NC} (HTTP $http_code)"
        PASSED=$((PASSED + 1))
        echo "$body" | jq '.' 2>/dev/null || echo "$body"
    else
        echo -e "${RED}✗ FAIL${NC} (HTTP $http_code)"
        FAILED=$((FAILED + 1))
        echo "$body" | jq '.' 2>/dev/null || echo "$body"
    fi
    echo ""
}

# 1. Health Check
echo "=== Health Check ==="
test_endpoint "GET /health" "GET" "/health"

# 2. Create Organizer
echo "=== Organizer Management ==="
TIMESTAMP=$(date +%s)
ORG_DATA="{
  \"name\": \"Test Organizer\",
  \"email\": \"test-$TIMESTAMP@example.com\",
  \"organization\": \"Test Org\"
}"
ORG_RESPONSE=$(curl -s -X POST -H "Content-Type: application/json" -d "$ORG_DATA" "$BASE_URL/api/v1/organizers")
API_KEY=$(echo "$ORG_RESPONSE" | jq -r '.api_key')
ORG_ID=$(echo "$ORG_RESPONSE" | jq -r '.org_id')

echo "Created Organizer: $ORG_ID"
echo "API Key: $API_KEY"
echo ""

test_endpoint "POST /api/v1/organizers" "POST" "/api/v1/organizers" "$ORG_DATA"

# 3. Get Current Organizer
test_endpoint "GET /api/v1/organizers/me" "GET" "/api/v1/organizers/me" "" "-H 'X-API-Key: $API_KEY'"

# 4. Update Organizer
UPDATE_ORG_DATA='{
  "name": "Updated Organizer",
  "organization": "Updated Org"
}'
test_endpoint "PUT /api/v1/organizers/me" "PUT" "/api/v1/organizers/me" "$UPDATE_ORG_DATA" "-H 'X-API-Key: $API_KEY'"

# 5. Create Hackathon
echo "=== Hackathon Management ==="
HACK_DATA='{
  "name": "Test Hackathon",
  "description": "Testing all endpoints",
  "agents_enabled": ["bug_hunter", "performance", "innovation"],
  "rubric": {
    "dimensions": [
      {
        "agent": "bug_hunter",
        "weight": 0.4,
        "criteria": ["Code quality", "Security"]
      },
      {
        "agent": "performance",
        "weight": 0.3,
        "criteria": ["Architecture", "Scalability"]
      },
      {
        "agent": "innovation",
        "weight": 0.3,
        "criteria": ["Creativity", "Documentation"]
      }
    ]
  },
  "budget_limit_usd": 10.0
}'
HACK_RESPONSE=$(curl -s -X POST -H "Content-Type: application/json" -H "X-API-Key: $API_KEY" -d "$HACK_DATA" "$BASE_URL/api/v1/hackathons")
HACK_ID=$(echo "$HACK_RESPONSE" | jq -r '.hack_id')

echo "Created Hackathon: $HACK_ID"
echo ""

test_endpoint "POST /api/v1/hackathons" "POST" "/api/v1/hackathons" "$HACK_DATA" "-H 'X-API-Key: $API_KEY'"

# 6. List Hackathons
test_endpoint "GET /api/v1/hackathons" "GET" "/api/v1/hackathons" "" "-H 'X-API-Key: $API_KEY'"

# 7. Get Hackathon
test_endpoint "GET /api/v1/hackathons/{hack_id}" "GET" "/api/v1/hackathons/$HACK_ID"

# 8. Update Hackathon
UPDATE_HACK_DATA='{
  "name": "Updated Hackathon",
  "description": "Updated description"
}'
test_endpoint "PUT /api/v1/hackathons/{hack_id}" "PUT" "/api/v1/hackathons/$HACK_ID" "$UPDATE_HACK_DATA"

# 9. Create Submission
echo "=== Submission Management ==="
SUB_DATA="{
  \"submissions\": [
    {
      \"team_name\": \"Test Team\",
      \"repo_url\": \"$TEST_REPO\",
      \"contact_email\": \"team@example.com\"
    }
  ]
}"
SUB_RESPONSE=$(curl -s -X POST -H "Content-Type: application/json" -d "$SUB_DATA" "$BASE_URL/api/v1/hackathons/$HACK_ID/submissions")
SUB_ID=$(echo "$SUB_RESPONSE" | jq -r '.submission_ids[0]')

echo "Created Submission: $SUB_ID"
echo ""

test_endpoint "POST /api/v1/hackathons/{hack_id}/submissions" "POST" "/api/v1/hackathons/$HACK_ID/submissions" "$SUB_DATA"

# 10. List Submissions
test_endpoint "GET /api/v1/hackathons/{hack_id}/submissions" "GET" "/api/v1/hackathons/$HACK_ID/submissions"

# 11. Get Submission
test_endpoint "GET /api/v1/submissions/{sub_id}" "GET" "/api/v1/submissions/$SUB_ID"

# 12. Estimate Cost
echo "=== Cost Estimation ==="
test_endpoint "POST /api/v1/hackathons/{hack_id}/estimate" "POST" "/api/v1/hackathons/$HACK_ID/estimate" "{}" "-H 'X-API-Key: $API_KEY'"

# 13. Trigger Analysis
echo "=== Analysis ==="
ANALYZE_DATA="{
  \"submission_ids\": [\"$SUB_ID\"]
}"
ANALYZE_RESPONSE=$(curl -s -X POST -H "Content-Type: application/json" -H "X-API-Key: $API_KEY" -d "$ANALYZE_DATA" "$BASE_URL/api/v1/hackathons/$HACK_ID/analyze")
JOB_ID=$(echo "$ANALYZE_RESPONSE" | jq -r '.job_id')

echo "Created Analysis Job: $JOB_ID"
echo ""

test_endpoint "POST /api/v1/hackathons/{hack_id}/analyze" "POST" "/api/v1/hackathons/$HACK_ID/analyze" "$ANALYZE_DATA" "-H 'X-API-Key: $API_KEY'"

# 14. List Jobs
test_endpoint "GET /api/v1/hackathons/{hack_id}/jobs" "GET" "/api/v1/hackathons/$HACK_ID/jobs" "" "-H 'X-API-Key: $API_KEY'"

# 15. Get Job Status
test_endpoint "GET /api/v1/hackathons/{hack_id}/jobs/{job_id}" "GET" "/api/v1/hackathons/$HACK_ID/jobs/$JOB_ID" "" "-H 'X-API-Key: $API_KEY'"

# 16. Get Scorecard (will be empty until analysis completes)
echo "=== Scoring ==="
test_endpoint "GET /api/v1/submissions/{sub_id}/scorecard" "GET" "/api/v1/submissions/$SUB_ID/scorecard"

# 17. Get Evidence (will be empty until analysis completes)
test_endpoint "GET /api/v1/hackathons/{hack_id}/submissions/{sub_id}/evidence" "GET" "/api/v1/hackathons/$HACK_ID/submissions/$SUB_ID/evidence"

# 18. Get Leaderboard
test_endpoint "GET /api/v1/hackathons/{hack_id}/leaderboard" "GET" "/api/v1/hackathons/$HACK_ID/leaderboard"

# 19. Get Hackathon Costs
echo "=== Cost Tracking ==="
test_endpoint "GET /api/v1/hackathons/{hack_id}/costs" "GET" "/api/v1/hackathons/$HACK_ID/costs" "" "-H 'X-API-Key: $API_KEY'"

# 20. Get Submission Costs
test_endpoint "GET /api/v1/submissions/{sub_id}/costs" "GET" "/api/v1/submissions/$SUB_ID/costs" "" "-H 'X-API-Key: $API_KEY'"

# Summary
echo "=========================================="
echo "Test Summary"
echo "=========================================="
echo -e "${GREEN}Passed: $PASSED${NC}"
echo -e "${RED}Failed: $FAILED${NC}"
echo "Total: $((PASSED + FAILED))"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}✗ Some tests failed${NC}"
    exit 1
fi
