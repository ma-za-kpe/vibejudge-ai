"""Bug condition exploration tests for cost tracking fix.

**Validates: Requirements 1.1, 1.2, 1.3, 2.1, 2.2, 2.3, 2.4, 2.5**

This test file contains property-based tests that explore the bug condition:
- Cost recording failures are silent (no exceptions raised)
- Enum values not converted to strings cause DynamoDB type errors
- Insufficient diagnostic logging prevents debugging
- Lambda handler doesn't properly handle cost recording exceptions

CRITICAL: These tests are EXPECTED TO FAIL on unfixed code.
Failure confirms the bug exists. When the fix is implemented, these tests should pass.
"""

from unittest.mock import MagicMock, patch

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from src.models.common import AgentName
from src.services.cost_service import CostService
from src.utils.dynamo import DynamoDBHelper

# ============================================================
# PROPERTY 1: Fault Condition - Cost Recording Failures Raise Exceptions
# ============================================================

@given(
    sub_id=st.text(min_size=5, max_size=50, alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd"))),
    agent_name=st.sampled_from([agent.value for agent in AgentName]),
    model_id=st.sampled_from([
        "amazon.nova-micro-v1:0",
        "amazon.nova-lite-v1:0",
        "anthropic.claude-sonnet-4-20250514"
    ]),
    input_tokens=st.integers(min_value=100, max_value=50000),
    output_tokens=st.integers(min_value=50, max_value=10000),
)
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], max_examples=20)
def test_property_cost_recording_failure_raises_exception(
    sub_id: str,
    agent_name: str,
    model_id: str,
    input_tokens: int,
    output_tokens: int,
):
    """Property 1: When db.put_cost_record() returns False, record_agent_cost() SHALL raise ValueError.
    
    **Validates: Requirements 2.1, 2.2**
    
    This test is EXPECTED TO FAIL on unfixed code because the current implementation
    raises ValueError correctly, but the Lambda handler catches and swallows the exception.
    
    The bug is that cost recording failures are silent at the Lambda handler level,
    not at the service level.
    """
    # Arrange: Mock DynamoDB to simulate write failure
    mock_db = MagicMock(spec=DynamoDBHelper)
    mock_db.put_cost_record.return_value = False  # Simulate DynamoDB write failure

    cost_service = CostService(db=mock_db)

    # Act & Assert: Verify that ValueError is raised with descriptive message
    with pytest.raises(ValueError) as exc_info:
        cost_service.record_agent_cost(
            sub_id=sub_id,
            agent_name=agent_name,
            model_id=model_id,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )

    # Verify error message includes context
    error_msg = str(exc_info.value)
    assert sub_id in error_msg, f"Error message should include sub_id: {error_msg}"
    assert agent_name in error_msg, f"Error message should include agent_name: {error_msg}"


# ============================================================
# PROPERTY 2: Fault Condition - Enum Conversion
# ============================================================

@given(
    sub_id=st.text(min_size=5, max_size=50, alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd"))),
    agent_name_enum=st.sampled_from(list(AgentName)),
    model_id=st.sampled_from([
        "amazon.nova-micro-v1:0",
        "amazon.nova-lite-v1:0",
        "anthropic.claude-sonnet-4-20250514"
    ]),
    input_tokens=st.integers(min_value=100, max_value=50000),
    output_tokens=st.integers(min_value=50, max_value=10000),
)
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], max_examples=20)
def test_property_enum_agent_name_conversion(
    sub_id: str,
    agent_name_enum: AgentName,
    model_id: str,
    input_tokens: int,
    output_tokens: int,
):
    """Property 2: When AgentName enum is passed, it SHALL be converted to string before DynamoDB write.
    
    **Validates: Requirements 2.3**
    
    This test is EXPECTED TO FAIL on unfixed code because the current implementation
    in cost_service.py does not convert enum values to strings before creating the record dict.
    """
    # Arrange: Mock DynamoDB to capture what's being written
    mock_db = MagicMock(spec=DynamoDBHelper)
    mock_db.put_cost_record.return_value = True

    cost_service = CostService(db=mock_db)

    # Act: Call with enum (this is what happens in lambda_handler.py)
    result = cost_service.record_agent_cost(
        sub_id=sub_id,
        agent_name=agent_name_enum,  # Pass enum directly
        model_id=model_id,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )

    # Assert: Verify the record dict has string agent_name, not enum
    assert mock_db.put_cost_record.called, "put_cost_record should be called"
    call_args = mock_db.put_cost_record.call_args[0][0]

    # The agent_name in the record should be a string
    assert isinstance(call_args["agent_name"], str), \
        f"agent_name should be string, got {type(call_args['agent_name'])}"
    assert call_args["agent_name"] == agent_name_enum.value, \
        f"agent_name should be '{agent_name_enum.value}', got '{call_args['agent_name']}'"


# ============================================================
# PROPERTY 3: Fault Condition - Diagnostic Logging
# ============================================================

@given(
    sub_id=st.text(min_size=5, max_size=50, alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd"))),
    agent_name=st.sampled_from([agent.value for agent in AgentName]),
    model_id=st.sampled_from([
        "amazon.nova-micro-v1:0",
        "amazon.nova-lite-v1:0",
        "anthropic.claude-sonnet-4-20250514"
    ]),
    input_tokens=st.integers(min_value=100, max_value=50000),
    output_tokens=st.integers(min_value=50, max_value=10000),
)
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], max_examples=20)
def test_property_diagnostic_logging_before_write(
    sub_id: str,
    agent_name: str,
    model_id: str,
    input_tokens: int,
    output_tokens: int,
):
    """Property 3: Diagnostic logging SHALL include PK, SK, cost, tokens, and model ID before write attempts.
    
    **Validates: Requirements 2.2**
    
    This test verifies that sufficient diagnostic information is logged before attempting
    the DynamoDB write, which is critical for debugging failures.
    """
    # Arrange: Mock DynamoDB and capture logging
    mock_db = MagicMock(spec=DynamoDBHelper)
    mock_db.put_cost_record.return_value = True

    cost_service = CostService(db=mock_db)

    # Act: Call record_agent_cost
    with patch('src.services.cost_service.logger') as mock_logger:
        result = cost_service.record_agent_cost(
            sub_id=sub_id,
            agent_name=agent_name,
            model_id=model_id,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )

        # Assert: Verify diagnostic logging includes required fields
        # Look for the "cost_record_saving" log call
        log_calls = [call for call in mock_logger.info.call_args_list
                     if len(call[0]) > 0 and call[0][0] == "cost_record_saving"]

        assert len(log_calls) > 0, "Should log 'cost_record_saving' before write attempt"

        # Check that the log includes required diagnostic fields
        log_kwargs = log_calls[0][1]
        assert "pk" in log_kwargs, "Diagnostic log should include PK"
        assert "sk" in log_kwargs, "Diagnostic log should include SK"
        assert "cost_usd" in log_kwargs, "Diagnostic log should include cost"
        assert "tokens" in log_kwargs, "Diagnostic log should include tokens"
        assert log_kwargs["sub_id"] == sub_id, "Diagnostic log should include sub_id"
        assert log_kwargs["agent"] == agent_name, "Diagnostic log should include agent name"


# ============================================================
# PROPERTY 4: Fault Condition - Lambda Handler Exception Handling
# ============================================================

def test_lambda_handler_cost_recording_exception_handling():
    """Property 4: Lambda handler SHALL catch cost recording exceptions and continue batch processing.
    
    **Validates: Requirements 2.4, 2.5**
    
    This test verifies that when cost recording fails in the Lambda handler,
    the exception is caught, logged with full context, and batch processing continues.
    
    This test is EXPECTED TO FAIL on unfixed code because the current implementation
    catches exceptions but doesn't log sufficient diagnostic information (missing model_id, tokens, cost).
    """
    from src.analysis.lambda_handler import handler
    from src.models.costs import CostRecord

    # Arrange: Create a mock event with a submission
    event = {
        "job_id": "JOB123",
        "hack_id": "HACK123",
        "submission_ids": ["SUB123"],
    }

    # Mock all the services and dependencies
    with patch('src.analysis.lambda_handler.DynamoDBHelper') as mock_db_class, \
         patch('src.analysis.lambda_handler.HackathonService') as mock_hack_service_class, \
         patch('src.analysis.lambda_handler.SubmissionService') as mock_sub_service_class, \
         patch('src.analysis.lambda_handler.AnalysisService') as mock_analysis_service_class, \
         patch('src.analysis.lambda_handler.CostService') as mock_cost_service_class, \
         patch('src.analysis.lambda_handler.analyze_single_submission') as mock_analyze, \
         patch('src.analysis.lambda_handler.logger') as mock_logger:

        # Setup mocks
        mock_db = MagicMock()
        mock_db_class.return_value = mock_db

        mock_hackathon = MagicMock()
        mock_hackathon.name = "Test Hackathon"
        mock_hackathon.agents_enabled = ["bug_hunter"]
        mock_hackathon.rubric = MagicMock()
        mock_hackathon.ai_policy_mode = MagicMock()
        mock_hackathon.ai_policy_mode.value = "full_vibe"

        mock_hack_service = MagicMock()
        mock_hack_service.get_hackathon.return_value = mock_hackathon
        mock_hack_service_class.return_value = mock_hack_service

        mock_submission = MagicMock()
        mock_submission.sub_id = "SUB123"
        mock_submission.repo_url = "https://github.com/test/repo"
        mock_submission.team_name = "Test Team"

        mock_sub_service = MagicMock()
        mock_sub_service.get_submission.return_value = mock_submission
        mock_sub_service_class.return_value = mock_sub_service

        mock_analysis_service = MagicMock()
        mock_analysis_service_class.return_value = mock_analysis_service

        # Mock cost service to raise exception
        mock_cost_service = MagicMock()
        mock_cost_service.record_agent_cost.side_effect = ValueError("DynamoDB write failed")
        mock_cost_service_class.return_value = mock_cost_service

        # Mock analyze_single_submission to return success with cost records
        mock_cost_record = MagicMock(spec=CostRecord)
        mock_cost_record.agent_name = AgentName.BUG_HUNTER
        mock_cost_record.model_id = "amazon.nova-lite-v1:0"
        mock_cost_record.input_tokens = 1000
        mock_cost_record.output_tokens = 500
        mock_cost_record.total_tokens = 1500

        mock_analyze.return_value = {
            "success": True,
            "overall_score": 8.5,
            "dimension_scores": {"Code Quality": 8.5},
            "weighted_scores": {},
            "recommendation": "solid_submission",
            "confidence": 0.9,
            "agent_scores": {},
            "strengths": [],
            "weaknesses": [],
            "repo_meta": {},
            "cost": 0.00018,
            "tokens": 1500,
            "duration_ms": 5000,
            "cost_records": [mock_cost_record],
        }

        # Act: Call the handler
        result = handler(event, {})

        # Assert: Verify the handler completed successfully despite cost recording failure
        assert result["statusCode"] == 200, "Handler should complete successfully"

        # Verify that cost recording exception was logged with diagnostic information
        error_log_calls = [call for call in mock_logger.error.call_args_list
                          if len(call[0]) > 0 and call[0][0] == "cost_recording_failed"]

        assert len(error_log_calls) > 0, "Should log 'cost_recording_failed' when exception occurs"

        # Check that the error log includes ALL required diagnostic fields
        error_log_kwargs = error_log_calls[0][1]
        assert "sub_id" in error_log_kwargs, "Error log should include sub_id"
        assert "agent" in error_log_kwargs, "Error log should include agent name"
        assert "error" in error_log_kwargs, "Error log should include error message"

        # THIS IS THE BUG: These fields are MISSING in the current implementation
        assert "model" in error_log_kwargs or "model_id" in error_log_kwargs, \
            "Error log should include model_id for debugging"
        assert "tokens" in error_log_kwargs or "input_tokens" in error_log_kwargs, \
            "Error log should include token counts for debugging"
        assert "cost" in error_log_kwargs or "cost_usd" in error_log_kwargs, \
            "Error log should include cost amount for debugging"

        # Verify that submission was still marked as complete (cost tracking is non-critical)
        assert mock_sub_service.update_submission_with_scores.called, \
            "Submission should be updated with scores despite cost recording failure"


# ============================================================
# UNIT TESTS: Specific Bug Scenarios
# ============================================================

def test_cost_recording_failure_with_false_return():
    """Unit test: Verify ValueError is raised when put_cost_record returns False.
    
    **Validates: Requirements 2.1**
    """
    # Arrange
    mock_db = MagicMock(spec=DynamoDBHelper)
    mock_db.put_cost_record.return_value = False

    cost_service = CostService(db=mock_db)

    # Act & Assert
    with pytest.raises(ValueError) as exc_info:
        cost_service.record_agent_cost(
            sub_id="SUB123",
            agent_name="bug_hunter",
            model_id="amazon.nova-lite-v1:0",
            input_tokens=1000,
            output_tokens=500,
        )

    assert "SUB123" in str(exc_info.value)
    assert "bug_hunter" in str(exc_info.value)


def test_enum_agent_name_not_converted():
    """Unit test: Verify that passing AgentName enum causes issues without conversion.
    
    **Validates: Requirements 2.3**
    
    This test is EXPECTED TO FAIL on unfixed code because the enum is not converted to string.
    """
    # Arrange
    mock_db = MagicMock(spec=DynamoDBHelper)
    mock_db.put_cost_record.return_value = True

    cost_service = CostService(db=mock_db)

    # Act: Pass enum directly (this is what happens in lambda_handler)
    result = cost_service.record_agent_cost(
        sub_id="SUB123",
        agent_name=AgentName.BUG_HUNTER,  # Pass enum, not string
        model_id="amazon.nova-lite-v1:0",
        input_tokens=1000,
        output_tokens=500,
    )

    # Assert: The record should have string agent_name
    call_args = mock_db.put_cost_record.call_args[0][0]
    assert isinstance(call_args["agent_name"], str), \
        f"agent_name should be string, got {type(call_args['agent_name'])}"
    assert call_args["agent_name"] == "bug_hunter"


def test_insufficient_diagnostic_logging():
    """Unit test: Verify diagnostic logging includes all required fields.
    
    **Validates: Requirements 2.2**
    """
    # Arrange
    mock_db = MagicMock(spec=DynamoDBHelper)
    mock_db.put_cost_record.return_value = False  # Simulate failure

    cost_service = CostService(db=mock_db)

    # Act & Assert
    with patch('src.services.cost_service.logger') as mock_logger:
        try:
            cost_service.record_agent_cost(
                sub_id="SUB123",
                agent_name="bug_hunter",
                model_id="amazon.nova-lite-v1:0",
                input_tokens=1000,
                output_tokens=500,
            )
        except ValueError:
            pass  # Expected

        # Verify diagnostic logging before write attempt
        saving_logs = [call for call in mock_logger.info.call_args_list
                      if len(call[0]) > 0 and call[0][0] == "cost_record_saving"]

        assert len(saving_logs) > 0, "Should log before write attempt"

        log_kwargs = saving_logs[0][1]
        assert "pk" in log_kwargs
        assert "sk" in log_kwargs
        assert "cost_usd" in log_kwargs
        assert "tokens" in log_kwargs
