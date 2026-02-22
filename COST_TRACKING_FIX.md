# Cost Tracking Bug Fix

## Issue Summary
Cost tracking was returning empty data (`cost_by_agent: {}`, `cost_by_model: {}`) despite the implementation existing in the codebase.

## Root Cause
The cost tracking data flow had two issues:

1. **Enum Serialization**: The `CostTracker` returns `CostRecord` Pydantic models with `agent_name` as an `AgentName` enum, but the lambda handler wasn't properly converting it to a string before passing to `cost_service.record_agent_cost()`.

2. **Silent Failures**: The `cost_service.record_agent_cost()` method was logging errors but not raising exceptions, making it difficult to detect when cost records failed to save.

## Changes Made

### 1. Lambda Handler (`src/analysis/lambda_handler.py`)
**Lines 133-156**: Improved cost recording with:
- Proper enum-to-string conversion with type hint
- Debug logging before each cost record attempt
- Try-except block to prevent cost recording failures from crashing the entire analysis
- Better error logging with context

```python
# Record costs
for cost_record in result["cost_records"]:
    agent_name_str = "unknown"
    try:
        # Extract agent_name as string (handle both enum and string)
        agent_name_str = (
            cost_record.agent_name.value 
            if hasattr(cost_record.agent_name, 'value') 
            else str(cost_record.agent_name)
        )
        
        logger.debug(
            "recording_cost",
            sub_id=sub_id,
            agent=agent_name_str,
            model=cost_record.model_id,
            tokens=cost_record.total_tokens,
        )
        
        cost_service.record_agent_cost(
            sub_id=sub_id,
            agent_name=agent_name_str,
            model_id=cost_record.model_id,
            input_tokens=cost_record.input_tokens,
            output_tokens=cost_record.output_tokens,
        )
    except Exception as e:
        # Don't fail the entire analysis if cost recording fails
        logger.error(
            "cost_recording_failed",
            sub_id=sub_id,
            agent=agent_name_str,
            error=str(e),
        )
```

### 2. Cost Service (`src/services/cost_service.py`)
**Lines 30-77**: Enhanced error handling:
- Added detailed logging before save attempt (includes PK/SK for debugging)
- Raises `ValueError` on save failure instead of silent logging
- Updated docstring to document the exception
- Better error messages with context

```python
logger.info(
    "cost_record_saving",
    sub_id=sub_id,
    agent=agent_name,
    pk=record["PK"],
    sk=record["SK"],
    cost_usd=total_cost,
    tokens=input_tokens + output_tokens,
)

success = self.db.put_cost_record(record)
if not success:
    error_msg = f"Failed to save cost record for {sub_id}/{agent_name}"
    logger.error(
        "cost_record_failed",
        sub_id=sub_id,
        agent=agent_name,
        error=error_msg,
    )
    raise ValueError(error_msg)
```

## Testing

### Unit Tests
All existing cost tracker tests pass:
```bash
pytest tests/unit/test_cost_tracker.py -v
# Result: 6 passed
```

### Type Checking
No type errors detected:
```bash
# Diagnostics checked for:
# - src/analysis/lambda_handler.py
# - src/services/cost_service.py
# Result: No diagnostics found
```

## Deployment Instructions

1. **Build the updated Lambda functions:**
   ```bash
   sam build
   ```

2. **Deploy to AWS:**
   ```bash
   sam deploy --config-env default
   ```

3. **Test the fix:**
   ```bash
   ./test_deployment.sh
   ```

4. **Verify cost tracking:**
   Check the output for:
   ```json
   {
     "cost_by_agent": {
       "bug_hunter": 0.002,
       "performance": 0.002,
       "innovation": 0.018,
       "ai_detection": 0.001
     },
     "cost_by_model": {
       "amazon.nova-lite-v1:0": 0.004,
       "anthropic.claude-sonnet-4-20250514": 0.018,
       "amazon.nova-micro-v1:0": 0.001
     }
   }
   ```

## Expected Behavior After Fix

1. **Cost records saved**: Each agent execution will save a cost record to DynamoDB with PK=`SUB#{sub_id}` and SK=`COST#{agent_name}`

2. **Detailed logging**: CloudWatch logs will show:
   - `cost_record_saving` - Before each save attempt with PK/SK
   - `cost_recorded` - After successful save
   - `cost_recording_failed` - If save fails (with error details)

3. **Graceful degradation**: If cost recording fails, the analysis continues and completes successfully (cost tracking is non-critical)

4. **API returns data**: GET `/hackathons/{hack_id}/costs` will return populated `cost_by_agent` and `cost_by_model` dictionaries

## Monitoring

After deployment, monitor CloudWatch logs for:
- `cost_record_saving` events (should appear for each agent)
- `cost_recorded` events (confirms successful saves)
- `cost_recording_failed` events (indicates issues)

Search query:
```
fields @timestamp, event, sub_id, agent, cost_usd, error
| filter event in ["cost_record_saving", "cost_recorded", "cost_recording_failed"]
| sort @timestamp desc
```

## Rollback Plan

If issues occur, rollback to previous version:
```bash
aws cloudformation describe-stack-events \
  --stack-name vibejudge-dev \
  --query 'StackEvents[0].PhysicalResourceId'

# Then rollback
sam deploy --config-env default --no-execute-changeset
```

## Related Files
- `src/analysis/lambda_handler.py` (lines 133-156)
- `src/services/cost_service.py` (lines 30-77)
- `src/analysis/cost_tracker.py` (unchanged, working correctly)
- `src/utils/dynamo.py` (unchanged, working correctly)

## Success Criteria
✅ Cost records appear in DynamoDB after analysis
✅ GET `/hackathons/{hack_id}/costs` returns non-empty data
✅ CloudWatch logs show successful cost recording
✅ No analysis failures due to cost tracking
