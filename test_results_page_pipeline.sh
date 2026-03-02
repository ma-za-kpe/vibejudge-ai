#!/bin/bash
# Test script for Results Page fixes - Run after quota resets
# This script tests the complete pipeline end-to-end

set -e

HACK_ID="01KJFQW23JKE473T0ZPSGSQ2J6"
API_KEY="vj_live_SCoecIaoqCSnMkFUJ/6FJIdq+9zZ2jms"
API_URL="https://2nu0j4n648.execute-api.us-east-1.amazonaws.com/dev/api/v1"

echo "======================================"
echo "Results Page Pipeline Test"
echo "======================================"
echo ""

# Step 1: Add test submissions
echo "Step 1: Adding 3 test submissions..."
curl -X POST \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "submissions": [
      {"team_name": "Innovation Squad", "repo_url": "https://github.com/streamlit/streamlit"},
      {"team_name": "Code Ninjas", "repo_url": "https://github.com/fastapi/fastapi"},
      {"team_name": "Tech Wizards", "repo_url": "https://github.com/pallets/flask"}
    ]
  }' \
  "$API_URL/hackathons/$HACK_ID/submissions" | jq '.'

echo ""
echo "Step 2: Listing all submissions..."
SUBMISSIONS=$(curl -s -H "X-API-Key: $API_KEY" "$API_URL/hackathons/$HACK_ID/submissions")
echo "$SUBMISSIONS" | jq '.submissions[] | {team_name, sub_id, status}'

# Extract submission IDs
SUB_IDS=$(echo "$SUBMISSIONS" | jq -r '.submissions[] | select(.status == "pending") | .sub_id')

if [ -z "$SUB_IDS" ]; then
  echo ""
  echo "❌ No pending submissions found. Cannot continue test."
  exit 1
fi

echo ""
echo "Step 3: Get cost estimate..."
curl -s -X POST -H "X-API-Key: $API_KEY" "$API_URL/hackathons/$HACK_ID/analyze/estimate" | jq '.'

echo ""
echo "Step 4: Starting analysis for all pending submissions..."
ANALYSIS_RESPONSE=$(curl -s -X POST -H "X-API-Key: $API_KEY" -H "Content-Type: application/json" -d '{}' "$API_URL/hackathons/$HACK_ID/analyze")
echo "$ANALYSIS_RESPONSE" | jq '.'

JOB_ID=$(echo "$ANALYSIS_RESPONSE" | jq -r '.job_id')

if [ "$JOB_ID" == "null" ] || [ -z "$JOB_ID" ]; then
  echo ""
  echo "❌ Failed to start analysis job"
  exit 1
fi

echo ""
echo "✅ Analysis job started: $JOB_ID"
echo ""
echo "Step 5: Monitoring analysis progress..."

for i in {1..20}; do
  sleep 10
  echo "  Check $i/20..."

  STATUS_RESPONSE=$(curl -s -H "X-API-Key: $API_KEY" "$API_URL/hackathons/$HACK_ID/analyze/status")
  STATUS=$(echo "$STATUS_RESPONSE" | jq -r '.status')
  PROGRESS=$(echo "$STATUS_RESPONSE" | jq -r '.progress.percent_complete // 0')
  COMPLETED=$(echo "$STATUS_RESPONSE" | jq -r '.progress.completed // 0')
  FAILED=$(echo "$STATUS_RESPONSE" | jq -r '.progress.failed // 0')

  echo "    Status: $STATUS | Progress: ${PROGRESS}% | Completed: $COMPLETED | Failed: $FAILED"

  if [ "$STATUS" == "completed" ]; then
    echo ""
    echo "✅ Analysis completed!"
    break
  fi

  if [ "$STATUS" == "failed" ]; then
    echo ""
    echo "❌ Analysis failed"
    echo "$STATUS_RESPONSE" | jq '.error'
    exit 1
  fi
done

echo ""
echo "Step 6: Fetching leaderboard..."
curl -s -H "X-API-Key: $API_KEY" "$API_URL/hackathons/$HACK_ID/leaderboard" | jq '.submissions[] | {rank, team_name, overall_score, recommendation}'

echo ""
echo "Step 7: Testing scorecard endpoint for first completed submission..."
# Get first completed submission ID
COMPLETED_SUB_ID=$(curl -s -H "X-API-Key: $API_KEY" "$API_URL/hackathons/$HACK_ID/submissions" | jq -r '.submissions[] | select(.status == "completed") | .sub_id' | head -1)

if [ -z "$COMPLETED_SUB_ID" ]; then
  echo "❌ No completed submissions found"
  exit 1
fi

echo "  Submission ID: $COMPLETED_SUB_ID"
echo ""
echo "  Fetching scorecard..."
SCORECARD=$(curl -s -H "X-API-Key: $API_KEY" "$API_URL/hackathons/$HACK_ID/submissions/$COMPLETED_SUB_ID/scorecard")

echo ""
echo "  Validating scorecard structure..."
echo "$SCORECARD" | jq '{
  team_name,
  overall_score,
  has_weighted_scores: (.weighted_scores != null),
  agent_scores_count: (.agent_scores | length),
  has_team_dynamics: (.team_dynamics != null),
  has_strategy_analysis: (.strategy_analysis != null),
  has_actionable_feedback: (.actionable_feedback != null)
}'

echo ""
echo "  Agent scores structure:"
echo "$SCORECARD" | jq '.agent_scores[] | {agent_name, overall_score, confidence, has_summary: (.summary != null), has_scores: (.scores != null), evidence_count: (.evidence | length)}'

echo ""
echo "======================================"
echo "✅ Pipeline test complete!"
echo "======================================"
echo ""
echo "📊 Next step: Open production dashboard and verify Results page displays all data correctly"
echo "   Dashboard URL: http://vibejudge-alb-prod-1135403146.us-east-1.elb.amazonaws.com"
echo ""
echo "✅ Checklist for manual verification:"
echo "   [ ] Tab 1 (Overview): Shows overall score, confidence, recommendation, dimension scores table"
echo "   [ ] Tab 2 (Agent Analysis): Shows all agents with scores, confidence, summary, detailed scores, evidence"
echo "   [ ] Tab 3 (Repository): Shows repo metadata (language, commits, contributors, tests, CI)"
echo "   [ ] Tab 4 (Team Dynamics): Shows team dynamics grade, strategy analysis, actionable feedback"
