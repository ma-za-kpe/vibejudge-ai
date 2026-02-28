"""Rate limiting, usage tracking, budget, and security event models."""

from datetime import datetime
from typing import Any

from pydantic import Field, field_validator, model_validator

from src.models.common import Severity, TimestampMixin, VibeJudgeBase

# ============================================================
# RATE LIMIT COUNTER MODEL
# ============================================================


class RateLimitCounter(VibeJudgeBase):
    """Sliding window counter for rate limiting with TTL."""

    counter_key: str = Field(description="api_key#{window_start_epoch}")
    api_key: str = Field(description="API key being tracked")
    window_start: int = Field(description="Unix timestamp (second precision)")
    request_count: int = Field(default=0, ge=0, description="Number of requests in window")
    ttl: int = Field(description="Auto-delete after 60 seconds (Unix timestamp)")

    # DynamoDB schema fields
    PK: str = Field(default="", description="RATELIMIT#{api_key}#{window_start}")
    SK: str = Field(default="COUNTER", description="Sort key")
    entity_type: str = Field(default="RATE_LIMIT_COUNTER")

    @model_validator(mode="after")
    def validate_ttl(self) -> "RateLimitCounter":
        """Ensure TTL is window_start + 60."""
        expected_ttl = self.window_start + 60
        if self.ttl != expected_ttl:
            raise ValueError(
                f"TTL must be window_start + 60 (expected {expected_ttl}, got {self.ttl})"
            )
        return self

    def set_dynamodb_keys(self) -> None:
        """Set DynamoDB partition and sort keys."""
        self.PK = f"RATELIMIT#{self.api_key}#{self.window_start}"
        self.SK = "COUNTER"


# ============================================================
# USAGE RECORD MODEL
# ============================================================


class UsageRecord(VibeJudgeBase, TimestampMixin):
    """Daily usage tracking for quota management."""

    usage_id: str = Field(description="ULID identifier")
    api_key: str = Field(description="API key")
    date: str = Field(description="YYYY-MM-DD format")

    # Counters
    request_count: int = Field(default=0, ge=0, description="Total requests")
    successful_requests: int = Field(default=0, ge=0, description="Successful requests")
    failed_requests: int = Field(default=0, ge=0, description="Failed requests")

    # Cost tracking
    total_cost_usd: float = Field(default=0.0, ge=0, description="Total cost in USD")
    bedrock_cost_usd: float = Field(default=0.0, ge=0, description="Bedrock cost in USD")
    lambda_cost_usd: float = Field(default=0.0, ge=0, description="Lambda cost in USD")

    # Metadata
    endpoints_used: dict[str, int] = Field(
        default_factory=dict, description="Endpoint usage counts"
    )

    # DynamoDB schema fields
    PK: str = Field(default="", description="USAGE#{api_key}#{date}")
    SK: str = Field(default="SUMMARY", description="Sort key")
    GSI1PK: str = Field(default="", description="APIKEY#{api_key}")
    GSI1SK: str = Field(default="", description="DATE#{date}")
    entity_type: str = Field(default="USAGE_RECORD")

    @field_validator("date")
    @classmethod
    def validate_date_format(cls, v: str) -> str:
        """Validate date is in YYYY-MM-DD format."""
        # Check format with regex first for strict validation
        import re

        if not re.match(r"^\d{4}-\d{2}-\d{2}$", v):
            raise ValueError("date must be in YYYY-MM-DD format")
        # Then validate it's a real date
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError:
            raise ValueError("date must be in YYYY-MM-DD format")
        return v

    @model_validator(mode="after")
    def validate_request_count(self) -> "UsageRecord":
        """Ensure request_count = successful_requests + failed_requests."""
        expected = self.successful_requests + self.failed_requests
        if self.request_count != expected:
            raise ValueError(
                f"request_count must equal successful_requests + failed_requests "
                f"(expected {expected}, got {self.request_count})"
            )
        return self

    def set_dynamodb_keys(self) -> None:
        """Set DynamoDB partition and sort keys."""
        self.PK = f"USAGE#{self.api_key}#{self.date}"
        self.SK = "SUMMARY"
        self.GSI1PK = f"APIKEY#{self.api_key}"
        self.GSI1SK = f"DATE#{self.date}"


# ============================================================
# BUDGET TRACKING MODEL
# ============================================================


class BudgetTracking(VibeJudgeBase, TimestampMixin):
    """Real-time budget tracking for cost control."""

    entity_type: str = Field(description="api_key | hackathon | submission")
    entity_id: str = Field(description="Entity identifier")

    # Budget limits
    budget_limit_usd: float = Field(gt=0, description="Maximum allowed spend")
    current_spend_usd: float = Field(default=0.0, ge=0, description="Current spend in USD")

    # Alerts
    alert_50_sent: bool = Field(default=False, description="50% threshold alert sent")
    alert_80_sent: bool = Field(default=False, description="80% threshold alert sent")
    alert_90_sent: bool = Field(default=False, description="90% threshold alert sent")
    alert_100_sent: bool = Field(default=False, description="100% threshold alert sent")

    # DynamoDB schema fields
    PK: str = Field(default="", description="BUDGET#{entity_type}#{entity_id}")
    SK: str = Field(default="TRACKING", description="Sort key")
    GSI1PK: str = Field(default="", description="ENTITY#{entity_type}")
    GSI1SK: str = Field(default="", description="SPEND#{current_spend_usd}")
    entity_type_field: str = Field(default="BUDGET_TRACKING")

    @field_validator("entity_type")
    @classmethod
    def validate_entity_type(cls, v: str) -> str:
        """Ensure entity_type is one of: api_key, hackathon, submission."""
        valid_types = ["api_key", "hackathon", "submission"]
        if v not in valid_types:
            raise ValueError(f"entity_type must be one of: {', '.join(valid_types)}")
        return v

    @model_validator(mode="after")
    def validate_current_spend(self) -> "BudgetTracking":
        """Warn if current_spend exceeds budget_limit * 1.1 (10% grace)."""
        max_allowed = self.budget_limit_usd * 1.1
        if self.current_spend_usd > max_allowed:
            raise ValueError(
                f"current_spend_usd ({self.current_spend_usd}) exceeds budget_limit * 1.1 ({max_allowed})"
            )
        return self

    def set_dynamodb_keys(self) -> None:
        """Set DynamoDB partition and sort keys."""
        self.PK = f"BUDGET#{self.entity_type}#{self.entity_id}"
        self.SK = "TRACKING"
        self.GSI1PK = f"ENTITY#{self.entity_type}"
        self.GSI1SK = f"SPEND#{self.current_spend_usd:.4f}"

    def get_usage_percentage(self) -> float:
        """Calculate current usage as percentage of budget."""
        if self.budget_limit_usd == 0:
            return 0.0
        return (self.current_spend_usd / self.budget_limit_usd) * 100

    def should_send_alert(self, threshold: int) -> bool:
        """Check if alert should be sent for given threshold (50, 80, 90, 100)."""
        usage_pct = self.get_usage_percentage()
        alert_map = {
            50: self.alert_50_sent,
            80: self.alert_80_sent,
            90: self.alert_90_sent,
            100: self.alert_100_sent,
        }
        if threshold not in alert_map:
            raise ValueError(f"Invalid threshold: {threshold}. Must be 50, 80, 90, or 100")
        return usage_pct >= threshold and not alert_map[threshold]


# ============================================================
# SECURITY EVENT MODEL
# ============================================================


class SecurityEvent(VibeJudgeBase):
    """Security event log for monitoring and incident response."""

    event_id: str = Field(description="ULID identifier")
    event_type: str = Field(description="auth_failure | rate_limit | budget_exceeded | anomaly")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    # Request context
    api_key_prefix: str = Field(description="First 8 chars of API key")
    ip_address: str | None = Field(default=None, description="Client IP address")
    endpoint: str = Field(description="API endpoint")

    # Event details
    status_code: int = Field(description="HTTP status code")
    error_message: str | None = Field(default=None, description="Error message")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    # Severity
    severity: Severity = Field(default=Severity.INFO, description="Event severity")

    # TTL for auto-cleanup (30 days)
    ttl: int = Field(description="Auto-delete after 30 days (Unix timestamp)")

    # DynamoDB schema fields
    PK: str = Field(default="", description="SECURITY#{date}")
    SK: str = Field(default="", description="EVENT#{timestamp}#{event_id}")
    GSI1PK: str = Field(default="", description="APIKEY#{api_key_prefix}")
    GSI1SK: str = Field(default="", description="TIMESTAMP#{timestamp}")
    entity_type_field: str = Field(default="SECURITY_EVENT")

    @field_validator("event_type")
    @classmethod
    def validate_event_type(cls, v: str) -> str:
        """Ensure event_type is one of: auth_failure, rate_limit, budget_exceeded, anomaly."""
        valid_types = ["auth_failure", "rate_limit", "budget_exceeded", "anomaly"]
        if v not in valid_types:
            raise ValueError(f"event_type must be one of: {', '.join(valid_types)}")
        return v

    @field_validator("api_key_prefix")
    @classmethod
    def validate_api_key_prefix(cls, v: str) -> str:
        """Ensure api_key_prefix is exactly 8 characters."""
        if len(v) != 8:
            raise ValueError("api_key_prefix must be exactly 8 characters")
        return v

    @field_validator("status_code")
    @classmethod
    def validate_status_code(cls, v: int) -> int:
        """Ensure status_code is a valid HTTP error status (400-599)."""
        if not 400 <= v <= 599:
            raise ValueError("status_code must be between 400 and 599")
        return v

    def set_dynamodb_keys(self) -> None:
        """Set DynamoDB partition and sort keys."""
        date_str = self.timestamp.strftime("%Y-%m-%d")
        timestamp_iso = self.timestamp.isoformat()
        self.PK = f"SECURITY#{date_str}"
        self.SK = f"EVENT#{timestamp_iso}#{self.event_id}"
        self.GSI1PK = f"APIKEY#{self.api_key_prefix}"
        self.GSI1SK = f"TIMESTAMP#{timestamp_iso}"

    @staticmethod
    def calculate_ttl(timestamp: datetime, days: int = 30) -> int:
        """Calculate TTL timestamp (Unix epoch) for auto-deletion."""
        from datetime import timedelta

        expiry = timestamp + timedelta(days=days)
        return int(expiry.timestamp())


# ============================================================
# USAGE SUMMARY MODEL
# ============================================================


class DailyUsageBreakdown(VibeJudgeBase):
    """Daily usage breakdown for summary."""

    date: str = Field(description="Date in YYYY-MM-DD format")
    requests: int = Field(ge=0, description="Total requests for the day")
    successful: int = Field(ge=0, description="Successful requests")
    failed: int = Field(ge=0, description="Failed requests")
    cost_usd: float = Field(ge=0.0, description="Total cost in USD")


class UsageSummary(VibeJudgeBase):
    """Usage summary response model."""

    api_key_prefix: str = Field(description="First 8 characters of API key")
    start_date: str = Field(description="Start date (YYYY-MM-DD)")
    end_date: str = Field(description="End date (YYYY-MM-DD)")
    total_requests: int = Field(ge=0, description="Total number of requests")
    successful_requests: int = Field(ge=0, description="Number of successful requests")
    failed_requests: int = Field(ge=0, description="Number of failed requests")
    total_cost_usd: float = Field(ge=0.0, description="Total cost in USD")
    endpoints_used: dict[str, int] = Field(
        default_factory=dict, description="Breakdown by endpoint"
    )
    daily_breakdown: list[DailyUsageBreakdown] = Field(
        default_factory=list, description="Daily usage records"
    )
    error: str | None = Field(
        default=None, description="Error message if summary generation failed"
    )
