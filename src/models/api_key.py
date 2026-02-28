"""API key models for authentication, rate limiting, and budget control."""

import re
from datetime import datetime

from pydantic import Field, field_validator

from src.models.common import Tier, TimestampMixin, VibeJudgeBase

# ============================================================
# VALIDATION CONSTANTS
# ============================================================

API_KEY_PATTERN = re.compile(r"^vj_(live|test)_[A-Za-z0-9+/]{32}$")

# Tier-based default limits
TIER_DEFAULTS = {
    Tier.FREE: {
        "rate_limit_per_second": 2,
        "daily_quota": 100,
        "budget_limit_usd": 10.0,
    },
    Tier.STARTER: {
        "rate_limit_per_second": 5,
        "daily_quota": 500,
        "budget_limit_usd": 50.0,
    },
    Tier.PRO: {
        "rate_limit_per_second": 10,
        "daily_quota": 2500,
        "budget_limit_usd": 250.0,
    },
    Tier.ENTERPRISE: {
        "rate_limit_per_second": 50,
        "daily_quota": 999999,  # Effectively unlimited
        "budget_limit_usd": 10000.0,
    },
}


# ============================================================
# REQUEST MODELS
# ============================================================


class APIKeyCreate(VibeJudgeBase):
    """Request model for creating a new API key."""

    hackathon_id: str | None = Field(
        default=None, description="Scope key to specific hackathon (optional)"
    )
    tier: Tier = Field(default=Tier.FREE, description="API key tier")
    expires_at: datetime | None = Field(default=None, description="Expiration timestamp (optional)")
    rate_limit_per_second: int | None = Field(
        default=None, gt=0, description="Custom rate limit (uses tier default if None)"
    )
    daily_quota: int | None = Field(
        default=None, gt=0, description="Custom daily quota (uses tier default if None)"
    )
    budget_limit_usd: float | None = Field(
        default=None, ge=0, description="Custom budget limit (uses tier default if None)"
    )

    @field_validator("expires_at")
    @classmethod
    def validate_expires_at(cls, v: datetime | None) -> datetime | None:
        """Ensure expiration is in the future."""
        if v is not None and v <= datetime.utcnow():
            raise ValueError("expires_at must be in the future")
        return v


# ============================================================
# RESPONSE MODELS
# ============================================================


class APIKeyResponse(VibeJudgeBase, TimestampMixin):
    """Response model for API key (excludes secret key)."""

    api_key_id: str = Field(description="ULID identifier")
    organizer_id: str = Field(description="Owner organizer ID")
    hackathon_id: str | None = Field(default=None, description="Scoped to hackathon")

    # Tier and limits
    tier: Tier = Field(description="API key tier")
    rate_limit_per_second: int = Field(description="Requests per second")
    daily_quota: int = Field(description="Requests per day")
    budget_limit_usd: float = Field(description="Maximum spend in USD")

    # Status
    active: bool = Field(description="Whether key is active")
    expires_at: datetime | None = Field(default=None, description="Expiration timestamp")
    deprecated: bool = Field(default=False, description="Whether key is deprecated")
    deprecated_at: datetime | None = Field(default=None, description="When key was deprecated")

    # Usage tracking
    total_requests: int = Field(default=0, description="Total requests made")
    total_cost_usd: float = Field(default=0.0, description="Total cost incurred")
    last_used_at: datetime | None = Field(default=None, description="Last request timestamp")


class APIKeyCreateResponse(APIKeyResponse):
    """Response model for API key creation (includes secret key once)."""

    api_key: str = Field(description="Secret API key (shown only once)")
    _warning: str = "Store your API key securely. It will not be shown again."


class APIKeyListResponse(VibeJudgeBase):
    """Response model for listing API keys."""

    api_keys: list[APIKeyResponse] = Field(description="List of API keys")
    total: int = Field(description="Total number of keys")


# ============================================================
# INTERNAL / DYNAMODB MODELS
# ============================================================


class APIKey(VibeJudgeBase, TimestampMixin):
    """Full API key model with secret key (internal use only)."""

    # Primary identifiers
    api_key_id: str = Field(description="ULID identifier")
    api_key: str = Field(description="Secret key: vj_{env}_{32-char-base64}")
    organizer_id: str = Field(description="Owner organizer ID")
    hackathon_id: str | None = Field(default=None, description="Scoped to hackathon")

    # Tier and limits
    tier: Tier = Field(default=Tier.FREE)
    rate_limit_per_second: int = Field(gt=0, description="Requests per second")
    daily_quota: int = Field(gt=0, description="Requests per day")
    budget_limit_usd: float = Field(ge=0, description="Maximum spend in USD")

    # Status
    active: bool = Field(default=True)
    expires_at: datetime | None = Field(default=None)
    deprecated: bool = Field(default=False)
    deprecated_at: datetime | None = Field(default=None)

    # Usage tracking
    total_requests: int = Field(default=0, ge=0)
    total_cost_usd: float = Field(default=0.0, ge=0)
    last_used_at: datetime | None = Field(default=None)

    # DynamoDB schema fields
    PK: str = Field(default="", description="APIKEY#{api_key_id}")
    SK: str = Field(default="METADATA", description="Sort key")
    GSI1PK: str = Field(default="", description="ORG#{organizer_id}")
    GSI1SK: str = Field(default="", description="APIKEY#{created_at}")
    GSI2PK: str | None = Field(default=None, description="HACKATHON#{hackathon_id}")
    GSI2SK: str | None = Field(default=None, description="APIKEY#{api_key_id}")
    entity_type: str = Field(default="API_KEY")

    @field_validator("api_key")
    @classmethod
    def validate_api_key_format(cls, v: str) -> str:
        """Validate API key format: vj_{env}_{32-char-base64}."""
        if not API_KEY_PATTERN.match(v):
            raise ValueError("API key must match format: vj_(live|test)_[A-Za-z0-9+/]{32}")
        return v

    @field_validator("expires_at")
    @classmethod
    def validate_expires_at(cls, v: datetime | None) -> datetime | None:
        """Ensure expiration is in the future if set."""
        if v is not None and v <= datetime.utcnow():
            raise ValueError("expires_at must be in the future")
        return v

    def to_response(self) -> APIKeyResponse:
        """Convert to response model (excludes secret key)."""
        return APIKeyResponse(
            api_key_id=self.api_key_id,
            organizer_id=self.organizer_id,
            hackathon_id=self.hackathon_id,
            tier=self.tier,
            rate_limit_per_second=self.rate_limit_per_second,
            daily_quota=self.daily_quota,
            budget_limit_usd=self.budget_limit_usd,
            active=self.active,
            created_at=self.created_at,
            updated_at=self.updated_at,
            expires_at=self.expires_at,
            deprecated=self.deprecated,
            deprecated_at=self.deprecated_at,
            total_requests=self.total_requests,
            total_cost_usd=self.total_cost_usd,
            last_used_at=self.last_used_at,
        )

    def to_create_response(self) -> APIKeyCreateResponse:
        """Convert to creation response model (includes secret key once)."""
        return APIKeyCreateResponse(
            api_key=self.api_key,
            api_key_id=self.api_key_id,
            organizer_id=self.organizer_id,
            hackathon_id=self.hackathon_id,
            tier=self.tier,
            rate_limit_per_second=self.rate_limit_per_second,
            daily_quota=self.daily_quota,
            budget_limit_usd=self.budget_limit_usd,
            active=self.active,
            created_at=self.created_at,
            updated_at=self.updated_at,
            expires_at=self.expires_at,
            deprecated=self.deprecated,
            deprecated_at=self.deprecated_at,
            total_requests=self.total_requests,
            total_cost_usd=self.total_cost_usd,
            last_used_at=self.last_used_at,
        )

    def set_dynamodb_keys(self) -> None:
        """Set DynamoDB partition and sort keys."""
        self.PK = f"APIKEY#{self.api_key_id}"
        self.SK = "METADATA"
        self.GSI1PK = f"ORG#{self.organizer_id}"
        self.GSI1SK = f"APIKEY#{self.created_at.isoformat()}"
        if self.hackathon_id:
            self.GSI2PK = f"HACKATHON#{self.hackathon_id}"
            self.GSI2SK = f"APIKEY#{self.api_key_id}"

    def is_valid(self) -> bool:
        """Check if API key is currently valid."""
        if not self.active:
            return False
        if self.expires_at and self.expires_at <= datetime.utcnow():
            return False
        return True

    def is_expired(self) -> bool:
        """Check if API key has expired."""
        if self.expires_at is None:
            return False
        return self.expires_at <= datetime.utcnow()


# ============================================================
# HELPER FUNCTIONS
# ============================================================


def get_tier_defaults(tier: Tier) -> dict[str, int | float]:
    """Get default rate limit, quota, and budget for a tier."""
    return TIER_DEFAULTS[tier].copy()


def validate_api_key_format(api_key: str) -> bool:
    """Validate API key format without raising exception."""
    return bool(API_KEY_PATTERN.match(api_key))
