#!/bin/bash
# Test script for individual submission analysis flow
# This script tests what happens when user clicks ▶️ analyze button

set -e

# Configuration
API_BASE_URL="${API_BASE_URL:-https://2nu0j4n648.execute-api.us-east-1.amazonaws.com/dev/api/v1}"
API_KEY="${API_KEY:-vj_live_SCoecIaoqCSnMkFUJ/6FJIdq+9zZ2jms}"
HACKATHON_ID="${HACKATHON_ID:-01KJFQW23JKE473T0ZPSGSQ2J6}"

echo "=================================================="
echo "Testing Individual Submission Analysis Flow"
echo "=================================================="
echo ""
echo "API Base URL: $API_BASE_URL"
echo "Hackathon ID: $HACKATHON_ID"
echo ""

# Step 1: Get list of submissions to find a pending one
echo "Step 1: Fetching submissions list..."
echo "Endpoint: GET /hackathons/{hack_id}/submissions"
echo ""

SUBMISSIONS_RESPONSE=$(curl -s \
  -H "X-API-Key: $API_KEY" \
  "$API_BASE_URL/hackathons/$HACKATHON_ID/submissions")

echo "Response:"
echo "$SUBMISSIONS_RESPONSE" | jq '.'
echo ""

# Extract a pending submission ID
PENDING_SUB_ID=$(echo "$SUBMISSIONS_RESPONSE" | jq -r '.submissions[] | select(.status == "pending") | .sub_id' | head -1)
TEAM_NAME=$(echo "$SUBMISSIONS_RESPONSE" | jq -r ".submissions[] | select(.sub_id == \"$PENDING_SUB_ID\") | .team_name")

if [ -z "$PENDING_SUB_ID" ]; then
    echo "❌ No pending submissions found. Cannot test analyze flow."
    exit 1
fi

echo "✅ Found pending submission:"
echo "   Submission ID: $PENDING_SUB_ID"
echo "   Team Name: $TEAM_NAME"
echo ""

# Step 2: User clicks ▶️ button - Dashboard shows confirmation
echo "Step 2: User clicks ▶️ analyze button"
echo "        (Frontend sets session state and shows confirmation dialog)"
echo "        Confirmation shows: Team Name and Submission ID"
echo ""

# Step 3: Check current analysis status
echo "Step 3: Checking current analysis status..."
echo "Endpoint: GET /hackathons/{hack_id}/analyze/status"
echo ""

STATUS_RESPONSE=$(curl -s \
  -H "X-API-Key: $API_KEY" \
  "$API_BASE_URL/hackathons/$HACKATHON_ID/analyze/status" \
  -w "\nHTTP_CODE: %{http_code}\n")

echo "Response:"
echo "$STATUS_RESPONSE" | sed '/^HTTP_CODE:/d' | jq '.' 2>/dev/null || echo "$STATUS_RESPONSE"
HTTP_CODE=$(echo "$STATUS_RESPONSE" | grep "HTTP_CODE:" | cut -d' ' -f2)
echo ""

# Step 4: User clicks "Confirm & Analyze" - Triggers analysis
echo "Step 4: User clicks 'Confirm & Analyze' button"
echo "Endpoint: POST /hackathons/{hack_id}/analyze"
echo "Payload: {\"submission_ids\": [\"$PENDING_SUB_ID\"]}"
echo ""

ANALYZE_RESPONSE=$(curl -s \
  -X POST \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"submission_ids\": [\"$PENDING_SUB_ID\"]}" \
  "$API_BASE_URL/hackathons/$HACKATHON_ID/analyze" \
  -w "\nHTTP_CODE: %{http_code}\n")

echo "Response:"
ANALYZE_BODY=$(echo "$ANALYZE_RESPONSE" | sed '/^HTTP_CODE:/d')
echo "$ANALYZE_BODY" | jq '.' 2>/dev/null || echo "$ANALYZE_BODY"
ANALYZE_HTTP_CODE=$(echo "$ANALYZE_RESPONSE" | grep "HTTP_CODE:" | cut -d' ' -f2)
echo ""

if [ "$ANALYZE_HTTP_CODE" != "202" ] && [ "$ANALYZE_HTTP_CODE" != "200" ]; then
    echo "❌ Analysis request failed with HTTP $ANALYZE_HTTP_CODE"
    echo "   This could mean:"
    echo "   - Analysis already in progress (409)"
    echo "   - Invalid API key (401)"
    echo "   - Budget exceeded (402)"
    echo "   - Rate limited (429)"
    exit 1
fi

# Extract job ID from response
JOB_ID=$(echo "$ANALYZE_BODY" | jq -r '.job_id' 2>/dev/null)
ESTIMATED_COST=$(echo "$ANALYZE_BODY" | jq -r '.estimated_cost_usd' 2>/dev/null)

echo "✅ Analysis job started successfully!"
echo "   Job ID: $JOB_ID"
echo "   Estimated Cost: \$$ESTIMATED_COST"
echo ""

# Step 5: Monitor job status
echo "Step 5: Monitoring job status..."
echo "Endpoint: GET /hackathons/{hack_id}/analyze/status"
echo ""

for i in {1..3}; do
    sleep 2

    JOB_STATUS=$(curl -s \
      -H "X-API-Key: $API_KEY" \
      "$API_BASE_URL/hackathons/$HACKATHON_ID/analyze/status")

    STATUS=$(echo "$JOB_STATUS" | jq -r '.status')
    PROGRESS=$(echo "$JOB_STATUS" | jq -r '.progress.percent_complete')

    echo "Check $i: Status=$STATUS, Progress=$PROGRESS%"

    if [ "$STATUS" = "completed" ]; then
        echo ""
        echo "✅ Analysis completed!"
        break
    fi
done

echo ""
echo "=================================================="
echo "Summary: What Happens When You Click ▶️"
echo "=================================================="
echo ""
echo "1. Frontend: Click ▶️ on submission '$TEAM_NAME'"
echo "   → Button changes to ⏳"
echo "   → Shows confirmation dialog with team name and submission ID"
echo ""
echo "2. Frontend: Click 'Confirm & Analyze'"
echo "   → POST /hackathons/{hack_id}/analyze"
echo "   → Payload: {\"submission_ids\": [\"$PENDING_SUB_ID\"]}"
echo ""
echo "3. Backend: Analysis Service"
echo "   → Creates analysis job record in DynamoDB"
echo "   → Sets hackathon analysis_status = 'in_progress'"
echo "   → Invokes Analyzer Lambda asynchronously"
echo "   → Returns job_id and estimated_cost_usd"
echo ""
echo "4. Backend: Analyzer Lambda"
echo "   → Clones GitHub repository"
echo "   → Runs code analysis agents"
echo "   → Stores results in DynamoDB"
echo "   → Updates job status to 'completed'"
echo "   → Resets hackathon analysis_status to 'not_started'"
echo ""
echo "5. Frontend: Shows Success"
echo "   → Displays job ID: $JOB_ID"
echo "   → Displays estimated cost: \$$ESTIMATED_COST"
echo "   → Page reloads to show updated status"
echo ""
echo "=================================================="
echo "API Endpoints Called (in order):"
echo "=================================================="
echo "1. GET  /hackathons/{hack_id}/submissions"
echo "2. GET  /hackathons/{hack_id}/analyze/status"
echo "3. POST /hackathons/{hack_id}/analyze"
echo "4. GET  /hackathons/{hack_id}/analyze/status (polling)"
echo ""
