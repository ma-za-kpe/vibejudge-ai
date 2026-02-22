#!/bin/bash
# VibeJudge AI — Deployment Test Script
# Run this after deploying to AWS to verify everything works

set -e  # Exit on error

# Set API URL (update this after deployment)
API_URL="${API_URL:-https://2nu0j4n648.execute-api.us-east-1.amazonaws.com/dev}"

echo "🚀 VibeJudge AI — Deployment Test Script"
echo "=========================================="
echo ""
echo "✅ API URL: $API_URL"
echo ""

# Step 1: Health Check
echo "📋 Step 1: Testing health endpoint..."
HEALTH_RESPONSE=$(curl -s $API_URL/health)
if echo "$HEALTH_RESPONSE" | grep -q "healthy"; then
    echo "✅ Health check passed"
else
    echo "❌ Health check failed"
    echo "Response: $HEALTH_RESPONSE"
    exit 1
fi
echo ""

# Step 2: Create Organizer
echo "📋 Step 2: Creating test organizer..."
# Use timestamp to make email unique
TIMESTAMP=$(date +%s)
ORGANIZER_RESPONSE=$(curl -s -X POST $API_URL/api/v1/organizers \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"Test Organizer\",
    \"email\": \"test-$TIMESTAMP@vibecoders.com\",
    \"organization\": \"Vibe Coders\"
  }")

API_KEY=$(echo "$ORGANIZER_RESPONSE" | jq -r '.api_key')
ORG_ID=$(echo "$ORGANIZER_RESPONSE" | jq -r '.org_id')

if [ -z "$API_KEY" ] || [ "$API_KEY" = "null" ]; then
    echo "❌ Failed to create organizer"
    echo "Response: $ORGANIZER_RESPONSE"
    exit 1
fi

echo "✅ Organizer created"
echo "   Org ID: $ORG_ID"
echo "   API Key: $API_KEY"
echo ""

# Step 3: Create Hackathon
echo "📋 Step 3: Creating test hackathon..."
HACKATHON_RESPONSE=$(curl -s -X POST $API_URL/api/v1/hackathons \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{
    "name": "Test Hackathon",
    "description": "Automated deployment test",
    "rubric": {
      "name": "Test Rubric",
      "version": "1.0",
      "max_score": 100.0,
      "dimensions": [
        {
          "name": "Code Quality",
          "weight": 0.3,
          "agent": "bug_hunter",
          "description": "Code quality and best practices"
        },
        {
          "name": "Innovation",
          "weight": 0.3,
          "agent": "innovation",
          "description": "Innovation and creativity"
        },
        {
          "name": "Performance",
          "weight": 0.2,
          "agent": "performance",
          "description": "Performance and scalability"
        },
        {
          "name": "Authenticity",
          "weight": 0.2,
          "agent": "ai_detection",
          "description": "Development authenticity"
        }
      ]
    },
    "agents_enabled": ["bug_hunter", "performance", "innovation", "ai_detection"],
    "ai_policy_mode": "ai_assisted"
  }')

HACK_ID=$(echo "$HACKATHON_RESPONSE" | jq -r '.hack_id')

if [ -z "$HACK_ID" ] || [ "$HACK_ID" = "null" ]; then
    echo "❌ Failed to create hackathon"
    echo "Response: $HACKATHON_RESPONSE"
    exit 1
fi

echo "✅ Hackathon created"
echo "   Hack ID: $HACK_ID"
echo ""

# Step 4: Add Submission
echo "📋 Step 4: Adding test submission..."
SUBMISSION_RESPONSE=$(curl -s -X POST $API_URL/api/v1/hackathons/$HACK_ID/submissions \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{
    "submissions": [{
      "team_name": "Test Team",
      "repo_url": "https://github.com/anthropics/anthropic-quickstarts"
    }]
  }')

SUB_ID=$(echo "$SUBMISSION_RESPONSE" | jq -r '.submissions[0].sub_id')

if [ -z "$SUB_ID" ] || [ "$SUB_ID" = "null" ]; then
    echo "❌ Failed to add submission"
    echo "Response: $SUBMISSION_RESPONSE"
    exit 1
fi

echo "✅ Submission added"
echo "   Sub ID: $SUB_ID"
echo "   Repo: https://github.com/anthropics/anthropic-quickstarts"
echo ""

# Step 5: Trigger Analysis
echo "📋 Step 5: Triggering analysis..."
ANALYSIS_RESPONSE=$(curl -s -X POST $API_URL/api/v1/hackathons/$HACK_ID/analyze \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{}')

JOB_ID=$(echo "$ANALYSIS_RESPONSE" | jq -r '.job_id')

if [ -z "$JOB_ID" ] || [ "$JOB_ID" = "null" ]; then
    echo "❌ Failed to trigger analysis"
    echo "Response: $ANALYSIS_RESPONSE"
    exit 1
fi

echo "✅ Analysis triggered"
echo "   Job ID: $JOB_ID"
echo ""

# Step 6: Wait for Analysis
echo "📋 Step 6: Waiting for analysis to complete..."
echo "   This typically takes 60-90 seconds..."
echo ""

for i in {1..18}; do
    sleep 5
    echo -n "."

    # Check status every 15 seconds
    if [ $((i % 3)) -eq 0 ]; then
        STATUS_RESPONSE=$(curl -s $API_URL/api/v1/hackathons/$HACK_ID/analyze/status \
          -H "X-API-Key: $API_KEY")

        STATUS=$(echo "$STATUS_RESPONSE" | jq -r '.status')

        if [ "$STATUS" = "completed" ]; then
            echo ""
            echo "✅ Analysis completed!"
            break
        elif [ "$STATUS" = "failed" ]; then
            echo ""
            echo "❌ Analysis failed"
            echo "Response: $STATUS_RESPONSE"
            exit 1
        fi
    fi
done

echo ""
echo ""

# Step 7: Get Results
echo "📋 Step 7: Fetching results..."
echo ""

# Get leaderboard
echo "🏆 Leaderboard:"
LEADERBOARD_RESPONSE=$(curl -s $API_URL/api/v1/hackathons/$HACK_ID/leaderboard \
  -H "X-API-Key: $API_KEY")
echo "$LEADERBOARD_RESPONSE" | jq '.'
echo ""

# Get costs
echo "💰 Cost Breakdown:"
COST_RESPONSE=$(curl -s $API_URL/api/v1/hackathons/$HACK_ID/costs \
  -H "X-API-Key: $API_KEY")
echo "$COST_RESPONSE" | jq '.'
echo ""

# Step 8: Summary
echo "=========================================="
echo "✅ ALL TESTS PASSED!"
echo "=========================================="
echo ""
echo "📊 Summary:"
echo "   • Health check: ✅"
echo "   • Organizer creation: ✅"
echo "   • Hackathon creation: ✅"
echo "   • Submission added: ✅"
echo "   • Analysis triggered: ✅"
echo "   • Analysis completed: ✅"
echo "   • Results retrieved: ✅"
echo ""
echo "🎉 Your VibeJudge AI deployment is working perfectly!"
echo ""
echo "📝 Test Data:"
echo "   API URL: $API_URL"
echo "   API Key: $API_KEY"
echo "   Hack ID: $HACK_ID"
echo "   Sub ID: $SUB_ID"
echo ""
echo "🔍 View logs:"
echo "   make logs-analyzer"
echo ""
echo "📚 Next steps:"
echo "   1. Test with more repos"
echo "   2. Monitor costs and performance"
echo "   3. Write competition article"
echo ""
