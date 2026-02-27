"""Unit tests for usage tracking service."""

from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest

from src.models.rate_limit import UsageRecord
from src.services.usage_tracking_service import UsageTrackingService
from src.utils.id_gen import generate_id


@pytest.fixture
def mock_db():
    """Create mock DynamoDB helper."""
    db = MagicMock()
    db.table = MagicMock()
    db._serialize_item = MagicMock(side_effect=lambda x: x)
    return db


@pytest.fixture
def service(mock_db):
    """Create usage tracking service with mock DB."""
    return UsageTrackingService(mock_db)


class TestRecordRequest:
    """Tests for record_request method."""

    def test_record_successful_request(self, service, mock_db):
        """Test recording a successful request."""
        # Mock get_item to return None (no existing record)
        mock_db.table.get_item.return_value = {"Item": None}

        # Record request
        service.record_request(
            api_key="vj_test_abc123",
            endpoint="/api/v1/hackathons",
            status_code=200,
            response_time_ms=150.5,
            cost_usd=0.001,
        )

        # Verify put_item was called
        assert mock_db.table.put_item.called
        call_args = mock_db.table.put_item.call_args[1]
        item = call_args["Item"]

        # Verify counters
        assert item["request_count"] == 1
        assert item["successful_requests"] == 1
        assert item["failed_requests"] == 0
        assert item["total_cost_usd"] == 0.001

    def test_record_failed_request(self, service, mock_db):
        """Test recording a failed request."""
        # Mock get_item to return None
        mock_db.table.get_item.return_value = {"Item": None}

        # Record failed request
        service.record_request(
            api_key="vj_test_abc123",
            endpoint="/api/v1/hackathons",
            status_code=500,
            response_time_ms=50.0,
            cost_usd=0.0,
        )

        # Verify counters
        call_args = mock_db.table.put_item.call_args[1]
        item = call_args["Item"]
        assert item["request_count"] == 1
        assert item["successful_requests"] == 0
        assert item["failed_requests"] == 1

    def test_record_request_updates_existing(self, service, mock_db):
        """Test recording request updates existing record."""
        # Create existing record
        existing = UsageRecord(
            usage_id=generate_id(),
            api_key="vj_test_abc123",
            date="2024-01-15",
            request_count=5,
            successful_requests=4,
            failed_requests=1,
            total_cost_usd=0.005,
            endpoints_used={"/api/v1/hackathons": 3},
        )

        # Mock get_item to return existing record
        mock_db.table.get_item.return_value = {"Item": existing.model_dump()}

        # Record new request
        service.record_request(
            api_key="vj_test_abc123",
            endpoint="/api/v1/submissions",
            status_code=201,
            response_time_ms=200.0,
            cost_usd=0.002,
        )

        # Verify updated counters
        call_args = mock_db.table.put_item.call_args[1]
        item = call_args["Item"]
        assert item["request_count"] == 6
        assert item["successful_requests"] == 5
        assert item["failed_requests"] == 1
        assert item["total_cost_usd"] == 0.007

    def test_record_request_tracks_endpoints(self, service, mock_db):
        """Test endpoint usage tracking."""
        mock_db.table.get_item.return_value = {"Item": None}

        # Record multiple requests to different endpoints
        service.record_request(
            api_key="vj_test_abc123",
            endpoint="/api/v1/hackathons",
            status_code=200,
            response_time_ms=100.0,
        )

        # Get the endpoints_used from the call
        call_args = mock_db.table.put_item.call_args[1]
        item = call_args["Item"]
        assert "/api/v1/hackathons" in item["endpoints_used"]
        assert item["endpoints_used"]["/api/v1/hackathons"] == 1

    def test_record_request_handles_errors(self, service, mock_db):
        """Test error handling in record_request."""
        # Mock get_item to raise exception
        mock_db.table.get_item.side_effect = Exception("DynamoDB error")

        # Should not raise exception
        service.record_request(
            api_key="vj_test_abc123",
            endpoint="/api/v1/hackathons",
            status_code=200,
            response_time_ms=100.0,
        )


class TestCheckDailyQuota:
    """Tests for check_daily_quota method."""

    def test_check_quota_no_usage(self, service, mock_db):
        """Test quota check with no usage today."""
        # Mock get_item to return None
        mock_db.table.get_item.return_value = {"Item": None}

        allowed, used, remaining = service.check_daily_quota(
            api_key="vj_test_abc123",
            daily_quota=100,
        )

        assert allowed is True
        assert used == 0
        assert remaining == 100

    def test_check_quota_within_limit(self, service, mock_db):
        """Test quota check within limit."""
        # Create usage record
        usage = UsageRecord(
            usage_id=generate_id(),
            api_key="vj_test_abc123",
            date=datetime.utcnow().strftime("%Y-%m-%d"),
            request_count=50,
            successful_requests=45,
            failed_requests=5,
        )

        mock_db.table.get_item.return_value = {"Item": usage.model_dump()}

        allowed, used, remaining = service.check_daily_quota(
            api_key="vj_test_abc123",
            daily_quota=100,
        )

        assert allowed is True
        assert used == 45  # Only successful requests count
        assert remaining == 55

    def test_check_quota_exceeded(self, service, mock_db):
        """Test quota check when exceeded."""
        # Create usage record at quota limit
        usage = UsageRecord(
            usage_id=generate_id(),
            api_key="vj_test_abc123",
            date=datetime.utcnow().strftime("%Y-%m-%d"),
            request_count=110,
            successful_requests=100,
            failed_requests=10,
        )

        mock_db.table.get_item.return_value = {"Item": usage.model_dump()}

        allowed, used, remaining = service.check_daily_quota(
            api_key="vj_test_abc123",
            daily_quota=100,
        )

        assert allowed is False
        assert used == 100
        assert remaining == 0

    def test_check_quota_failed_requests_excluded(self, service, mock_db):
        """Test that failed requests don't count toward quota."""
        # Create usage record with many failed requests
        usage = UsageRecord(
            usage_id=generate_id(),
            api_key="vj_test_abc123",
            date=datetime.utcnow().strftime("%Y-%m-%d"),
            request_count=150,
            successful_requests=50,
            failed_requests=100,
        )

        mock_db.table.get_item.return_value = {"Item": usage.model_dump()}

        allowed, used, remaining = service.check_daily_quota(
            api_key="vj_test_abc123",
            daily_quota=100,
        )

        # Should still be allowed since only 50 successful requests
        assert allowed is True
        assert used == 50
        assert remaining == 50

    def test_check_quota_handles_errors(self, service, mock_db):
        """Test error handling in check_daily_quota."""
        # Mock get_item to raise exception
        mock_db.table.get_item.side_effect = Exception("DynamoDB error")

        # Should fail open (allow request)
        allowed, used, remaining = service.check_daily_quota(
            api_key="vj_test_abc123",
            daily_quota=100,
        )

        assert allowed is True
        assert used == 0
        assert remaining == 100


class TestGetUsageSummary:
    """Tests for get_usage_summary method."""

    def test_get_usage_summary_single_day(self, service, mock_db):
        """Test usage summary for single day."""
        # Create usage record
        usage = UsageRecord(
            usage_id=generate_id(),
            api_key="vj_test_abc123",
            date="2024-01-15",
            request_count=100,
            successful_requests=95,
            failed_requests=5,
            total_cost_usd=0.050,
            endpoints_used={
                "/api/v1/hackathons": 60,
                "/api/v1/submissions": 40,
            },
        )

        mock_db.table.query.return_value = {"Items": [usage.model_dump()]}

        start_date = datetime(2024, 1, 15)
        end_date = datetime(2024, 1, 15)

        summary = service.get_usage_summary(
            api_key="vj_test_abc123",
            start_date=start_date,
            end_date=end_date,
        )

        assert summary["total_requests"] == 100
        assert summary["successful_requests"] == 95
        assert summary["failed_requests"] == 5
        assert summary["total_cost_usd"] == 0.050
        assert len(summary["daily_breakdown"]) == 1
        assert summary["endpoints_used"]["/api/v1/hackathons"] == 60

    def test_get_usage_summary_multiple_days(self, service, mock_db):
        """Test usage summary aggregates multiple days."""
        # Create usage records for 3 days
        usage1 = UsageRecord(
            usage_id=generate_id(),
            api_key="vj_test_abc123",
            date="2024-01-15",
            request_count=50,
            successful_requests=48,
            failed_requests=2,
            total_cost_usd=0.025,
            endpoints_used={"/api/v1/hackathons": 30},
        )

        usage2 = UsageRecord(
            usage_id=generate_id(),
            api_key="vj_test_abc123",
            date="2024-01-16",
            request_count=75,
            successful_requests=70,
            failed_requests=5,
            total_cost_usd=0.038,
            endpoints_used={"/api/v1/hackathons": 40, "/api/v1/submissions": 35},
        )

        mock_db.table.query.return_value = {
            "Items": [usage1.model_dump(), usage2.model_dump()]
        }

        start_date = datetime(2024, 1, 15)
        end_date = datetime(2024, 1, 16)

        summary = service.get_usage_summary(
            api_key="vj_test_abc123",
            start_date=start_date,
            end_date=end_date,
        )

        # Verify aggregation
        assert summary["total_requests"] == 125
        assert summary["successful_requests"] == 118
        assert summary["failed_requests"] == 7
        assert summary["total_cost_usd"] == 0.063
        assert len(summary["daily_breakdown"]) == 2
        assert summary["endpoints_used"]["/api/v1/hackathons"] == 70

    def test_get_usage_summary_no_data(self, service, mock_db):
        """Test usage summary with no data."""
        mock_db.table.query.return_value = {"Items": []}

        start_date = datetime(2024, 1, 15)
        end_date = datetime(2024, 1, 15)

        summary = service.get_usage_summary(
            api_key="vj_test_abc123",
            start_date=start_date,
            end_date=end_date,
        )

        assert summary["total_requests"] == 0
        assert summary["successful_requests"] == 0
        assert summary["failed_requests"] == 0
        assert summary["total_cost_usd"] == 0.0
        assert len(summary["daily_breakdown"]) == 0

    def test_get_usage_summary_handles_errors(self, service, mock_db):
        """Test error handling in get_usage_summary."""
        mock_db.table.query.side_effect = Exception("DynamoDB error")

        start_date = datetime(2024, 1, 15)
        end_date = datetime(2024, 1, 15)

        summary = service.get_usage_summary(
            api_key="vj_test_abc123",
            start_date=start_date,
            end_date=end_date,
        )

        # Should return empty summary with error
        assert summary["total_requests"] == 0
        assert "error" in summary


class TestExportUsageCSV:
    """Tests for export_usage_csv method."""

    def test_export_csv_format(self, service, mock_db):
        """Test CSV export format."""
        # Create usage record
        usage = UsageRecord(
            usage_id=generate_id(),
            api_key="vj_test_abc123",
            date="2024-01-15",
            request_count=100,
            successful_requests=95,
            failed_requests=5,
            total_cost_usd=0.050,
            endpoints_used={"/api/v1/hackathons": 60},
        )

        mock_db.table.query.return_value = {"Items": [usage.model_dump()]}

        start_date = datetime(2024, 1, 15)
        end_date = datetime(2024, 1, 15)

        csv_content = service.export_usage_csv(
            api_key="vj_test_abc123",
            start_date=start_date,
            end_date=end_date,
        )

        # Verify CSV contains expected data
        assert "date,total_requests,successful_requests,failed_requests" in csv_content
        assert "2024-01-15,100,95,5" in csv_content
        assert "SUMMARY" in csv_content
        assert "Total Requests,100" in csv_content
        assert "ENDPOINT BREAKDOWN" in csv_content

    def test_export_csv_handles_errors(self, service, mock_db):
        """Test error handling in export_usage_csv."""
        mock_db.table.query.side_effect = Exception("DynamoDB error")

        start_date = datetime(2024, 1, 15)
        end_date = datetime(2024, 1, 15)

        csv_content = service.export_usage_csv(
            api_key="vj_test_abc123",
            start_date=start_date,
            end_date=end_date,
        )

        # CSV is still generated with empty data when summary has error
        assert "date,total_requests" in csv_content
        assert "Total Requests,0" in csv_content


class TestQuotaResetTime:
    """Tests for get_quota_reset_time method."""

    def test_quota_reset_time(self, service):
        """Test quota reset time calculation."""
        reset_time = service.get_quota_reset_time()

        # Should be midnight UTC tomorrow
        now = datetime.utcnow()
        tomorrow = now.date() + timedelta(days=1)
        expected = datetime.combine(tomorrow, datetime.min.time())

        assert reset_time == expected
        assert reset_time.hour == 0
        assert reset_time.minute == 0
        assert reset_time.second == 0
