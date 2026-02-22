# Bugfix Requirements Document

## Introduction

Cost tracking data is not being persisted to DynamoDB after analysis completes, undermining a core value proposition of VibeJudge AI: cost transparency. The analysis runs successfully and returns cost data in the response, but when querying costs later via the API, no cost records are found in the database. This bug prevents organizers from seeing exactly what they're paying per agent, which is a critical feature for budget-conscious hackathon organizers.

The root cause is insufficient error handling in the cost tracking service. When DynamoDB write operations fail, the system only logs an error and continues execution, allowing the analysis to complete "successfully" even though cost data was never persisted.

## Bug Analysis

### Current Behavior (Defect)

1.1 WHEN `db.put_cost_record()` fails in `cost_service.py` THEN the system logs an error but continues execution without raising an exception

1.2 WHEN cost record writes fail silently THEN the analysis Lambda completes with status "success" despite missing cost data

1.3 WHEN `CostRecord` objects with `AgentName` enum values are passed to `record_agent_cost()` THEN the system may fail to convert enums to strings, causing DynamoDB write failures

1.4 WHEN cost recording fails in `lambda_handler.py` THEN there is insufficient diagnostic logging to identify which agent or submission caused the failure

### Expected Behavior (Correct)

2.1 WHEN `db.put_cost_record()` fails in `cost_service.py` THEN the system SHALL raise a `ValueError` with a descriptive error message including submission ID and agent name

2.2 WHEN cost record writes fail THEN the system SHALL log detailed diagnostic information including PK, SK, cost amount, and token counts before the write attempt

2.3 WHEN `CostRecord` objects with `AgentName` enum values are passed to `record_agent_cost()` THEN the system SHALL properly convert enum values to strings before processing

2.4 WHEN cost recording fails in `lambda_handler.py` THEN the system SHALL catch the exception, log the error with full context (submission ID, agent name, error details), and continue processing other submissions without crashing the entire batch

2.5 WHEN cost recording fails for a submission THEN the system SHALL still mark the submission analysis as complete (cost tracking is non-critical) but SHALL log the cost recording failure

### Unchanged Behavior (Regression Prevention)

3.1 WHEN `db.put_cost_record()` succeeds THEN the system SHALL CONTINUE TO save cost records to DynamoDB with PK=`SUB#{sub_id}` and SK=`COST#{agent_name}`

3.2 WHEN cost records are successfully written THEN the system SHALL CONTINUE TO log success events with cost and token information

3.3 WHEN all cost records are successfully written for a submission THEN the system SHALL CONTINUE TO complete the analysis successfully and update submission status to "completed"

3.4 WHEN querying costs via GET `/hackathons/{hack_id}/costs` THEN the system SHALL CONTINUE TO return aggregated cost data by agent and by model

3.5 WHEN multiple submissions are analyzed in a batch THEN the system SHALL CONTINUE TO process all submissions independently, with one submission's cost recording failure not affecting others

3.6 WHEN hackathon cost summaries are updated THEN the system SHALL CONTINUE TO aggregate costs from all submissions correctly
