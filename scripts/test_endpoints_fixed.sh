#!/bin/bash

# VibeJudge API - Complete Endpoint Test Script
set -e

BASE_URL="https://2nu0j4n648.execute-api.us-east-1.amazonaws.com/dev"
TEST_REPO="https://github.com/ma-za-kpe/vibejudge-ai"

echo "=========================================="
echo "VibeJudge API - Complete Endpoint Testing"
echo "=========================================="
echo ""

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

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
    else
        echo -e "${RED}✗ FAIL${NC} (HTTP $http_code)"
        FAILED=$((FAILED + 1))
    fi
    echo "$body" | jq '.' 2>/dev/null || echo "$body"
    echo ""
}

# 1. Health
test_endpoint "GET /health" "GET" "/health"

# 2. Create Organizer
TIMESTAMP=$(date +%s)
ORG_DATA="{\"name\":\"Test Org\",\"email\":\"test-$TIMESTAMP@example.com\",\"organization\":\"Test\"}"
ORG_RESPONSE=$(curl -s -X POST -H "Content-Type: application/json" -d "$ORG_DATA" "$BASE_URL/api/v1/organizers")
API_KEY=$(echo "$ORG_RESPONSE" | jq -r '.api_key')
echo "API Key: $API_KEY"
echo ""

test_endpoint "POST /api/v1/organizers" "POST" "/api/v1/organizers" "$ORG_DATA"

# 3-4. Organizer endpoints
test_endpoint "GET /api/v1/organizers/me" "GET" "/api/v1/organizers/me" "" "$API_KEY"
test_endpoint "PUT /api/v1/organizers/me" "PUT" "/api/v1/organizers/me" '{"name":"Updated"}' "$API_KEY"

# 5. Create Hackathon
HACK_DATA='{"name":"Test Hack","description":"Test","agents_enabled":["bug_hunter","performance","innovation"],"rubric":{"dimensions":[{"agent":"bug_hunter","weight":0.4,"criteria":["Quality"]},{"agent":"performance","weight":0.3,"criteria":["Speed"]},{"agent":"innovation","weight":0.3,"criteria":["Novel"]}]},"budget_limit_usd":10.0}'
HACK_RESPONSE=$(curl -s -X POST -H "Content-Type: application/json" -H "X-API-Key: $API_KEY" -d "$HACK_DATA" "$BASE_URL/api/v1/hackathons")
HACK_ID=$(echo "$HACK_RESPONSE" | jq -r '.hack_id')
echo "Hackathon ID: $HACK_ID"
echo ""

test_endpoint "POST /api/v1/hackathons" "POST" "/api/v1/hackathons" "$HACK_DATA" "$API_KEY"

# 6-8. Hackathon endpoints
test_endpoint "GET /api/v1/hackathons" "GET" "/api/v1/hackathons" "" "$API_KEY"
test_endpoint "GET /api/v1/hackathons/{hack_id}" "GET" "/api/v1/hackathons/$HACK_ID"
test_endpoint "PUT /api/v1/hackathons/{hack_id}" "PUT" "/api/v1/hackathons/$HACK_ID" '{"name":"Updated Hack"}'

# 9. Create Submission
SUB_DATA="{\"submissions\":[{\"team_name\":\"Test Team\",\"repo_url\":\"$TEST_REPO\",\"contact_email\":\"team@example.com\"}]}"
SUB_RESPONSE=$(curl -s -X POST -H "Content-Type: application/json" -d "$SUB_DATA" "$BASE_URL/api/v1/hackathons/$HACK_ID/submissions")
SUB_ID=$(echo "$SUB_RESPONSE" | jq -r '.submission_ids[0]')
echo "Submission ID: $SUB_ID"
echo ""

test_endpoint "POST /api/v1/hackathons/{hack_id}/submissions" "POST" "/api/v1/hackathons/$HACK_ID/submissions" "$SUB_DATA"

# 10-11. Submission endpoints
test_endpoint "GET /api/v1/hackathons/{hack_id}/submissions" "GET" "/api/v1/hackathons/$HACK_ID/submissions"
test_endpoint "GET /api/v1/submissions/{sub_id}" "GET" "/api/v1/submissions/$SUB_ID"

# 12. Estimate Cost
test_endpoint "POST /api/v1/hackathons/{hack_id}/estimate" "POST" "/api/v1/hackathons/$HACK_ID/estimate" '{}' "$API_KEY"

# 13. Trigger Analysis
ANALYZE_DATA="{\"submission_ids\":[\"$SUB_ID\"]}"
ANALYZE_RESPONSE=$(curl -s -X POST -H "Content-Type: application/json" -H "X-API-Key: $API_KEY" -d "$ANALYZE_DATA" "$BASE_URL/api/v1/hackathons/$HACK_ID/analyze")
JOB_ID=$(echo "$ANALYZE_RESPONSE" | jq -r '.job_id')
echo "Job ID: $JOB_ID"
echo ""

test_endpoint "POST /api/v1/hackathons/{hack_id}/analyze" "POST" "/api/v1/hackathons/$HACK_ID/analyze" "$ANALYZE_DATA" "$API_KEY"

# 14-15. Job endpoints
test_endpoint "GET /api/v1/hackathons/{hack_id}/jobs" "GET" "/api/v1/hackathons/$HACK_ID/jobs" "" "$API_KEY"
test_endpoint "GET /api/v1/hackathons/{hack_id}/jobs/{job_id}" "GET" "/api/v1/hackathons/$HACK_ID/jobs/$JOB_ID" "" "$API_KEY"

# 16-18. Scoring endpoints
test_endpoint "GET /api/v1/submissions/{sub_id}/scorecard" "GET" "/api/v1/submissions/$SUB_ID/scorecard"
test_endpoint "GET /api/v1/hackathons/{hack_id}/submissions/{sub_id}/evidence" "GET" "/api/v1/hackathons/$HACK_ID/submissions/$SUB_ID/evidence"
test_endpoint "GET /api/v1/hackathons/{hack_id}/leaderboard" "GET" "/api/v1/hackathons/$HACK_ID/leaderboard"

# 19-20. Cost endpoints
test_endpoint "GET /api/v1/hackathons/{hack_id}/costs" "GET" "/api/v1/hackathons/$HACK_ID/costs" "" "$API_KEY"
test_endpoint "GET /api/v1/submissions/{sub_id}/costs" "GET" "/api/v1/submissions/$SUB_ID/costs" "" "$API_KEY"

echo "=========================================="
echo "Test Summary"
echo "=========================================="
echo -e "${GREEN}Passed: $PASSED${NC}"
echo -e "${RED}Failed: $FAILED${NC}"
echo "Total: $((PASSED + FAILED))"
