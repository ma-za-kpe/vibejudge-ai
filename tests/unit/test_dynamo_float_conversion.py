"""Unit tests for DynamoDB float→Decimal conversion.

Critical: These tests ensure float values are never passed to DynamoDB,
preventing TypeError: "Float types are not supported."
"""

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import MagicMock, Mock, patch

import pytest

from src.utils.dynamo import DynamoDBHelper


class TestFloatConversion:
    """Test float→Decimal conversion in all DynamoDB write operations."""

    @pytest.fixture
    def mock_table(self):
        """Mock DynamoDB table."""
        with patch('boto3.resource') as mock_resource:
            mock_table = Mock()
            mock_resource.return_value.Table.return_value = mock_table
            yield mock_table

    @pytest.fixture
    def db(self, mock_table):
        """DynamoDB helper with mocked table."""
        return DynamoDBHelper("test-table")

    def test_serialize_item_converts_float_to_decimal(self, db):
        """Test _serialize_item converts float values to Decimal."""
        item = {
            "score": 67.97,
            "cost": 0.053,
            "percentage": 100.0,
        }

        result = db._serialize_item(item)

        assert isinstance(result["score"], Decimal)
        assert isinstance(result["cost"], Decimal)
        assert isinstance(result["percentage"], Decimal)
        assert result["score"] == Decimal("67.97")
        assert result["cost"] == Decimal("0.053")

    def test_serialize_item_converts_nested_floats(self, db):
        """Test _serialize_item handles nested dictionaries with floats."""
        item = {
            "submission": {
                "overall_score": 67.97,
                "weighted_scores": {
                    "innovation": 8.5,
                    "performance": 7.2,
                },
            }
        }

        result = db._serialize_item(item)

        assert isinstance(result["submission"]["overall_score"], Decimal)
        assert isinstance(result["submission"]["weighted_scores"]["innovation"], Decimal)
        assert isinstance(result["submission"]["weighted_scores"]["performance"], Decimal)

    def test_serialize_item_converts_floats_in_lists(self, db):
        """Test _serialize_item handles lists containing floats."""
        item = {
            "scores": [67.97, 45.3, 89.1],
            "costs": [0.053, 0.041, 0.067],
        }

        result = db._serialize_item(item)

        assert all(isinstance(score, Decimal) for score in result["scores"])
        assert all(isinstance(cost, Decimal) for cost in result["costs"])

    def test_update_submission_status_converts_float_scores(self, db, mock_table):
        """Test update_submission_status converts float scores to Decimal."""
        db.update_submission_status(
            hack_id="HACK123",
            sub_id="SUB456",
            status="completed",
            updated_at=datetime.now(UTC).isoformat(),
            overall_score=67.97,  # ← float
            total_cost_usd=0.053,  # ← float
        )

        # Get the call arguments
        call_args = mock_table.update_item.call_args
        expr_values = call_args[1]["ExpressionAttributeValues"]

        # Verify floats were converted to Decimal
        assert isinstance(expr_values[":overall_score"], Decimal)
        assert isinstance(expr_values[":total_cost_usd"], Decimal)
        assert expr_values[":overall_score"] == Decimal("67.97")
        assert expr_values[":total_cost_usd"] == Decimal("0.053")

    def test_update_submission_status_converts_nested_dict_floats(self, db, mock_table):
        """Test update_submission_status converts floats in nested dicts."""
        db.update_submission_status(
            hack_id="HACK123",
            sub_id="SUB456",
            status="completed",
            updated_at=datetime.now(UTC).isoformat(),
            weighted_scores={
                "innovation": {"raw": 8.5, "weight": 0.3, "weighted": 25.5},
                "performance": {"raw": 7.2, "weight": 0.25, "weighted": 18.0},
            },
        )

        call_args = mock_table.update_item.call_args
        expr_values = call_args[1]["ExpressionAttributeValues"]
        weighted_scores = expr_values[":weighted_scores"]

        # Verify all nested floats converted to Decimal
        assert isinstance(weighted_scores["innovation"]["raw"], Decimal)
        assert isinstance(weighted_scores["innovation"]["weight"], Decimal)
        assert isinstance(weighted_scores["innovation"]["weighted"], Decimal)
        assert isinstance(weighted_scores["performance"]["raw"], Decimal)

    def test_update_api_key_usage_converts_float_cost(self, db, mock_table):
        """Test update_api_key_usage converts float cost to Decimal."""
        db.update_api_key_usage(
            api_key_id="KEY123",
            total_requests=100,
            total_cost_usd=5.75,  # ← float
            last_used_at=datetime.now(UTC).isoformat(),
        )

        call_args = mock_table.update_item.call_args
        expr_values = call_args[1]["ExpressionAttributeValues"]

        # Verify float converted to Decimal
        assert isinstance(expr_values[":total_cost_usd"], Decimal)
        assert expr_values[":total_cost_usd"] == Decimal("5.75")

    def test_put_cost_record_handles_float_costs(self, db, mock_table):
        """Test put_cost_record serializes float costs."""
        cost_record = {
            "PK": "SUB#123",
            "SK": "COST#agent",
            "input_cost_usd": 0.025,  # ← float
            "output_cost_usd": 0.028,  # ← float
            "total_cost_usd": 0.053,  # ← float
        }

        db.put_cost_record(cost_record)

        call_args = mock_table.put_item.call_args
        item = call_args[1]["Item"]

        # Verify floats converted to Decimal
        assert isinstance(item["input_cost_usd"], Decimal)
        assert isinstance(item["output_cost_usd"], Decimal)
        assert isinstance(item["total_cost_usd"], Decimal)

    def test_put_analysis_job_handles_float_cost(self, db, mock_table):
        """Test put_analysis_job serializes float costs."""
        job = {
            "PK": "HACK#123",
            "SK": "JOB#456",
            "total_cost_usd": 2.5,  # ← float
        }

        db.put_analysis_job(job)

        call_args = mock_table.put_item.call_args
        item = call_args[1]["Item"]

        # Verify float converted to Decimal
        assert isinstance(item["total_cost_usd"], Decimal)

    def test_realistic_submission_update_scenario(self, db, mock_table):
        """Test realistic scenario: updating submission with analysis results."""
        # This mimics what lambda_handler does when analysis completes
        db.update_submission_status(
            hack_id="HACK123",
            sub_id="SUB456",
            status="completed",
            updated_at=datetime.now(UTC).isoformat(),
            overall_score=67.97,  # ← float from orchestrator
            total_cost_usd=0.053,  # ← float from cost calculation
            weighted_scores={
                "innovation": {
                    "raw": 8.5,
                    "weight": 0.3,
                    "weighted": 25.5,
                },
            },
            agent_scores={
                "innovation_agent": {
                    "overall_score": 8.5,
                    "confidence": 0.92,
                },
            },
            repo_meta={
                "commit_count": 45,
                "contributor_count": 3,
                "development_duration_hours": 12.5,  # ← float
            },
        )

        call_args = mock_table.update_item.call_args
        expr_values = call_args[1]["ExpressionAttributeValues"]

        # Verify ALL floats converted (top-level and nested)
        assert isinstance(expr_values[":overall_score"], Decimal)
        assert isinstance(expr_values[":total_cost_usd"], Decimal)
        assert isinstance(expr_values[":weighted_scores"]["innovation"]["raw"], Decimal)
        assert isinstance(expr_values[":agent_scores"]["innovation_agent"]["overall_score"], Decimal)
        assert isinstance(expr_values[":agent_scores"]["innovation_agent"]["confidence"], Decimal)
        assert isinstance(expr_values[":repo_meta"]["development_duration_hours"], Decimal)

        # Verify no TypeError was raised
        assert mock_table.update_item.called


class TestErrorScenarios:
    """Test that float conversion prevents production errors."""

    @pytest.fixture
    def mock_table(self):
        """Mock DynamoDB table that rejects floats like real DynamoDB."""
        def raise_on_float(*args, **kwargs):
            """Simulate boto3 behavior when encountering float."""
            expr_values = kwargs.get("ExpressionAttributeValues", {})
            for key, value in expr_values.items():
                if isinstance(value, float):
                    raise TypeError(f"Float types are not supported. Use Decimal types instead. Got {value}")
                # Check nested dicts
                if isinstance(value, dict):
                    for k, v in value.items():
                        if isinstance(v, float):
                            raise TypeError(f"Float types are not supported. Use Decimal types instead. Got {v}")
            # Also check put_item
            item = kwargs.get("Item", {})
            for key, value in item.items():
                if isinstance(value, float):
                    raise TypeError(f"Float types are not supported. Use Decimal types instead. Got {value}")
            return MagicMock()

        with patch('boto3.resource') as mock_resource:
            mock_table = Mock()
            mock_table.update_item.side_effect = raise_on_float
            mock_table.put_item.side_effect = raise_on_float
            mock_resource.return_value.Table.return_value = mock_table
            yield mock_table

    @pytest.fixture
    def db(self, mock_table):
        """DynamoDB helper with mocked table."""
        return DynamoDBHelper("test-table")

    def test_submission_update_does_not_raise_float_error(self, db):
        """Test that submission updates with float scores don't raise TypeError."""
        # This should NOT raise TypeError because floats are converted
        result = db.update_submission_status(
            hack_id="HACK123",
            sub_id="SUB456",
            status="completed",
            updated_at=datetime.now(UTC).isoformat(),
            overall_score=67.97,  # ← would cause TypeError without fix
            total_cost_usd=0.053,  # ← would cause TypeError without fix
        )

        assert result is True

    def test_api_key_usage_update_does_not_raise_float_error(self, db):
        """Test that API key updates with float cost don't raise TypeError."""
        # This should NOT raise TypeError because floats are converted
        result = db.update_api_key_usage(
            api_key_id="KEY123",
            total_cost_usd=5.75,  # ← would cause TypeError without fix
        )

        assert result is True
