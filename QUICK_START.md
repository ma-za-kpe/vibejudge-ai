# VibeJudge AI — Quick Start Guide

**5-Minute Setup for AWS Deployment**

---

## Prerequisites

```bash
# Check you have these installed
python --version    # Should be 3.12+
aws --version       # AWS CLI configured
sam --version       # AWS SAM CLI
docker --version    # For local testing
```

---

## Step 1: Enable Bedrock Models (5 minutes)

1. Go to [AWS Console → Bedrock → Model Access](https://console.aws.amazon.com/bedrock/home#/modelaccess)
2. Click "Manage model access"
3. Enable these models:
   - ✅ `amazon.nova-micro-v1:0`
   - ✅ `amazon.nova-lite-v1:0`
   - ✅ `anthropic.claude-sonnet-4-20250514`
4. Click "Save changes"
5. Wait for "Access granted" status (usually instant)

**⚠️ Critical:** Analysis will fail without these models!

---

## Step 2: Deploy to AWS (2 minutes)

```bash
# Clone and setup
git clone <your-repo>
cd vibejudge-ai
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Deploy to dev environment
make deploy-dev

# Save the API URL from output:
# https://xxxxxxxxxx.execute-api.us-east-1.amazonaws.com
```

---

## Step 3: Test the API (3 minutes)

```bash
# Set your API URL
export API_URL="https://xxxxxxxxxx.execute-api.us-east-1.amazonaws.com"

# 1. Health check
curl $API_URL/health

# 2. Create organizer account
curl -X POST $API_URL/api/v1/organizers \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Organizer",
    "email": "test@example.com",
    "organization": "Test Org"
  }'

# Save the API key from response!
export API_KEY="vj_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"

# 3. Create hackathon
curl -X POST $API_URL/api/v1/hackathons \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{
    "name": "Test Hackathon",
    "description": "Testing deployment",
    "rubric": {
      "dimensions": {
        "code_quality": {"weight": 0.3, "description": "Code quality"},
        "innovation": {"weight": 0.3, "description": "Innovation"},
        "performance": {"weight": 0.2, "description": "Performance"},
        "authenticity": {"weight": 0.2, "description": "Authenticity"}
      }
    },
    "agents_enabled": ["bug_hunter", "performance", "innovation", "ai_detection"],
    "ai_policy_mode": "encouraged"
  }'

# Save hack_id from response
export HACK_ID="hack_xxxxxxxxxxxxxxxxxxxxxxxxxx"

# 4. Add submission
curl -X POST $API_URL/api/v1/hackathons/$HACK_ID/submissions \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{
    "submissions": [{
      "team_name": "Test Team",
      "repo_url": "https://github.com/anthropics/anthropic-quickstarts"
    }]
  }'

# 5. Trigger analysis
curl -X POST $API_URL/api/v1/hackathons/$HACK_ID/analyze \
  -H "X-API-Key: $API_KEY"

# Save job_id from response
export JOB_ID="job_xxxxxxxxxxxxxxxxxxxxxxxxxx"

# 6. Wait 60 seconds, then check status
sleep 60
curl $API_URL/api/v1/hackathons/$HACK_ID/analyze/status \
  -H "X-API-Key: $API_KEY"

# 7. View leaderboard
curl $API_URL/api/v1/hackathons/$HACK_ID/leaderboard \
  -H "X-API-Key: $API_KEY"
```

---

## Step 4: View API Documentation

Open in browser:
```
https://xxxxxxxxxx.execute-api.us-east-1.amazonaws.com/docs
```

---

## Common Issues

### "Model access denied"
→ Enable Bedrock models in AWS Console (Step 1)

### "Lambda timeout"
→ Check CloudWatch logs: `make logs-analyzer`

### "403 Forbidden"
→ Check API key: `echo $API_KEY` (should start with "vj_")

### "Analysis stuck in PENDING"
→ Check Lambda logs for errors: `make logs-analyzer`

---

## Next Steps

- Read [DEPLOYMENT.md](DEPLOYMENT.md) for detailed guide
- Read [TESTING.md](TESTING.md) for local development
- Check [PROJECT_STATUS.md](PROJECT_STATUS.md) for full status

---

## Cost Estimate

**Per submission:** ~$0.025 (mostly Bedrock)  
**500 submissions:** ~$11.50  
**All other AWS services:** Free Tier ✅

---

## Support

- CloudWatch Logs: `make logs-api` or `make logs-analyzer`
- Issues: Check GitHub issues
- Email: maku@vibecoders.com

---

**Built with ❤️ using Kiro AI IDE**
