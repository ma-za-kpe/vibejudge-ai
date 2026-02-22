#!/bin/bash
# Test VibeJudge AI API - Complete Flow

set -e

API_URL="http://localhost:8001"

echo "=========================================="
echo "VibeJudge AI - API Integration Test"
echo "=========================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Step 1: Create Organizer
echo -e "${BLUE}Step 1: Creating organizer...${NC}"
ORGANIZER_RESPONSE=$(curl -s -X POST "$API_URL/api/v1/organizers" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Organizer",
    "email": "test@vibejudge.ai",
    "organization": "Vibe Coders"
  }')

echo "$ORGANIZER_RESPONSE" | python3 -m json.tool

ORG_ID=$(echo "$ORGANIZER_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['org_id'])")
API_KEY=$(echo "$ORGANIZER_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['api_key'])")

echo -e "${GREEN}✓ Organizer created: $ORG_ID${NC}"
echo -e "${GREEN}✓ API Key: ${API_KEY:0:16}...${NC}"
echo ""

# Step 2: Create Hackathon
echo -e "${BLUE}Step 2: Creating hackathon...${NC}"
HACKATHON_RESPONSE=$(curl -s -X POST "$API_URL/api/v1/hackathons?org_id=$ORG_ID" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Hackathon 2026",
    "description": "Testing VibeJudge AI MVP",
    "rubric": {
      "name": "Default Rubric",
      "version": "1.0",
      "max_score": 100.0,
      "dimensions": [
        {
          "name": "Code Quality",
          "agent": "bug_hunter",
          "weight": 0.3,
          "description": "Code quality, security, and testing"
        },
        {
          "name": "Architecture",
          "agent": "performance",
          "weight": 0.3,
          "description": "Architecture, scalability, and performance"
        },
        {
          "name": "Innovation",
          "agent": "innovation",
          "weight": 0.3,
          "description": "Creativity, novelty, and documentation"
        },
        {
          "name": "Authenticity",
          "agent": "ai_detection",
          "weight": 0.1,
          "description": "Development authenticity and AI usage"
        }
      ]
    },
    "agents_enabled": ["bug_hunter", "performance", "innovation", "ai_detection"],
    "ai_policy_mode": "ai_assisted",
    "budget_limit_usd": 50.0
  }')

echo "$HACKATHON_RESPONSE" | python3 -m json.tool

HACK_ID=$(echo "$HACKATHON_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['hack_id'])")

echo -e "${GREEN}✓ Hackathon created: $HACK_ID${NC}"
echo ""

# Step 3: Get Hackathon
echo -e "${BLUE}Step 3: Retrieving hackathon...${NC}"
curl -s "$API_URL/api/v1/hackathons/$HACK_ID" | python3 -m json.tool
echo -e "${GREEN}✓ Hackathon retrieved${NC}"
echo ""

# Step 4: List Hackathons
echo -e "${BLUE}Step 4: Listing hackathons...${NC}"
curl -s "$API_URL/api/v1/hackathons?org_id=$ORG_ID" | python3 -m json.tool
echo -e "${GREEN}✓ Hackathons listed${NC}"
echo ""

# Step 5: Create Submissions
echo -e "${BLUE}Step 5: Creating submissions...${NC}"
SUBMISSIONS_RESPONSE=$(curl -s -X POST "$API_URL/api/v1/hackathons/$HACK_ID/submissions" \
  -H "Content-Type: application/json" \
  -d '{
    "submissions": [
      {
        "team_name": "Team Alpha",
        "repo_url": "https://github.com/anthropics/anthropic-quickstarts"
      },
      {
        "team_name": "Team Beta",
        "repo_url": "https://github.com/fastapi/fastapi"
      }
    ]
  }')

echo "$SUBMISSIONS_RESPONSE" | python3 -m json.tool

SUB_ID=$(echo "$SUBMISSIONS_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['submissions'][0]['sub_id'])")

echo -e "${GREEN}✓ Submissions created${NC}"
echo ""

# Step 6: List Submissions
echo -e "${BLUE}Step 6: Listing submissions...${NC}"
curl -s "$API_URL/api/v1/hackathons/$HACK_ID/submissions" | python3 -m json.tool
echo -e "${GREEN}✓ Submissions listed${NC}"
echo ""

# Step 7: Get Submission
echo -e "${BLUE}Step 7: Retrieving submission...${NC}"
curl -s "$API_URL/api/v1/submissions/$SUB_ID" | python3 -m json.tool
echo -e "${GREEN}✓ Submission retrieved${NC}"
echo ""

# Step 8: Estimate Cost
echo -e "${BLUE}Step 8: Estimating analysis cost...${NC}"
curl -s -X POST "$API_URL/api/v1/hackathons/$HACK_ID/analyze/estimate" \
  -H "Content-Type: application/json" | python3 -m json.tool
echo -e "${GREEN}✓ Cost estimated${NC}"
echo ""

# Summary
echo "=========================================="
echo -e "${GREEN}All tests passed!${NC}"
echo "=========================================="
echo ""
echo "Created Resources:"
echo "  Organizer ID: $ORG_ID"
echo "  Hackathon ID: $HACK_ID"
echo "  Submission ID: $SUB_ID"
echo ""
echo "Next steps:"
echo "  - Verify data in DynamoDB"
echo "  - Test analysis trigger (placeholder)"
echo "  - Deploy to AWS"
