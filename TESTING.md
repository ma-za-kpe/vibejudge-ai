# VibeJudge AI — Local Testing Guide

This guide covers local development and testing before deploying to AWS.

## Prerequisites

### Required Software
- Python 3.12+
- Docker (for local DynamoDB)
- AWS CLI v2
- AWS SAM CLI
- Git

### AWS Setup
1. AWS account with Bedrock access enabled
2. AWS credentials configured (`~/.aws/credentials`)
3. Bedrock model access granted:
   - `amazon.nova-micro-v1:0`
   - `amazon.nova-lite-v1:0`
   - `anthropic.claude-sonnet-4-20250514`

To request Bedrock model access:
```bash
# Go to AWS Console → Bedrock → Model access
# Request access for Nova Micro, Nova Lite, and Claude Sonnet 4
```

### Python Environment
```bash
# Create virtual environment
python3.12 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
make install-dev

# Or manually:
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### Environment Variables
```bash
# Create .env file from template
make env

# Edit .env with your values
# Minimum required:
# - AWS_REGION=us-east-1
# - AWS_PROFILE=default (or your profile name)
# - DYNAMODB_TABLE_NAME=VibeJudgeTable
```

---

## Testing Strategy

### 1. Unit Tests (No AWS Required)
Run unit tests with mocked AWS services:

```bash
# Run all unit tests
make test-unit

# Run with coverage
make test-cov

# Run specific test file
pytest tests/unit/test_agents.py -v

# Run specific test
pytest tests/unit/test_agents.py::test_bug_hunter_initialization -v
```

**What's tested:**
- Pydantic model validation
- Agent response parsing
- Orchestrator logic
- Cost calculations
- Evidence validation

**Current status:** 48 tests passing ✅

### 2. Local API Testing (FastAPI + Uvicorn)
Best for rapid development and debugging:

```bash
# Terminal 1: Start local DynamoDB
make dynamodb-local

# Terminal 2: Create table (one-time setup)
make create-table-local

# Terminal 3: Start FastAPI server
make run-local
```

The API will be available at:
- **API Base:** http://localhost:8000
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

**Test endpoints:**
```bash
# Health check
curl http://localhost:8000/health

# Create organizer (returns API key)
curl -X POST http://localhost:8000/api/v1/organizers \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Organizer",
    "email": "test@example.com",
    "organization": "Test Org"
  }'

# Create hackathon (use API key from above)
curl -X POST http://localhost:8000/api/v1/hackathons \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_API_KEY" \
  -d '{
    "name": "Test Hackathon 2026",
    "description": "Testing VibeJudge AI",
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
    "ai_policy_mode": "ai_assisted"
  }'
```

### 3. SAM Local Testing (Lambda Simulation)
Test Lambda functions locally with SAM:

```bash
# Build SAM application
make build

# Test API Lambda with sample event
make local-invoke-api

# Test Analyzer Lambda with sample event
make local-invoke-analyzer

# Start API Gateway locally (alternative to uvicorn)
make local-api
```

**Note:** SAM local uses Docker to simulate Lambda environment. It's slower than uvicorn but more accurate.

---

## Testing the Analysis Pipeline

### Test Repository
We use `anthropic-quickstarts` as a test repo because it's:
- Small (~50 files, <5MB)
- Well-documented
- Real-world code quality
- Public (no auth needed)

### End-to-End Test Flow

#### Option A: Using Local FastAPI Server (Recommended)
```bash
# 1. Start services
make dynamodb-local  # Terminal 1
make run-local       # Terminal 2

# 2. Create organizer and hackathon (see API testing above)

# 3. Submit a repo for analysis
curl -X POST http://localhost:8000/api/v1/submissions \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_API_KEY" \
  -d '{
    "hackathon_id": "HACK#YOUR_HACK_ID",
    "team_name": "Test Team",
    "repo_url": "https://github.com/anthropics/anthropic-quickstarts",
    "submission_time": "2026-02-21T10:00:00Z"
  }'

# 4. Trigger analysis (this will call Bedrock!)
curl -X POST http://localhost:8000/api/v1/analysis/analyze \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_API_KEY" \
  -d @events/test-analysis-request.json

# 5. Check analysis status
curl http://localhost:8000/api/v1/analysis/status/SUB#YOUR_SUB_ID \
  -H "X-API-Key: YOUR_API_KEY"

# 6. View results
curl http://localhost:8000/api/v1/submissions/SUB#YOUR_SUB_ID \
  -H "X-API-Key: YOUR_API_KEY"
```

#### Option B: Direct Lambda Invocation
```bash
# Invoke Analyzer Lambda directly with test event
make local-invoke-analyzer

# This uses events/test-analysis.json
# Edit the file to test different repos or configurations
```

---

## Cost Monitoring

### Expected Costs (Per Analysis)
Based on `anthropic-quickstarts` repo:

| Agent | Model | Est. Tokens | Est. Cost |
|-------|-------|-------------|-----------|
| BugHunter | Nova Lite | 30K in, 5K out | $0.0030 |
| Performance | Nova Lite | 30K in, 5K out | $0.0030 |
| Innovation | Claude Sonnet 4 | 30K in, 5K out | $0.1650 |
| AIDetection | Nova Micro | 20K in, 3K out | $0.0011 |
| **TOTAL** | | | **~$0.17** |

### Track Costs in Real-Time
```bash
# View cost breakdown after analysis
curl http://localhost:8000/api/v1/costs/hackathons/HACK#YOUR_HACK_ID \
  -H "X-API-Key: YOUR_API_KEY"

# View per-submission costs
curl http://localhost:8000/api/v1/costs/submissions/SUB#YOUR_SUB_ID \
  -H "X-API-Key: YOUR_API_KEY"
```

### Cost Safety Limits
The system has built-in cost limits:
- Max $1.00 per submission (safety limit)
- Default $50.00 per hackathon budget
- Analysis stops if budget exceeded

---

## Troubleshooting

### Issue: "Bedrock model not found"
**Solution:** Request model access in AWS Console → Bedrock → Model access

### Issue: "DynamoDB table not found"
**Solution:** 
```bash
# Check if local DynamoDB is running
docker ps | grep dynamodb

# Create table
make create-table-local

# Verify table exists
aws dynamodb list-tables --endpoint-url http://localhost:8000
```

### Issue: "Git clone failed"
**Solution:**
- Check repo URL is valid and public
- Ensure git is installed: `git --version`
- Check disk space in /tmp (Lambda uses ephemeral storage)

### Issue: "Lambda timeout"
**Solution:**
- Reduce repo size (MAX_REPO_SIZE_MB in .env)
- Reduce context size (MAX_CONTEXT_FILES in .env)
- Increase timeout in template.yaml (max 900s for Lambda)

### Issue: "Rate limit exceeded"
**Solution:**
- Add GITHUB_TOKEN to .env for higher rate limits
- Wait 60 minutes for rate limit reset
- Use smaller repos for testing

### Issue: "Import errors"
**Solution:**
```bash
# Ensure virtual environment is activated
source .venv/bin/activate

# Reinstall dependencies
make install-dev

# Check Python version
python --version  # Should be 3.12+
```

### Issue: "Tests failing"
**Solution:**
```bash
# Run tests with verbose output
pytest tests/unit/test_agents.py -v -s

# Check for Pydantic validation errors
pytest tests/unit/test_agents.py::test_bug_hunter_analysis -v -s

# Verify mock data matches schemas
# See tests/conftest.py for fixture definitions
```

---

## Development Workflow

### Recommended Flow
1. Write unit tests first (TDD)
2. Run tests: `make test-unit`
3. Start local API: `make run-local`
4. Test endpoints with Swagger UI
5. Run full analysis with test repo
6. Check logs and costs
7. Iterate

### Code Quality Checks
```bash
# Run all quality checks
make quality

# Or individually:
make lint        # Ruff linter
make format      # Black formatter
make type-check  # Mypy type checker
```

### Pre-Commit Checklist
```bash
# Run before committing
make pre-commit

# This runs:
# - Code formatting
# - Linting
# - Unit tests
```

---

## Next Steps

Once local testing is complete:

1. **Deploy to AWS Dev:**
   ```bash
   make deploy-dev
   ```

2. **Test deployed API:**
   ```bash
   # Get API Gateway URL from SAM output
   export API_URL="https://YOUR_API_ID.execute-api.us-east-1.amazonaws.com"
   
   curl $API_URL/health
   ```

3. **Monitor logs:**
   ```bash
   make logs-api       # API Lambda logs
   make logs-analyzer  # Analyzer Lambda logs
   ```

4. **Run integration tests:**
   ```bash
   make test-integration
   ```

---

## Useful Commands Reference

```bash
# Development
make run-local              # Start FastAPI with uvicorn
make test                   # Run all tests
make test-cov               # Run tests with coverage
make quality                # Run all code quality checks

# Local Lambda Testing
make build                  # Build SAM application
make local-invoke-analyzer  # Test Analyzer Lambda
make local-api              # Start API Gateway locally

# Database
make dynamodb-local         # Start local DynamoDB
make create-table-local     # Create table in local DynamoDB

# Deployment
make deploy-dev             # Deploy to dev environment
make logs-api               # Tail API logs
make logs-analyzer          # Tail Analyzer logs

# Cleanup
make clean                  # Clean build artifacts
make clean-repos            # Clean cloned test repos
```

---

## Support

For issues or questions:
1. Check this guide's troubleshooting section
2. Review logs: `make logs-api` or `make logs-analyzer`
3. Check AWS CloudWatch for detailed error traces
4. Review Bedrock quotas in AWS Console
5. See [REALITY_CHECK.md](REALITY_CHECK.md) for platform audit findings
6. See [COST_TRACKING_FIX.md](COST_TRACKING_FIX.md) for cost tracking bugfix details

---

**Last Updated:** February 22, 2026  
**Version:** 1.0.0
