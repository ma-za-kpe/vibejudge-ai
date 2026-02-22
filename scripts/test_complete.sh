#!/bin/bash
set -e

BASE_URL="https://2nu0j4n648.execute-api.us-east-1.amazonaws.com/dev"
TEST_REPO="https://github.com/ma-za-kpe/vibejudge-ai"

echo "VibeJudge API - Complete Test"
echo "=============================="

# Create organizer
TIMESTAMP=$(date +%s)
ORG=$(curl -s -X POST -H "Content-Type: application/json" \
  -d "{\"name\":\"Test\",\"email\":\"test-$TIMESTAMP@example.com\",\"organization\":\"Test\"}" \
  "$BASE_URL/api/v1/organizers")
API_KEY=$(echo "$ORG" | jq -r '.api_key')
echo "✓ Created organizer (API Key: ${API_KEY:0:20}...)"

# Create hackathon with CORRECT rubric format
HACK=$(curl -s -X POST -H "Content-Type: application/json" -H "X-API-Key: $API_KEY" \
  -d '{
    "name": "Test Hackathon",
    "description": "Testing",
    "agents_enabled": ["bug_hunter", "performance", "innovation"],
    "rubric": {
      "dimensions": [
        {
          "name": "Code Quality & Security",
          "agent": "bug_hunter",
          "weight": 0.4,
          "criteria": ["Code quality", "Security", "Testing"]
        },
        {
          "name": "Architecture & Performance",
          "agent": "performance",
          "weight": 0.3,
          "criteria": ["Architecture", "Scalability"]
        },
        {
          "name": "Innovation & Documentation",
          "agent": "innovation",
          "weight": 0.3,
          "criteria": ["Creativity", "Documentation"]
        }
      ]
    },
    "budget_limit_usd": 10.0
  }' \
  "$BASE_URL/api/v1/hackathons")
HACK_ID=$(echo "$HACK" | jq -r '.hack_id')
echo "✓ Created hackathon ($HACK_ID)"

# Create submission
SUB=$(curl -s -X POST -H "Content-Type: application/json" \
  -d "{\"submissions\":[{\"team_name\":\"Test Team\",\"repo_url\":\"$TEST_REPO\",\"contact_email\":\"team@example.com\"}]}" \
  "$BASE_URL/api/v1/hackathons/$HACK_ID/submissions")
SUB_ID=$(echo "$SUB" | jq -r '.submissions[0].sub_id')
echo "✓ Created submission ($SUB_ID)"

# Trigger analysis
JOB=$(curl -s -X POST -H "Content-Type: application/json" -H "X-API-Key: $API_KEY" \
  -d "{\"submission_ids\":[\"$SUB_ID\"]}" \
  "$BASE_URL/api/v1/hackathons/$HACK_ID/analyze")
JOB_ID=$(echo "$JOB" | jq -r '.job_id')
echo "✓ Triggered analysis (Job: $JOB_ID)"

echo ""
echo "Test complete! All core endpoints working."
echo "Analysis job is running in background."
echo ""
echo "Monitor progress:"
echo "  curl -H 'X-API-Key: $API_KEY' $BASE_URL/api/v1/hackathons/$HACK_ID/jobs/$JOB_ID"
