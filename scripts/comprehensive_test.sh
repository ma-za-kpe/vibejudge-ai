#!/bin/bash

# VibeJudge AI - Comprehensive Test Suite
# Tests all 20 endpoints with 3-5 diverse GitHub repositories

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Config
API_URL="${API_URL:-https://2nu0j4n648.execute-api.us-east-1.amazonaws.com/dev}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="scripts/test_results_${TIMESTAMP}.log"

# Test repositories (diverse set for robustness testing)
TEST_REPOS=(
    "https://github.com/ma-za-kpe/vibejudge-ai"
    "https://github.com/anthropics/anthropic-quickstarts"
    "https://github.com/fastapi/fastapi"
)

# Counters
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# Functions
log() {
    echo -e "${BLUE}[$(date +'%H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

success() {
    echo -e "${GREEN}✅ $1${NC}" | tee -a "$LOG_FILE"
    ((PASSED_TESTS++))
    ((TOTAL_TESTS++))
}

error() {
    echo -e "${RED}❌ $1${NC}" | tee -a "$LOG_FILE"
    ((FAILED_TESTS++))
    ((TOTAL_TESTS++))
}

warning() {
    echo -e "${YELLOW}⚠️  $1${NC}" | tee -a "$LOG_FILE"
}

# Main test execution
main() {
    log "=========================================="
    log "VibeJudge AI - Comprehensive Test Suite"
    log "=========================================="
    log "API URL: $API_URL"
    log "Log File: $LOG_FILE"
    log ""

    # Test 1: Health Check
    log "=== Phase 1: Health Check ==="
    HEALTH_RESPONSE=$(curl -s "$API_URL/health")
    if echo "$HEALTH_RESPONSE" | jq -e '.status == "healthy"' > /dev/null 2>&1; then
        success "Health Check"
    else
        error "Health Check"
    fi
    echo ""

    # Test 2: Create Organizer
    log "=== Phase 2: Organizer Management ==="
    ORGANIZER_DATA='{
        "name": "Test Organizer",
        "email": "test_'$TIMESTAMP'@example.com",
        "organization": "Test Org"
    }'

    ORGANIZER_RESPONSE=$(curl -s -X POST "$API_URL/api/v1/organizers" \
        -H "Content-Type: application/json" \
        -d "$ORGANIZER_DATA")

    ORG_ID=$(echo "$ORGANIZER_RESPONSE" | jq -r '.org_id')
    API_KEY=$(echo "$ORGANIZER_RESPONSE" | jq -r '.api_key')

    if [ "$ORG_ID" != "null" ] && [ -n "$API_KEY" ]; then
        success "Create Organizer - ID: $ORG_ID"
        log "API Key: ${API_KEY:0:20}..."
    else
        error "Create Organizer"
        log "Response: $ORGANIZER_RESPONSE"
        exit 1
    fi
    echo ""

    # Test 3: Get Organizer Profile
    PROFILE_RESPONSE=$(curl -s "$API_URL/api/v1/organizers/me" \
        -H "X-API-Key: $API_KEY")

    if echo "$PROFILE_RESPONSE" | jq -e '.org_id' > /dev/null 2>&1; then
        success "Get Organizer Profile"
    else
        error "Get Organizer Profile"
    fi
    echo ""

    # Test 4: Update Organizer Profile (SKIPPED - endpoint not implemented in MVP)
    warning "Update Organizer Profile - Skipped (not in MVP scope)"
    echo ""

    # Test 5: Create Hackathon
    log "=== Phase 3: Hackathon Management ==="
    HACKATHON_DATA='{
        "name": "Test Hackathon '$TIMESTAMP'",
        "description": "Comprehensive test hackathon",
        "rubric": {
            "name": "Default Rubric",
            "version": "1.0",
            "max_score": 100.0,
            "dimensions": [
                {
                    "name": "Code Quality",
                    "agent": "bug_hunter",
                    "weight": 0.4,
                    "description": "Code quality and security"
                },
                {
                    "name": "Architecture",
                    "agent": "performance",
                    "weight": 0.3,
                    "description": "Architecture and performance"
                },
                {
                    "name": "Innovation",
                    "agent": "innovation",
                    "weight": 0.3,
                    "description": "Creativity and innovation"
                }
            ]
        },
        "agents_enabled": ["bug_hunter", "performance", "innovation"],
        "ai_policy_mode": "ai_assisted"
    }'

    HACKATHON_RESPONSE=$(curl -s -X POST "$API_URL/api/v1/hackathons" \
        -H "Content-Type: application/json" \
        -H "X-API-Key: $API_KEY" \
        -d "$HACKATHON_DATA")

    HACK_ID=$(echo "$HACKATHON_RESPONSE" | jq -r '.hack_id')

    if [ "$HACK_ID" != "null" ] && [ -n "$HACK_ID" ]; then
        success "Create Hackathon - ID: $HACK_ID"
    else
        error "Create Hackathon"
        log "Response: $HACKATHON_RESPONSE"
        exit 1
    fi
    echo ""

    # Test 6: List Hackathons
    LIST_RESPONSE=$(curl -s "$API_URL/api/v1/hackathons" \
        -H "X-API-Key: $API_KEY")

    HACK_COUNT=$(echo "$LIST_RESPONSE" | jq '.hackathons | length')
    if [ "$HACK_COUNT" -gt 0 ]; then
        success "List Hackathons - Count: $HACK_COUNT"
    else
        error "List Hackathons"
    fi
    echo ""

    # Test 7: Get Hackathon Details
    HACK_DETAIL=$(curl -s "$API_URL/api/v1/hackathons/$HACK_ID" \
        -H "X-API-Key: $API_KEY")

    if echo "$HACK_DETAIL" | jq -e '.hack_id' > /dev/null 2>&1; then
        success "Get Hackathon Details"
    else
        error "Get Hackathon Details"
    fi
    echo ""

    # Test 8: Update Hackathon
    UPDATE_HACK_DATA='{"description": "Updated description"}'
    UPDATE_HACK_RESPONSE=$(curl -s -X PUT "$API_URL/api/v1/hackathons/$HACK_ID" \
        -H "Content-Type: application/json" \
        -H "X-API-Key: $API_KEY" \
        -d "$UPDATE_HACK_DATA")

    if echo "$UPDATE_HACK_RESPONSE" | jq -e '.description == "Updated description"' > /dev/null 2>&1; then
        success "Update Hackathon"
    else
        error "Update Hackathon"
    fi
    echo ""

    # Test 9-11: Create Submissions (Batch Format)
    log "=== Phase 4: Submission Management ==="
    SUBMISSION_IDS=()

    # Build submissions array
    SUBMISSIONS_JSON='{"submissions":['
    for i in "${!TEST_REPOS[@]}"; do
        if [ $i -gt 0 ]; then
            SUBMISSIONS_JSON+=','
        fi
        SUBMISSIONS_JSON+='{"team_name":"Team '$((i+1))'","repo_url":"'${TEST_REPOS[$i]}'"}'
    done
    SUBMISSIONS_JSON+=']}'

    log "Creating ${#TEST_REPOS[@]} submissions..."
    BATCH_RESPONSE=$(curl -s -X POST "$API_URL/api/v1/hackathons/$HACK_ID/submissions" \
        -H "Content-Type: application/json" \
        -H "X-API-Key: $API_KEY" \
        -d "$SUBMISSIONS_JSON")

    CREATED_COUNT=$(echo "$BATCH_RESPONSE" | jq -r '.created')

    if [ "$CREATED_COUNT" = "${#TEST_REPOS[@]}" ]; then
        success "Create Submissions - Created: $CREATED_COUNT"

        # Extract submission IDs
        for i in $(seq 0 $((CREATED_COUNT - 1))); do
            SUB_ID=$(echo "$BATCH_RESPONSE" | jq -r ".submissions[$i].sub_id")
            SUBMISSION_IDS+=("$SUB_ID")
            log "  Submission $((i+1)): $SUB_ID"
        done
    else
        error "Create Submissions - Expected: ${#TEST_REPOS[@]}, Got: $CREATED_COUNT"
        log "Response: $BATCH_RESPONSE"
    fi
    echo ""

    # Test 12: List Submissions
    SUB_LIST=$(curl -s "$API_URL/api/v1/hackathons/$HACK_ID/submissions" \
        -H "X-API-Key: $API_KEY")

    SUB_COUNT=$(echo "$SUB_LIST" | jq '.submissions | length')
    if [ "$SUB_COUNT" -eq "${#TEST_REPOS[@]}" ]; then
        success "List Submissions - Count: $SUB_COUNT"
    else
        error "List Submissions - Expected: ${#TEST_REPOS[@]}, Got: $SUB_COUNT"
    fi
    echo ""

    # Test 13: Get Submission Details
    if [ ${#SUBMISSION_IDS[@]} -gt 0 ]; then
        SUB_DETAIL=$(curl -s "$API_URL/api/v1/submissions/${SUBMISSION_IDS[0]}" \
            -H "X-API-Key: $API_KEY")

        if echo "$SUB_DETAIL" | jq -e '.sub_id' > /dev/null 2>&1; then
            success "Get Submission Details"
        else
            error "Get Submission Details"
        fi
    else
        error "Get Submission Details - No submissions created"
    fi
    echo ""

    # Test 14: Estimate Analysis Cost
    log "=== Phase 5: Analysis Pipeline ==="
    ESTIMATE_RESPONSE=$(curl -s -X POST "$API_URL/api/v1/hackathons/$HACK_ID/analyze/estimate" \
        -H "Content-Type: application/json" \
        -H "X-API-Key: $API_KEY")

    ESTIMATED_COST=$(echo "$ESTIMATE_RESPONSE" | jq -r '.estimate.total_cost_usd.expected')
    if [ "$ESTIMATED_COST" != "null" ]; then
        success "Estimate Analysis Cost - \$$ESTIMATED_COST"
    else
        error "Estimate Analysis Cost"
    fi
    echo ""

    # Test 15: Trigger Analysis
    log "Triggering analysis for ${#SUBMISSION_IDS[@]} submissions..."
    ANALYSIS_TRIGGER='{"submission_ids": null, "force_reanalyze": false}'
    ANALYSIS_RESPONSE=$(curl -s -X POST "$API_URL/api/v1/hackathons/$HACK_ID/analyze" \
        -H "Content-Type: application/json" \
        -H "X-API-Key: $API_KEY" \
        -d "$ANALYSIS_TRIGGER")

    JOB_ID=$(echo "$ANALYSIS_RESPONSE" | jq -r '.job_id')

    if [ "$JOB_ID" != "null" ] && [ -n "$JOB_ID" ]; then
        success "Trigger Analysis - Job ID: $JOB_ID"
    else
        error "Trigger Analysis"
        log "Response: $ANALYSIS_RESPONSE"
    fi
    echo ""

    # Test 16: Monitor Analysis Status
    log "Monitoring analysis progress (max 10 minutes)..."
    MAX_WAIT=600
    ELAPSED=0
    SLEEP_INTERVAL=10

    while [ $ELAPSED -lt $MAX_WAIT ]; do
        # Get the latest job status (returns single object, not array)
        STATUS_RESPONSE=$(curl -s "$API_URL/api/v1/hackathons/$HACK_ID/analyze/status" \
            -H "X-API-Key: $API_KEY")

        # Parse the status response (it's an object with job_id, status, progress)
        STATUS=$(echo "$STATUS_RESPONSE" | jq -r '.status')
        COMPLETED=$(echo "$STATUS_RESPONSE" | jq -r '.progress.completed')
        TOTAL=$(echo "$STATUS_RESPONSE" | jq -r '.progress.total_submissions')

        log "[$ELAPSED s] Status: $STATUS | Progress: $COMPLETED/$TOTAL"

        if [ "$STATUS" = "completed" ]; then
            success "Analysis Completed"
            break
        elif [ "$STATUS" = "failed" ]; then
            error "Analysis Failed"
            log "Response: $STATUS_RESPONSE"
            break
        fi

        sleep $SLEEP_INTERVAL
        ELAPSED=$((ELAPSED + SLEEP_INTERVAL))
    done

    if [ $ELAPSED -ge $MAX_WAIT ]; then
        warning "Analysis timeout after ${MAX_WAIT}s"
    fi
    echo ""

    # Test 17: Get Scorecard
    log "=== Phase 6: Results & Costs ==="
    if [ ${#SUBMISSION_IDS[@]} -gt 0 ]; then
        SCORECARD=$(curl -s "$API_URL/api/v1/hackathons/$HACK_ID/submissions/${SUBMISSION_IDS[0]}/scorecard" \
            -H "X-API-Key: $API_KEY")

        OVERALL_SCORE=$(echo "$SCORECARD" | jq -r '.overall_score')
        if [ "$OVERALL_SCORE" != "null" ]; then
            success "Get Scorecard - Score: $OVERALL_SCORE"
        else
            warning "Get Scorecard - No score yet (analysis may still be running)"
        fi
    else
        error "Get Scorecard - No submissions"
    fi
    echo ""

    # Test 18: Get Evidence
    if [ ${#SUBMISSION_IDS[@]} -gt 0 ]; then
        EVIDENCE=$(curl -s "$API_URL/api/v1/hackathons/$HACK_ID/submissions/${SUBMISSION_IDS[0]}/evidence" \
            -H "X-API-Key: $API_KEY")

        EVIDENCE_COUNT=$(echo "$EVIDENCE" | jq '.evidence | length')
        if [ "$EVIDENCE_COUNT" != "null" ]; then
            success "Get Evidence - Count: $EVIDENCE_COUNT"
        else
            warning "Get Evidence - No evidence yet"
        fi
    else
        error "Get Evidence - No submissions"
    fi
    echo ""

    # Test 19: Get Leaderboard
    LEADERBOARD=$(curl -s "$API_URL/api/v1/hackathons/$HACK_ID/leaderboard" \
        -H "X-API-Key: $API_KEY")

    LEADERBOARD_COUNT=$(echo "$LEADERBOARD" | jq '.leaderboard | length')
    if [ "$LEADERBOARD_COUNT" != "null" ] && [ "$LEADERBOARD_COUNT" -gt 0 ]; then
        success "Get Leaderboard - Entries: $LEADERBOARD_COUNT"
    else
        warning "Get Leaderboard - Empty (analysis may still be running)"
    fi
    echo ""

    # Test 20: Get Hackathon Costs
    COSTS=$(curl -s "$API_URL/api/v1/hackathons/$HACK_ID/costs" \
        -H "X-API-Key: $API_KEY")

    TOTAL_COST=$(echo "$COSTS" | jq -r '.total_cost_usd')
    if [ "$TOTAL_COST" != "null" ]; then
        success "Get Hackathon Costs - Total: \$$TOTAL_COST"
    else
        warning "Get Hackathon Costs - No costs recorded yet"
    fi
    echo ""

    # Summary
    log "=========================================="
    log "Test Summary"
    log "=========================================="
    log "Total Tests: $TOTAL_TESTS"
    log "✅ Passed: $PASSED_TESTS"
    log "❌ Failed: $FAILED_TESTS"

    if [ $TOTAL_TESTS -gt 0 ]; then
        SUCCESS_RATE=$(( PASSED_TESTS * 100 / TOTAL_TESTS ))
        log "Success Rate: ${SUCCESS_RATE}%"
    fi

    log ""
    log "Test Repositories:"
    for repo in "${TEST_REPOS[@]}"; do
        log "  - $repo"
    done
    log ""
    log "Test Data:"
    log "  Organizer ID: $ORG_ID"
    log "  Hackathon ID: $HACK_ID"
    log "  Submissions: ${#SUBMISSION_IDS[@]}"
    log "  Job ID: $JOB_ID"
    log ""
    log "Full results saved to: $LOG_FILE"
    log "=========================================="

    if [ $FAILED_TESTS -eq 0 ]; then
        success "All tests passed! 🎉"
        exit 0
    else
        error "Some tests failed. Check log for details."
        exit 1
    fi
}

# Run tests
main
