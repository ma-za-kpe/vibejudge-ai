"""Unit tests for rate limiting models."""

from datetime import datetime, timedelta

import pytest
from pydantic import ValidationError

from src.models.common import Severity
from src.models.rate_limit import (
    BudgetTracking,
    RateLimitCounter,
    SecurityEvent,
    UsageRecord,
)


class TestRateLimitCounter:
    """Tests for RateLimitCounter model."""

    def test_create_with_valid_data(self) -> None:
        """Test creating rate limit counter with valid data."""
        window_start = int(datetime.utcnow().timestamp())
        counter = RateLimitCounter(
            counter_key=f"vj_test_abc#{window_start}",
            api_key="vj_test_abc123def456ghi789jkl012mno34pqr",
            window_start=window_start,
            request_count=5,
            ttl=window_start + 60,
        )
        assert counter.api_key == "vj_test_abc123def456ghi789jkl012mno34pqr"
        assert counter.window_start == window_start
        assert counter.request_count == 5
        assert counter.ttl == window_start + 60

    def test_ttl_validation(self) -> None:
        """Test that TTL must be window_start + 60."""
        window_start = int(datetime.utcnow().timestamp())

        # Valid TTL
        counter = RateLimitCounter(
            counter_key=f"vj_test_abc#{window_start}",
            api_key="vj_test_abc123def456ghi789jkl012mno34pqr",
            window_start=window_start,
            ttl=window_start + 60,
        )
        assert counter.ttl == window_start + 60

        # Invalid TTL
        with pytest.raises(ValidationError) as exc_info:
            RateLimitCounter(
                counter_key=f"vj_test_abc#{window_start}",
                api_key="vj_test_abc123def456ghi789jkl012mno34pqr",
                window_start=window_start,
                ttl=window_start + 120,  # Wrong TTL
            )
        assert "TTL must be window_start + 60" in str(exc_info.value)

    def test_request_count_must_be_non_negative(self) -> None:
        """Test that request_count must be >= 0."""
        window_start = int(datetime.utcnow().timestamp())

        # Valid: 0
        counter = RateLimitCounter(
            counter_key=f"vj_test_abc#{window_start}",
            api_key="vj_test_abc123def456ghi789jkl012mno34pqr",
            window_start=window_start,
            request_count=0,
            ttl=window_start + 60,
        )
        assert counter.request_count == 0

        # Invalid: negative
        with pytest.raises(ValidationError):
            RateLimitCounter(
                counter_key=f"vj_test_abc#{window_start}",
                api_key="vj_test_abc123def456ghi789jkl012mno34pqr",
                window_start=window_start,
                request_count=-1,
                ttl=window_start + 60,
            )

    def test_set_dynamodb_keys(self) -> None:
        """Test DynamoDB key generation."""
        window_start = int(datetime.utcnow().timestamp())
        counter = RateLimitCounter(
            counter_key=f"vj_test_abc#{window_start}",
            api_key="vj_test_abc123def456ghi789jkl012mno34pqr",
            window_start=window_start,
            ttl=window_start + 60,
        )
        counter.set_dynamodb_keys()

        assert f"RATELIMIT#vj_test_abc123def456ghi789jkl012mno34pqr#{window_start}" == counter.PK
        assert counter.SK == "COUNTER"


class TestUsageRecord:
    """Tests for UsageRecord model."""

    def test_create_with_valid_data(self) -> None:
        """Test creating usage record with valid data."""
        record = UsageRecord(
            usage_id="01HQ123456789",
            api_key="vj_test_abc123def456ghi789jkl012mno34pqr",
            date="2024-01-15",
            request_count=100,
            successful_requests=95,
            failed_requests=5,
            total_cost_usd=2.50,
            bedrock_cost_usd=2.30,
            lambda_cost_usd=0.20,
        )
        assert record.api_key == "vj_test_abc123def456ghi789jkl012mno34pqr"
        assert record.date == "2024-01-15"
        assert record.request_count == 100
        assert record.successful_requests == 95
        assert record.failed_requests == 5

    def test_date_format_validation(self) -> None:
        """Test that date must be in YYYY-MM-DD format."""
        # Valid format
        record = UsageRecord(
            usage_id="01HQ123456789",
            api_key="vj_test_abc123def456ghi789jkl012mno34pqr",
            date="2024-01-15",
            request_count=10,
            successful_requests=10,
            failed_requests=0,
        )
        assert record.date == "2024-01-15"

        # Invalid formats
        invalid_dates = ["2024/01/15", "15-01-2024", "2024-1-15", "invalid"]
        for invalid_date in invalid_dates:
            with pytest.raises(ValidationError) as exc_info:
                UsageRecord(
                    usage_id="01HQ123456789",
                    api_key="vj_test_abc123def456ghi789jkl012mno34pqr",
                    date=invalid_date,
                    request_count=10,
                    successful_requests=10,
                    failed_requests=0,
                )
            assert "date must be in YYYY-MM-DD format" in str(exc_info.value)

    def test_request_count_validation(self) -> None:
        """Test that request_count = successful_requests + failed_requests."""
        # Valid: counts match
        record = UsageRecord(
            usage_id="01HQ123456789",
            api_key="vj_test_abc123def456ghi789jkl012mno34pqr",
            date="2024-01-15",
            request_count=100,
            successful_requests=95,
            failed_requests=5,
        )
        assert record.request_count == 100

        # Invalid: counts don't match
        with pytest.raises(ValidationError) as exc_info:
            UsageRecord(
                usage_id="01HQ123456789",
                api_key="vj_test_abc123def456ghi789jkl012mno34pqr",
                date="2024-01-15",
                request_count=100,
                successful_requests=90,
                failed_requests=5,  # Should be 10
            )
        assert "request_count must equal successful_requests + failed_requests" in str(
            exc_info.value
        )

    def test_cost_fields_must_be_non_negative(self) -> None:
        """Test that all cost fields must be >= 0."""
        # Valid: 0.0
        record = UsageRecord(
            usage_id="01HQ123456789",
            api_key="vj_test_abc123def456ghi789jkl012mno34pqr",
            date="2024-01-15",
            request_count=0,
            successful_requests=0,
            failed_requests=0,
            total_cost_usd=0.0,
            bedrock_cost_usd=0.0,
            lambda_cost_usd=0.0,
        )
        assert record.total_cost_usd == 0.0

        # Invalid: negative total_cost_usd
        with pytest.raises(ValidationError):
            UsageRecord(
                usage_id="01HQ123456789",
                api_key="vj_test_abc123def456ghi789jkl012mno34pqr",
                date="2024-01-15",
                request_count=0,
                successful_requests=0,
                failed_requests=0,
                total_cost_usd=-1.0,
            )

    def test_set_dynamodb_keys(self) -> None:
        """Test DynamoDB key generation."""
        record = UsageRecord(
            usage_id="01HQ123456789",
            api_key="vj_test_abc123def456ghi789jkl012mno34pqr",
            date="2024-01-15",
            request_count=10,
            successful_requests=10,
            failed_requests=0,
        )
        record.set_dynamodb_keys()

        assert record.PK == "USAGE#vj_test_abc123def456ghi789jkl012mno34pqr#2024-01-15"
        assert record.SK == "SUMMARY"
        assert record.GSI1PK == "APIKEY#vj_test_abc123def456ghi789jkl012mno34pqr"
        assert record.GSI1SK == "DATE#2024-01-15"

    def test_endpoints_used_default(self) -> None:
        """Test that endpoints_used defaults to empty dict."""
        record = UsageRecord(
            usage_id="01HQ123456789",
            api_key="vj_test_abc123def456ghi789jkl012mno34pqr",
            date="2024-01-15",
            request_count=0,
            successful_requests=0,
            failed_requests=0,
        )
        assert record.endpoints_used == {}


class TestBudgetTracking:
    """Tests for BudgetTracking model."""

    def test_create_with_valid_data(self) -> None:
        """Test creating budget tracking with valid data."""
        budget = BudgetTracking(
            entity_type="api_key",
            entity_id="01HQ123456789",
            budget_limit_usd=100.0,
            current_spend_usd=50.0,
        )
        assert budget.entity_type == "api_key"
        assert budget.entity_id == "01HQ123456789"
        assert budget.budget_limit_usd == 100.0
        assert budget.current_spend_usd == 50.0

    def test_entity_type_validation(self) -> None:
        """Test that entity_type must be one of: api_key, hackathon, submission."""
        valid_types = ["api_key", "hackathon", "submission"]
        for entity_type in valid_types:
            budget = BudgetTracking(
                entity_type=entity_type,
                entity_id="01HQ123456789",
                budget_limit_usd=100.0,
            )
            assert budget.entity_type == entity_type

        # Invalid type
        with pytest.raises(ValidationError) as exc_info:
            BudgetTracking(
                entity_type="invalid",
                entity_id="01HQ123456789",
                budget_limit_usd=100.0,
            )
        assert "entity_type must be one of" in str(exc_info.value)

    def test_budget_limit_must_be_positive(self) -> None:
        """Test that budget_limit_usd must be > 0."""
        # Valid: positive
        budget = BudgetTracking(
            entity_type="api_key",
            entity_id="01HQ123456789",
            budget_limit_usd=100.0,
        )
        assert budget.budget_limit_usd == 100.0

        # Invalid: zero
        with pytest.raises(ValidationError):
            BudgetTracking(
                entity_type="api_key",
                entity_id="01HQ123456789",
                budget_limit_usd=0.0,
            )

        # Invalid: negative
        with pytest.raises(ValidationError):
            BudgetTracking(
                entity_type="api_key",
                entity_id="01HQ123456789",
                budget_limit_usd=-1.0,
            )

    def test_current_spend_validation(self) -> None:
        """Test that current_spend cannot exceed budget_limit * 1.1."""
        # Valid: within limit
        budget = BudgetTracking(
            entity_type="api_key",
            entity_id="01HQ123456789",
            budget_limit_usd=100.0,
            current_spend_usd=100.0,
        )
        assert budget.current_spend_usd == 100.0

        # Valid: within 10% grace
        budget = BudgetTracking(
            entity_type="api_key",
            entity_id="01HQ123456789",
            budget_limit_usd=100.0,
            current_spend_usd=110.0,
        )
        assert budget.current_spend_usd == 110.0

        # Invalid: exceeds 10% grace
        with pytest.raises(ValidationError) as exc_info:
            BudgetTracking(
                entity_type="api_key",
                entity_id="01HQ123456789",
                budget_limit_usd=100.0,
                current_spend_usd=111.0,
            )
        assert "exceeds budget_limit * 1.1" in str(exc_info.value)

    def test_alert_flags_default_to_false(self) -> None:
        """Test that all alert flags default to False."""
        budget = BudgetTracking(
            entity_type="api_key",
            entity_id="01HQ123456789",
            budget_limit_usd=100.0,
        )
        assert budget.alert_50_sent is False
        assert budget.alert_80_sent is False
        assert budget.alert_90_sent is False
        assert budget.alert_100_sent is False

    def test_set_dynamodb_keys(self) -> None:
        """Test DynamoDB key generation."""
        budget = BudgetTracking(
            entity_type="api_key",
            entity_id="01HQ123456789",
            budget_limit_usd=100.0,
            current_spend_usd=50.0,
        )
        budget.set_dynamodb_keys()

        assert budget.PK == "BUDGET#api_key#01HQ123456789"
        assert budget.SK == "TRACKING"
        assert budget.GSI1PK == "ENTITY#api_key"
        assert budget.GSI1SK == "SPEND#50.0000"

    def test_get_usage_percentage(self) -> None:
        """Test usage percentage calculation."""
        budget = BudgetTracking(
            entity_type="api_key",
            entity_id="01HQ123456789",
            budget_limit_usd=100.0,
            current_spend_usd=50.0,
        )
        assert budget.get_usage_percentage() == 50.0

        # Edge case: zero budget
        budget.budget_limit_usd = 0.01  # Can't be 0 due to validation
        budget.current_spend_usd = 0.0
        assert budget.get_usage_percentage() == 0.0

    def test_should_send_alert(self) -> None:
        """Test alert threshold logic."""
        budget = BudgetTracking(
            entity_type="api_key",
            entity_id="01HQ123456789",
            budget_limit_usd=100.0,
            current_spend_usd=50.0,
        )

        # 50% threshold: should send
        assert budget.should_send_alert(50) is True

        # Mark as sent
        budget.alert_50_sent = True
        assert budget.should_send_alert(50) is False

        # 80% threshold: not reached yet
        assert budget.should_send_alert(80) is False

        # Increase spend to 80%
        budget.current_spend_usd = 80.0
        assert budget.should_send_alert(80) is True

        # Invalid threshold
        with pytest.raises(ValueError) as exc_info:
            budget.should_send_alert(75)
        assert "Invalid threshold" in str(exc_info.value)


class TestSecurityEvent:
    """Tests for SecurityEvent model."""

    def test_create_with_valid_data(self) -> None:
        """Test creating security event with valid data."""
        timestamp = datetime.utcnow()
        ttl = int((timestamp + timedelta(days=30)).timestamp())

        event = SecurityEvent(
            event_id="01HQ123456789",
            event_type="rate_limit",
            timestamp=timestamp,
            api_key_prefix="vj_test_",
            endpoint="/api/v1/hackathons",
            status_code=429,
            severity=Severity.MEDIUM,
            ttl=ttl,
        )
        assert event.event_type == "rate_limit"
        assert event.api_key_prefix == "vj_test_"
        assert event.status_code == 429
        assert event.severity == Severity.MEDIUM

    def test_event_type_validation(self) -> None:
        """Test that event_type must be one of valid types."""
        valid_types = ["auth_failure", "rate_limit", "budget_exceeded", "anomaly"]
        timestamp = datetime.utcnow()
        ttl = int((timestamp + timedelta(days=30)).timestamp())

        for event_type in valid_types:
            event = SecurityEvent(
                event_id="01HQ123456789",
                event_type=event_type,
                timestamp=timestamp,
                api_key_prefix="vj_test_",
                endpoint="/api/v1/hackathons",
                status_code=429,
                ttl=ttl,
            )
            assert event.event_type == event_type

        # Invalid type
        with pytest.raises(ValidationError) as exc_info:
            SecurityEvent(
                event_id="01HQ123456789",
                event_type="invalid",
                timestamp=timestamp,
                api_key_prefix="vj_test_",
                endpoint="/api/v1/hackathons",
                status_code=429,
                ttl=ttl,
            )
        assert "event_type must be one of" in str(exc_info.value)

    def test_api_key_prefix_validation(self) -> None:
        """Test that api_key_prefix must be exactly 8 characters."""
        timestamp = datetime.utcnow()
        ttl = int((timestamp + timedelta(days=30)).timestamp())

        # Valid: 8 characters
        event = SecurityEvent(
            event_id="01HQ123456789",
            event_type="rate_limit",
            timestamp=timestamp,
            api_key_prefix="vj_test_",
            endpoint="/api/v1/hackathons",
            status_code=429,
            ttl=ttl,
        )
        assert event.api_key_prefix == "vj_test_"

        # Invalid: too short
        with pytest.raises(ValidationError) as exc_info:
            SecurityEvent(
                event_id="01HQ123456789",
                event_type="rate_limit",
                timestamp=timestamp,
                api_key_prefix="vj_test",
                endpoint="/api/v1/hackathons",
                status_code=429,
                ttl=ttl,
            )
        assert "api_key_prefix must be exactly 8 characters" in str(exc_info.value)

        # Invalid: too long
        with pytest.raises(ValidationError):
            SecurityEvent(
                event_id="01HQ123456789",
                event_type="rate_limit",
                timestamp=timestamp,
                api_key_prefix="vj_test_ab",
                endpoint="/api/v1/hackathons",
                status_code=429,
                ttl=ttl,
            )

    def test_status_code_validation(self) -> None:
        """Test that status_code must be between 400 and 599."""
        timestamp = datetime.utcnow()
        ttl = int((timestamp + timedelta(days=30)).timestamp())

        # Valid codes
        valid_codes = [400, 401, 403, 429, 500, 503, 599]
        for code in valid_codes:
            event = SecurityEvent(
                event_id="01HQ123456789",
                event_type="rate_limit",
                timestamp=timestamp,
                api_key_prefix="vj_test_",
                endpoint="/api/v1/hackathons",
                status_code=code,
                ttl=ttl,
            )
            assert event.status_code == code

        # Invalid codes
        invalid_codes = [200, 300, 399, 600]
        for code in invalid_codes:
            with pytest.raises(ValidationError) as exc_info:
                SecurityEvent(
                    event_id="01HQ123456789",
                    event_type="rate_limit",
                    timestamp=timestamp,
                    api_key_prefix="vj_test_",
                    endpoint="/api/v1/hackathons",
                    status_code=code,
                    ttl=ttl,
                )
            assert "status_code must be between 400 and 599" in str(exc_info.value)

    def test_set_dynamodb_keys(self) -> None:
        """Test DynamoDB key generation."""
        timestamp = datetime(2024, 1, 15, 10, 30, 45)
        ttl = int((timestamp + timedelta(days=30)).timestamp())

        event = SecurityEvent(
            event_id="01HQ123456789",
            event_type="rate_limit",
            timestamp=timestamp,
            api_key_prefix="vj_test_",
            endpoint="/api/v1/hackathons",
            status_code=429,
            ttl=ttl,
        )
        event.set_dynamodb_keys()

        assert event.PK == "SECURITY#2024-01-15"
        assert event.SK.startswith("EVENT#2024-01-15T10:30:45")
        assert event.GSI1PK == "APIKEY#vj_test_"
        assert event.GSI1SK.startswith("TIMESTAMP#2024-01-15T10:30:45")

    def test_calculate_ttl(self) -> None:
        """Test TTL calculation."""
        timestamp = datetime(2024, 1, 15, 10, 30, 45)

        # Default 30 days
        ttl = SecurityEvent.calculate_ttl(timestamp)
        expected = timestamp + timedelta(days=30)
        assert ttl == int(expected.timestamp())

        # Custom days
        ttl = SecurityEvent.calculate_ttl(timestamp, days=7)
        expected = timestamp + timedelta(days=7)
        assert ttl == int(expected.timestamp())

    def test_optional_fields(self) -> None:
        """Test that optional fields work correctly."""
        timestamp = datetime.utcnow()
        ttl = int((timestamp + timedelta(days=30)).timestamp())

        event = SecurityEvent(
            event_id="01HQ123456789",
            event_type="rate_limit",
            timestamp=timestamp,
            api_key_prefix="vj_test_",
            endpoint="/api/v1/hackathons",
            status_code=429,
            ttl=ttl,
            ip_address="192.168.1.1",
            error_message="Rate limit exceeded",
            metadata={"user_agent": "Mozilla/5.0"},
        )
        assert event.ip_address == "192.168.1.1"
        assert event.error_message == "Rate limit exceeded"
        assert event.metadata == {"user_agent": "Mozilla/5.0"}

    def test_severity_default(self) -> None:
        """Test that severity defaults to INFO."""
        timestamp = datetime.utcnow()
        ttl = int((timestamp + timedelta(days=30)).timestamp())

        event = SecurityEvent(
            event_id="01HQ123456789",
            event_type="rate_limit",
            timestamp=timestamp,
            api_key_prefix="vj_test_",
            endpoint="/api/v1/hackathons",
            status_code=429,
            ttl=ttl,
        )
        assert event.severity == Severity.INFO
