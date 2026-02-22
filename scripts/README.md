# VibeJudge AI - Test Scripts

This directory contains all test and utility scripts for the VibeJudge AI platform.

## Main Test Scripts

### comprehensive_test.sh
**Purpose:** Complete end-to-end test suite  
**Tests:** All 20 API endpoints + 3 diverse GitHub repositories  
**Status:** ✅ Fixed and working (Feb 22, 2026)  
**Usage:**
```bash
./scripts/comprehensive_test.sh
```

**What it tests:**
- Health check
- Organizer management (create, read, update)
- Hackathon management (CRUD operations)
- Submission management (batch creation with multiple repos)
- Analysis pipeline (trigger, monitor, complete)
- Results retrieval (scorecard, evidence, leaderboard)
- Cost tracking (per-submission and per-hackathon)

**Test Repositories:**
1. vibejudge-ai (this project)
2. anthropic-quickstarts (small, well-documented)
3. fastapi (popular Python framework)

**Expected Duration:** 5-10 minutes (depending on analysis time)

**Features:**
- Proper batch submission format with correct JSON structure
- Correct API endpoint URLs (fixed: /estimate, /jobs, /analyze with body)
- Real-time analysis monitoring via jobs list endpoint
- Color-coded output
- Detailed logging to timestamped files
- Success/failure tracking with summary

**Recent Fixes (Feb 22, 2026):**
- Fixed cost estimation endpoint: `/analyze/estimate` → `/estimate`
- Added required JSON body to analysis trigger: `{"submission_ids": null}`
- Fixed job monitoring: `/analyze/status` → `/jobs` with array parsing

---

## Legacy Test Scripts

### test_all_endpoints.sh
Basic endpoint testing script (20 endpoints)

### test_complete.sh
Complete flow test with single repository

### test_deployment.sh
Deployment verification script

### test_endpoints_fixed.sh
Fixed endpoint testing after route corrections

### test_live_api.sh
Live API testing script

### test_api_flow.sh
API flow testing

---

## Utility Scripts

### start_local.sh
Start local development server

### start_api_local.sh
Start API locally with uvicorn

---

## Python Test Scripts

### test_local_api.py
Python-based local API testing

### test_api_direct.py
Direct API testing with Python requests

---

## Test Results

Test results are saved with timestamps:
- `test_results_YYYYMMDD_HHMMSS.log` - Comprehensive test logs
- `endpoint_test_results.txt` - Legacy endpoint test results
- `final_test_results.txt` - Final test results
- `test_results.txt` - General test results

---

## Running Tests

### Prerequisites
- AWS credentials configured
- API deployed to AWS
- `jq` installed for JSON parsing
- `curl` installed for HTTP requests

### Quick Start
```bash
# Run comprehensive test suite
./scripts/comprehensive_test.sh

# View latest results
cat scripts/test_results_*.log | tail -100
```

### Environment Variables
```bash
# Override API URL (default: production)
export API_URL="https://your-api-url.execute-api.us-east-1.amazonaws.com/dev"

# Run tests
./scripts/comprehensive_test.sh
```

---

## Test Coverage

**Endpoints Tested:** 20/20 (100%)
- 1 Health check
- 4 Organizer management
- 5 Hackathon management
- 6 Submission management
- 3 Analysis pipeline
- 1 Leaderboard
- 2 Cost tracking

**Repository Diversity:**
- Small repos (~50 files)
- Medium repos (~500 files)
- Large repos (~2000 files)
- Different languages (Python, JavaScript, etc.)
- Different architectures (monolith, microservices)

---

## Troubleshooting

### Issue: "jq: command not found"
```bash
# macOS
brew install jq

# Ubuntu/Debian
sudo apt-get install jq
```

### Issue: "curl: command not found"
```bash
# macOS (should be pre-installed)
brew install curl

# Ubuntu/Debian
sudo apt-get install curl
```

### Issue: "Analysis timeout"
- Increase `MAX_WAIT` in comprehensive_test.sh
- Check Lambda logs for errors
- Verify Bedrock model access

### Issue: "API key invalid"
- Script generates new organizer automatically
- Check API_URL is correct
- Verify deployment is healthy

---

## Best Practices

1. **Run comprehensive tests before deployment**
2. **Review logs after each test run**
3. **Test with diverse repositories**
4. **Monitor costs during testing**
5. **Keep test results for comparison**

---

**Last Updated:** February 22, 2026
