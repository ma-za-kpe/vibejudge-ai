"""Preservation property tests for cost tracking fix.

**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6**

This test file contains property-based tests that verify successful cost recording
behavior remains unchanged after the fix is implemented.

IMPORTANT: These tests are EXPECTED TO PASS on unfixed code.
They capture the baseline behavior that must be preserved.
"""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from src.models.common import AgentName
from src.services.cost_service import CostService
from src.utils.dynamo import DynamoDBHelper

# ============================================================
# PROPERTY 4: Preservation - Successful Cost Recording
# ============================================================


@given(
    sub_id=st.text(
        min_size=5,
        max_size=50,
        alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd")),
    ),
    agent_name=st.sampled_from([agent.value for agent in AgentName]),
    model_id=st.sampled_from(
        [
            "amazon.nova-micro-v1:0",
            "amazon.nova-lite-v1:0",
            "anthropic.claude-sonnet-4-20250514",
        ]
    ),
    input_tokens=st.integers(min_value=100, max_value=50000),
    output_tokens=st.integers(min_value=50, max_value=10000),
)
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], max_examples=30)
def test_property_successful_cost_recording_preserved(
    sub_id: str,
    agent_name: str,
    model_id: str,
    input_tokens: int,
    output_tokens: int,
):
    """Property 4.1: Successful cost recording produces same record dict and logging.

    **Validates: Requirements 3.1, 3.2**

    For all successful cost writes (where put_cost_record() returns True),
    verify the same record dict structure and logging behavior.

    This test is EXPECTED TO PASS on unfixed code - it captures baseline behavior.
    """
    # Arrange: Mock DynamoDB to simulate successful write
    mock_db = MagicMock(spec=DynamoDBHelper)
    mock_db.put_cost_record.return_value = True  # Successful write

    cost_service = CostService(db=mock_db)

    # Act: Record cost with successful write
    with patch("src.services.cost_service.logger") as mock_logger:
        result = cost_service.record_agent_cost(
            sub_id=sub_id,
            agent_name=agent_name,
            model_id=model_id,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )

        # Assert: Verify record structure is preserved
        assert isinstance(result, dict), "Should return dict"
        assert result["PK"] == f"SUB#{sub_id}", "PK format preserved"
        assert result["SK"] == f"COST#{agent_name}", "SK format preserved"
        assert result["entity_type"] == "COST", "Entity type preserved"
        assert result["sub_id"] == sub_id, "sub_id preserved"
        assert result["agent_name"] == agent_name, "agent_name preserved"
        assert result["model_id"] == model_id, "model_id preserved"
        assert result["input_tokens"] == input_tokens, "input_tokens preserved"
        assert result["output_tokens"] == output_tokens, "output_tokens preserved"
        assert result["total_tokens"] == input_tokens + output_tokens, "total_tokens preserved"
        assert "input_cost_usd" in result, "input_cost_usd preserved"
        assert "output_cost_usd" in result, "output_cost_usd preserved"
        assert "total_cost_usd" in result, "total_cost_usd preserved"
        assert "timestamp" in result, "timestamp preserved"

        # Verify logging behavior is preserved
        # Should log "cost_record_saving" before write
        saving_logs = [
            call
            for call in mock_logger.info.call_args_list
            if len(call[0]) > 0 and call[0][0] == "cost_record_saving"
        ]
        assert len(saving_logs) > 0, "Should log before write attempt"

        # Should log "cost_recorded" after successful write
        recorded_logs = [
            call
            for call in mock_logger.info.call_args_list
            if len(call[0]) > 0 and call[0][0] == "cost_recorded"
        ]
        assert len(recorded_logs) > 0, "Should log after successful write"

        # Verify put_cost_record was called with correct record
        assert mock_db.put_cost_record.called, "Should call put_cost_record"
        call_args = mock_db.put_cost_record.call_args[0][0]
        assert call_args["PK"] == f"SUB#{sub_id}", "PK passed correctly"
        assert call_args["SK"] == f"COST#{agent_name}", "SK passed correctly"


@given(
    sub_id=st.text(
        min_size=5,
        max_size=50,
        alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd")),
    ),
    agent_names=st.lists(
        st.sampled_from([agent.value for agent in AgentName]),
        min_size=1,
        max_size=4,
        unique=True,
    ),
    model_id=st.sampled_from(
        [
            "amazon.nova-micro-v1:0",
            "amazon.nova-lite-v1:0",
            "anthropic.claude-sonnet-4-20250514",
        ]
    ),
    input_tokens=st.integers(min_value=100, max_value=50000),
    output_tokens=st.integers(min_value=50, max_value=10000),
)
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], max_examples=20)
def test_property_cost_aggregation_preserved(
    sub_id: str,
    agent_names: list[str],
    model_id: str,
    input_tokens: int,
    output_tokens: int,
):
    """Property 4.2: Cost aggregation produces correct totals.

    **Validates: Requirements 3.4**

    For all cost aggregation queries, verify the same aggregated results.

    This test is EXPECTED TO PASS on unfixed code - it captures baseline behavior.
    """
    # Arrange: Mock DynamoDB to return cost records
    mock_db = MagicMock(spec=DynamoDBHelper)

    # Calculate expected costs
    from src.constants import MODEL_RATES

    rates = MODEL_RATES.get(model_id, {"input": 0, "output": 0})
    input_cost = input_tokens * rates["input"]
    output_cost = output_tokens * rates["output"]
    total_cost_per_agent = input_cost + output_cost

    # Create mock cost records for each agent
    mock_records = []
    for agent_name in agent_names:
        mock_records.append(
            {
                "PK": f"SUB#{sub_id}",
                "SK": f"COST#{agent_name}",
                "entity_type": "COST",
                "sub_id": sub_id,
                "agent_name": agent_name,
                "model_id": model_id,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens,
                "input_cost_usd": input_cost,
                "output_cost_usd": output_cost,
                "total_cost_usd": total_cost_per_agent,
                "timestamp": datetime.now(UTC).isoformat(),
            }
        )

    mock_db.get_submission_costs.return_value = mock_records

    cost_service = CostService(db=mock_db)

    # Act: Get submission costs
    result = cost_service.get_submission_costs(sub_id)

    # Assert: Verify aggregation is correct
    expected_total_cost = total_cost_per_agent * len(agent_names)
    expected_total_tokens = (input_tokens + output_tokens) * len(agent_names)

    assert result["sub_id"] == sub_id, "sub_id preserved"
    assert abs(result["total_cost_usd"] - expected_total_cost) < 0.0001, (
        f"Total cost aggregation preserved: expected {expected_total_cost}, got {result['total_cost_usd']}"
    )
    assert result["total_tokens"] == expected_total_tokens, (
        f"Total tokens aggregation preserved: expected {expected_total_tokens}, got {result['total_tokens']}"
    )
    assert len(result["agent_costs"]) == len(agent_names), "Agent costs count preserved"


@given(
    hack_id=st.text(
        min_size=5,
        max_size=50,
        alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd")),
    ),
    submission_count=st.integers(min_value=1, max_value=10),
    agent_names=st.lists(
        st.sampled_from([agent.value for agent in AgentName]),
        min_size=1,
        max_size=4,
        unique=True,
    ),
    model_id=st.sampled_from(
        [
            "amazon.nova-micro-v1:0",
            "amazon.nova-lite-v1:0",
            "anthropic.claude-sonnet-4-20250514",
        ]
    ),
    input_tokens=st.integers(min_value=100, max_value=10000),
    output_tokens=st.integers(min_value=50, max_value=5000),
)
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], max_examples=15)
def test_property_hackathon_cost_summary_preserved(
    hack_id: str,
    submission_count: int,
    agent_names: list[str],
    model_id: str,
    input_tokens: int,
    output_tokens: int,
):
    """Property 4.3: Hackathon cost summary aggregation is correct.

    **Validates: Requirements 3.6**

    For all hackathon cost summaries, verify the same aggregation totals.

    This test is EXPECTED TO PASS on unfixed code - it captures baseline behavior.
    """
    # Arrange: Mock DynamoDB to return submissions and cost records
    mock_db = MagicMock(spec=DynamoDBHelper)

    # Calculate expected costs
    from src.constants import MODEL_RATES

    rates = MODEL_RATES.get(model_id, {"input": 0, "output": 0})
    input_cost = input_tokens * rates["input"]
    output_cost = output_tokens * rates["output"]
    total_cost_per_agent = input_cost + output_cost

    # Create mock submissions
    mock_submissions = []
    for i in range(submission_count):
        mock_submissions.append(
            {
                "sub_id": f"SUB{i}",
                "hack_id": hack_id,
            }
        )

    mock_db.list_submissions.return_value = mock_submissions

    # Create mock cost records for each submission
    def get_submission_costs_side_effect(sub_id: str):
        records = []
        for agent_name in agent_names:
            records.append(
                {
                    "PK": f"SUB#{sub_id}",
                    "SK": f"COST#{agent_name}",
                    "entity_type": "COST",
                    "sub_id": sub_id,
                    "agent_name": agent_name,
                    "model_id": model_id,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "total_tokens": input_tokens + output_tokens,
                    "input_cost_usd": input_cost,
                    "output_cost_usd": output_cost,
                    "total_cost_usd": total_cost_per_agent,
                    "timestamp": datetime.now(UTC).isoformat(),
                }
            )
        return records

    mock_db.get_submission_costs.side_effect = get_submission_costs_side_effect

    cost_service = CostService(db=mock_db)

    # Act: Get hackathon costs
    result = cost_service.get_hackathon_costs(hack_id)

    # Assert: Verify aggregation is correct
    expected_total_cost = total_cost_per_agent * len(agent_names) * submission_count
    expected_total_tokens = (input_tokens + output_tokens) * len(agent_names) * submission_count
    expected_avg_cost = expected_total_cost / submission_count

    assert result["hack_id"] == hack_id, "hack_id preserved"
    assert abs(result["total_cost_usd"] - expected_total_cost) < 0.0001, (
        f"Total cost aggregation preserved: expected {expected_total_cost}, got {result['total_cost_usd']}"
    )
    assert result["total_tokens"] == expected_total_tokens, (
        f"Total tokens aggregation preserved: expected {expected_total_tokens}, got {result['total_tokens']}"
    )
    assert result["submission_count"] == submission_count, "Submission count preserved"
    assert abs(result["average_cost_per_submission"] - expected_avg_cost) < 0.0001, (
        f"Average cost preserved: expected {expected_avg_cost}, got {result['average_cost_per_submission']}"
    )

    # Verify agent breakdown
    assert len(result["agent_breakdown"]) == len(agent_names), "Agent breakdown count preserved"
    for agent_breakdown in result["agent_breakdown"]:
        expected_agent_cost = total_cost_per_agent * submission_count
        expected_agent_tokens = (input_tokens + output_tokens) * submission_count
        assert abs(agent_breakdown["total_cost_usd"] - expected_agent_cost) < 0.0001, (
            f"Agent cost aggregation preserved for {agent_breakdown['agent_name']}"
        )
        assert agent_breakdown["total_tokens"] == expected_agent_tokens, (
            f"Agent tokens aggregation preserved for {agent_breakdown['agent_name']}"
        )
        assert agent_breakdown["execution_count"] == submission_count, (
            f"Agent execution count preserved for {agent_breakdown['agent_name']}"
        )


# ============================================================
# PROPERTY 5: Preservation - Batch Processing Independence
# ============================================================


def test_property_batch_processing_independence_preserved():
    """Property 4.4: Batch processing continues independently when one submission's cost recording fails.

    **Validates: Requirements 3.5**

    For all batch processing scenarios, verify the same independence behavior.

    This test is EXPECTED TO PASS on unfixed code - it captures baseline behavior.
    """
    from src.analysis.lambda_handler import handler
    from src.models.costs import CostRecord

    # Arrange: Create a mock event with multiple submissions
    event = {
        "job_id": "JOB123",
        "hack_id": "HACK123",
        "submission_ids": ["SUB1", "SUB2", "SUB3"],
    }

    # Mock all the services and dependencies
    with (
        patch("src.analysis.lambda_handler.DynamoDBHelper") as mock_db_class,
        patch("src.analysis.lambda_handler.HackathonService") as mock_hack_service_class,
        patch("src.analysis.lambda_handler.SubmissionService") as mock_sub_service_class,
        patch("src.analysis.lambda_handler.AnalysisService") as mock_analysis_service_class,
        patch("src.analysis.lambda_handler.CostService") as mock_cost_service_class,
        patch("src.analysis.lambda_handler.analyze_single_submission") as mock_analyze,
        patch("src.analysis.lambda_handler.logger") as mock_logger,
        patch(
            "src.constants.MODEL_RATES",
            {"amazon.nova-lite-v1:0": {"input": 0.00000006, "output": 0.00000024}},
        ),
    ):
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

        # Create mock submissions
        mock_submissions = {}
        for sub_id in event["submission_ids"]:
            mock_sub = MagicMock()
            mock_sub.sub_id = sub_id
            mock_sub.repo_url = f"https://github.com/test/{sub_id}"
            mock_sub.team_name = f"Team {sub_id}"
            mock_submissions[sub_id] = mock_sub

        mock_sub_service = MagicMock()
        mock_sub_service.get_submission.side_effect = lambda sub_id: mock_submissions.get(sub_id)
        mock_sub_service_class.return_value = mock_sub_service

        mock_analysis_service = MagicMock()
        mock_analysis_service_class.return_value = mock_analysis_service

        # Mock cost service to fail for SUB1 only
        mock_cost_service = MagicMock()

        def record_cost_side_effect(sub_id, **kwargs):
            if sub_id == "SUB1":
                raise ValueError("DynamoDB write failed for SUB1")
            return {"PK": f"SUB#{sub_id}", "SK": "COST#bug_hunter"}

        mock_cost_service.record_agent_cost.side_effect = record_cost_side_effect
        mock_cost_service_class.return_value = mock_cost_service

        # Mock analyze_single_submission to return success for all
        def analyze_side_effect(submission, hackathon, db):
            mock_cost_record = MagicMock(spec=CostRecord)
            mock_cost_record.agent_name = AgentName.BUG_HUNTER
            mock_cost_record.model_id = "amazon.nova-lite-v1:0"
            mock_cost_record.input_tokens = 1000
            mock_cost_record.output_tokens = 500
            mock_cost_record.total_tokens = 1500

            return {
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

        mock_analyze.side_effect = analyze_side_effect

        # Act: Call the handler
        result = handler(event, {})

        # Assert: Verify batch processing independence is preserved
        assert result["statusCode"] == 200, "Handler should complete successfully"

        # Verify all 3 submissions were processed (analyze_single_submission called 3 times)
        assert mock_analyze.call_count == 3, (
            "All submissions should be analyzed despite cost recording failure"
        )

        # Verify all 3 submissions were updated with scores
        assert mock_sub_service.update_submission_with_scores.call_count == 3, (
            "All submissions should be updated despite cost recording failure"
        )

        # Verify cost recording was attempted for all 3 submissions
        assert mock_cost_service.record_agent_cost.call_count == 3, (
            "Cost recording should be attempted for all submissions"
        )

        # Verify error was logged for SUB1 but processing continued
        error_logs = [
            call
            for call in mock_logger.error.call_args_list
            if len(call[0]) > 0 and call[0][0] == "cost_recording_failed"
        ]
        assert len(error_logs) == 1, "Should log cost recording failure for SUB1 only"
        assert error_logs[0][1]["sub_id"] == "SUB1", "Error log should be for SUB1"

        # Verify job was marked as completed
        completed_calls = [
            call
            for call in mock_analysis_service.update_job_status.call_args_list
            if call[1].get("status") == "completed"
        ]
        assert len(completed_calls) > 0, "Job should be marked as completed"


# ============================================================
# UNIT TESTS: Specific Preservation Scenarios
# ============================================================


def test_successful_cost_recording_returns_dict():
    """Unit test: Verify successful cost recording returns dict with correct structure.

    **Validates: Requirements 3.1, 3.2**
    """
    # Arrange
    mock_db = MagicMock(spec=DynamoDBHelper)
    mock_db.put_cost_record.return_value = True

    cost_service = CostService(db=mock_db)

    # Act
    result = cost_service.record_agent_cost(
        sub_id="SUB123",
        agent_name="bug_hunter",
        model_id="amazon.nova-lite-v1:0",
        input_tokens=1000,
        output_tokens=500,
    )

    # Assert
    assert isinstance(result, dict), "Should return dict"
    assert result["PK"] == "SUB#SUB123"
    assert result["SK"] == "COST#bug_hunter"
    assert result["entity_type"] == "COST"
    assert result["sub_id"] == "SUB123"
    assert result["agent_name"] == "bug_hunter"
    assert result["model_id"] == "amazon.nova-lite-v1:0"
    assert result["input_tokens"] == 1000
    assert result["output_tokens"] == 500
    assert result["total_tokens"] == 1500


def test_cost_aggregation_multiple_agents():
    """Unit test: Verify cost aggregation works correctly for multiple agents.

    **Validates: Requirements 3.4**
    """
    # Arrange
    mock_db = MagicMock(spec=DynamoDBHelper)

    mock_records = [
        {
            "agent_name": "bug_hunter",
            "total_cost_usd": 0.00018,
            "total_tokens": 1500,
        },
        {
            "agent_name": "performance",
            "total_cost_usd": 0.00024,
            "total_tokens": 2000,
        },
    ]
    mock_db.get_submission_costs.return_value = mock_records

    cost_service = CostService(db=mock_db)

    # Act
    result = cost_service.get_submission_costs("SUB123")

    # Assert
    assert result["sub_id"] == "SUB123"
    assert abs(result["total_cost_usd"] - 0.00042) < 0.0001
    assert result["total_tokens"] == 3500
    assert len(result["agent_costs"]) == 2


def test_hackathon_cost_summary_update():
    """Unit test: Verify hackathon cost summary update works correctly.

    **Validates: Requirements 3.6**
    """
    # Arrange
    mock_db = MagicMock(spec=DynamoDBHelper)

    mock_submissions = [
        {"sub_id": "SUB1", "hack_id": "HACK123"},
        {"sub_id": "SUB2", "hack_id": "HACK123"},
    ]
    mock_db.list_submissions.return_value = mock_submissions

    def get_costs_side_effect(sub_id):
        return [
            {
                "agent_name": "bug_hunter",
                "total_cost_usd": 0.00018,
                "total_tokens": 1500,
            }
        ]

    mock_db.get_submission_costs.side_effect = get_costs_side_effect
    mock_db.put_hackathon_cost_summary.return_value = True

    cost_service = CostService(db=mock_db)

    # Act
    result = cost_service.update_hackathon_cost_summary("HACK123")

    # Assert
    assert result is True
    assert mock_db.put_hackathon_cost_summary.called

    # Verify the summary record structure
    call_args = mock_db.put_hackathon_cost_summary.call_args[0][0]
    assert call_args["PK"] == "HACK#HACK123"
    assert call_args["SK"] == "COST#SUMMARY"
    assert call_args["entity_type"] == "COST_SUMMARY"
    assert call_args["hack_id"] == "HACK123"
    assert abs(call_args["total_cost_usd"] - 0.00036) < 0.0001
    assert call_args["total_tokens"] == 3000
    assert call_args["submission_count"] == 2
