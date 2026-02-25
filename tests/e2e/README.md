# End-to-End Production Tests

## Overview

This directory contains E2E tests that validate the **live production API** at:
```
https://2nu0j4n648.execute-api.us-east-1.amazonaws.com/dev
```

## Purpose

These tests validate the complete user flow and specifically check for **deployment gaps** where features work locally but fail in production.

## Critical Validations

### Human-Centric Intelligence Features (97% complete locally)
- ✅ `team_dynamics` field populated in scorecard
- ✅ `strategy_analysis` field populated in scorecard  
- ✅ `actionable_feedback` array populated in scorecard
- ✅ `/individual-scorecards` endpoint accessible
- ✅ `/intelligence` dashboard endpoint accessible

### Core Platform Features
- ✅ Organizer registration
- ✅ Hackathon creation with rubric
- ✅ Batch submission
- ✅ Analysis triggering
- ✅ Status polling
- ✅ Cost tracking (42% reduction target)

## Running the Tests

### Prerequisites

```bash
# Install httpx if not already installed
pip install httpx pytest
```

### Run All E2E Tests

```bash
# From project root
pytest tests/e2e/test_live_production.py -v -s

# Or run directly
python tests/e2e/test_live_production.py
```

### Run Specific Test

```bash
# Test only scorecard validation
pytest tests/e2e/test_live_production.py::TestLiveProduction::test_03_validate_scorecard_human_centric_fields -v -s

# Test only individual scorecards endpoint
pytest tests/e2e/test_live_production.py::TestLiveProduction::test_04_validate_individual_scorecards_endpoint -v -s
```

## Test Flow

1. **Register Organizer** → Get API key
2. **Create Hackathon** → Get hack_id
3. **Submit 2 Repos** → Get submission_ids
   - `https://github.com/ma-za-kpe/vibejudge-ai` (VibeJudge itself)
   - `https://github.com/pallets/flask` (Flask framework)
4. **Trigger Analysis** → Start batch processing
5. **Poll Status** → Wait max 10 minutes for completion
6. **Validate Scorecard** → Check human-centric intelligence fields
7. **Validate Individual Scorecards** → Check endpoint exists
8. **Validate Intelligence Dashboard** → Check endpoint exists
9. **Validate Cost Tracking** → Check 42% reduction target

## Expected Failures (Deployment Gaps)

If human-centric intelligence features are NOT deployed, you'll see:

```
❌ DEPLOYMENT GAP: team_dynamics is null!
   TeamAnalyzer results not being stored in DynamoDB.

❌ DEPLOYMENT GAP: strategy_analysis is null!
   StrategyDetector results not being stored in DynamoDB.

❌ DEPLOYMENT GAP: actionable_feedback is empty!
   BrandVoiceTransformer results not being stored in DynamoDB.

❌ DEPLOYMENT GAP: /individual-scorecards endpoint not found!
   Route may not be registered in production.

❌ DEPLOYMENT GAP: /intelligence endpoint not found!
   Route may not be registered in production.
```

## Debugging Production Issues

### Check CloudWatch Logs

```bash
# API Lambda logs
aws logs tail /aws/lambda/VibeJudgeApiFunction --follow

# Analyzer Lambda logs
aws logs tail /aws/lambda/VibeJudgeAnalyzerFunction --follow
```

### Check DynamoDB Records

```bash
# Get submission record
aws dynamodb get-item \
  --table-name VibeJudgeTable \
  --key '{"PK": {"S": "SUB#<sub_id>"}, "SK": {"S": "META"}}'

# Check if team_dynamics, strategy_analysis, actionable_feedback fields exist
```

### Common Issues

1. **Orchestrator not calling new analyzers**
   - Check `src/analysis/orchestrator.py` integration
   - Verify TeamAnalyzer, StrategyDetector, BrandVoiceTransformer are imported

2. **Results not being stored in DynamoDB**
   - Check `src/services/submission_service.py` update logic
   - Verify fields are being serialized correctly

3. **Routes not registered**
   - Check `src/api/routes/submissions.py` for new endpoints
   - Verify routes are included in `src/api/main.py`

4. **Lambda deployment out of sync**
   - Run `sam build && sam deploy` to redeploy
   - Check deployment logs for errors

## Success Criteria

All tests should pass with:
- ✅ All submissions analyzed within 10 minutes
- ✅ `team_dynamics` populated with workload distribution and grade
- ✅ `strategy_analysis` populated with test strategy and maturity level
- ✅ `actionable_feedback` contains at least 1 item with effort estimates
- ✅ Individual scorecards endpoint returns contributor data
- ✅ Intelligence dashboard endpoint returns hiring intelligence
- ✅ Cost reduction >= 30% (target: 42%)

## Next Steps After Test Failure

1. **Identify the gap** - Which assertion failed?
2. **Check local tests** - Do unit/integration tests pass locally?
3. **Review orchestrator** - Is the new analyzer being called?
4. **Check DynamoDB schema** - Are new fields being stored?
5. **Verify deployment** - Is the latest code deployed to Lambda?
6. **Check CloudWatch** - Any errors in Lambda logs?

## Contact

For issues with these tests, check:
- `.kiro/specs/human-centric-intelligence/` - Feature spec
- `PROJECT_PROGRESS.md` - Implementation status
- CloudWatch Logs - Runtime errors
