"""Unit tests for API key models."""

from datetime import datetime, timedelta

import pytest
from pydantic import ValidationError

from src.models.api_key import (
    APIKey,
    APIKeyCreate,
    APIKeyCreateResponse,
    APIKeyListResponse,
    APIKeyResponse,
    get_tier_defaults,
    validate_api_key_format,
)
from src.models.common import Tier


class TestAPIKeyCreate:
    """Tests for APIKeyCreate request model."""

    def test_create_with_defaults(self) -> None:
        """Test creating API key request with default values."""
        request = APIKeyCreate()
        assert request.tier == Tier.FREE
        assert request.hackathon_id is None
        assert request.expires_at is None
        assert request.rate_limit_per_second is None
        assert request.daily_quota is None
        assert request.budget_limit_usd is None

    def test_create_with_custom_values(self) -> None:
        """Test creating API key request with custom values."""
        future_date = datetime.utcnow() + timedelta(days=30)
        request = APIKeyCreate(
            hackathon_id="HACK#123",
            tier=Tier.PRO,
            expires_at=future_date,
            rate_limit_per_second=20,
            daily_quota=5000,
            budget_limit_usd=500.0,
        )
        assert request.tier == Tier.PRO
        assert request.hackathon_id == "HACK#123"
        assert request.expires_at == future_date
        assert request.rate_limit_per_second == 20
        assert request.daily_quota == 5000
        assert request.budget_limit_usd == 500.0

    def test_expires_at_must_be_future(self) -> None:
        """Test that expires_at must be in the future."""
        past_date = datetime.utcnow() - timedelta(days=1)
        with pytest.raises(ValidationError) as exc_info:
            APIKeyCreate(expires_at=past_date)
        assert "expires_at must be in the future" in str(exc_info.value)

    def test_rate_limit_must_be_positive(self) -> None:
        """Test that rate_limit_per_second must be > 0."""
        with pytest.raises(ValidationError):
            APIKeyCreate(rate_limit_per_second=0)
        with pytest.raises(ValidationError):
            APIKeyCreate(rate_limit_per_second=-1)

    def test_daily_quota_must_be_positive(self) -> None:
        """Test that daily_quota must be > 0."""
        with pytest.raises(ValidationError):
            APIKeyCreate(daily_quota=0)
        with pytest.raises(ValidationError):
            APIKeyCreate(daily_quota=-1)

    def test_budget_limit_must_be_non_negative(self) -> None:
        """Test that budget_limit_usd must be >= 0."""
        request = APIKeyCreate(budget_limit_usd=0.0)
        assert request.budget_limit_usd == 0.0
        with pytest.raises(ValidationError):
            APIKeyCreate(budget_limit_usd=-1.0)


class TestAPIKeyResponse:
    """Tests for APIKeyResponse model."""

    def test_response_excludes_secret_key(self) -> None:
        """Test that APIKeyResponse does not include secret key field."""
        response = APIKeyResponse(
            api_key_id="01HQ123456789",
            organizer_id="ORG#123",
            tier=Tier.FREE,
            rate_limit_per_second=2,
            daily_quota=100,
            budget_limit_usd=10.0,
            active=True,
        )
        # Verify secret key is not in the model
        assert not hasattr(response, "api_key")
        assert response.api_key_id == "01HQ123456789"


class TestAPIKeyCreateResponse:
    """Tests for APIKeyCreateResponse model."""

    def test_create_response_includes_secret_key(self) -> None:
        """Test that APIKeyCreateResponse includes secret key."""
        response = APIKeyCreateResponse(
            api_key="vj_test_abc123def456ghi789jkl012mno34pqr",
            api_key_id="01HQ123456789",
            organizer_id="ORG#123",
            tier=Tier.FREE,
            rate_limit_per_second=2,
            daily_quota=100,
            budget_limit_usd=10.0,
            active=True,
        )
        assert response.api_key == "vj_test_abc123def456ghi789jkl012mno34pqr"
        assert response._warning == "Store your API key securely. It will not be shown again."


class TestAPIKeyListResponse:
    """Tests for APIKeyListResponse model."""

    def test_list_response(self) -> None:
        """Test API key list response."""
        keys = [
            APIKeyResponse(
                api_key_id="01HQ123456789",
                organizer_id="ORG#123",
                tier=Tier.FREE,
                rate_limit_per_second=2,
                daily_quota=100,
                budget_limit_usd=10.0,
                active=True,
            ),
            APIKeyResponse(
                api_key_id="01HQ987654321",
                organizer_id="ORG#123",
                tier=Tier.PRO,
                rate_limit_per_second=10,
                daily_quota=2500,
                budget_limit_usd=250.0,
                active=True,
            ),
        ]
        response = APIKeyListResponse(api_keys=keys, total=2)
        assert len(response.api_keys) == 2
        assert response.total == 2


class TestAPIKey:
    """Tests for APIKey internal model."""

    def test_valid_api_key_format(self) -> None:
        """Test that valid API key formats are accepted."""
        valid_keys = [
            "vj_live_abc123def456ghi789jkl012mno34pqr",
            "vj_test_ABC123DEF456GHI789JKL012MNO34PQR",
            "vj_live_abcdefghijklmnopqrstuvwxyz1234ab",
            "vj_test_ABCDEFGHIJKLMNOPQRSTUVWXYZ1234AB",
            "vj_live_abc+def/ghi+jkl/mno+pqr/stu+vwxy",
        ]
        for key in valid_keys:
            api_key = APIKey(
                api_key_id="01HQ123456789",
                api_key=key,
                organizer_id="ORG#123",
                tier=Tier.FREE,
                rate_limit_per_second=2,
                daily_quota=100,
                budget_limit_usd=10.0,
            )
            assert api_key.api_key == key

    def test_invalid_api_key_format(self) -> None:
        """Test that invalid API key formats are rejected."""
        invalid_keys = [
            "vj_prod_abc123def456ghi789jkl012mno345",  # Wrong env
            "vj_live_abc123",  # Too short
            "vj_live_abc123def456ghi789jkl012mno34pqrextra",  # Too long
            "live_abc123def456ghi789jkl012mno345pqr",  # Missing prefix
            "vj_live_abc123def456ghi789jkl012mno34",  # 31 chars instead of 32
            "vj_live_abc123def456ghi789jkl012mno34@",  # Invalid char
        ]
        for key in invalid_keys:
            with pytest.raises(ValidationError) as exc_info:
                APIKey(
                    api_key_id="01HQ123456789",
                    api_key=key,
                    organizer_id="ORG#123",
                    tier=Tier.FREE,
                    rate_limit_per_second=2,
                    daily_quota=100,
                    budget_limit_usd=10.0,
                )
            assert "API key must match format" in str(exc_info.value)

    def test_set_dynamodb_keys(self) -> None:
        """Test DynamoDB key generation."""
        api_key = APIKey(
            api_key_id="01HQ123456789",
            api_key="vj_test_abc123def456ghi789jkl012mno34pqr",
            organizer_id="ORG#123",
            hackathon_id="HACK#456",
            tier=Tier.FREE,
            rate_limit_per_second=2,
            daily_quota=100,
            budget_limit_usd=10.0,
        )
        api_key.set_dynamodb_keys()

        assert api_key.PK == "APIKEY#01HQ123456789"
        assert api_key.SK == "METADATA"
        assert api_key.GSI1PK == "ORG#ORG#123"
        assert api_key.GSI1SK.startswith("APIKEY#")
        assert api_key.GSI2PK == "HACKATHON#HACK#456"
        assert api_key.GSI2SK == "APIKEY#01HQ123456789"

    def test_set_dynamodb_keys_without_hackathon(self) -> None:
        """Test DynamoDB key generation without hackathon_id."""
        api_key = APIKey(
            api_key_id="01HQ123456789",
            api_key="vj_test_abc123def456ghi789jkl012mno34pqr",
            organizer_id="ORG#123",
            tier=Tier.FREE,
            rate_limit_per_second=2,
            daily_quota=100,
            budget_limit_usd=10.0,
        )
        api_key.set_dynamodb_keys()

        assert api_key.PK == "APIKEY#01HQ123456789"
        assert api_key.SK == "METADATA"
        assert api_key.GSI1PK == "ORG#ORG#123"
        assert api_key.GSI2PK == ""  # Not set without hackathon_id

    def test_is_valid_active_key(self) -> None:
        """Test is_valid() for active, non-expired key."""
        api_key = APIKey(
            api_key_id="01HQ123456789",
            api_key="vj_test_abc123def456ghi789jkl012mno34pqr",
            organizer_id="ORG#123",
            tier=Tier.FREE,
            rate_limit_per_second=2,
            daily_quota=100,
            budget_limit_usd=10.0,
            active=True,
            expires_at=datetime.utcnow() + timedelta(days=30),
        )
        assert api_key.is_valid() is True

    def test_is_valid_inactive_key(self) -> None:
        """Test is_valid() for inactive key."""
        api_key = APIKey(
            api_key_id="01HQ123456789",
            api_key="vj_test_abc123def456ghi789jkl012mno34pqr",
            organizer_id="ORG#123",
            tier=Tier.FREE,
            rate_limit_per_second=2,
            daily_quota=100,
            budget_limit_usd=10.0,
            active=False,
        )
        assert api_key.is_valid() is False

    def test_is_valid_expired_key(self) -> None:
        """Test is_valid() for expired key."""
        api_key = APIKey(
            api_key_id="01HQ123456789",
            api_key="vj_test_abc123def456ghi789jkl012mno34pqr",
            organizer_id="ORG#123",
            tier=Tier.FREE,
            rate_limit_per_second=2,
            daily_quota=100,
            budget_limit_usd=10.0,
            active=True,
            expires_at=datetime.utcnow() - timedelta(days=1),
        )
        assert api_key.is_valid() is False

    def test_is_expired(self) -> None:
        """Test is_expired() method."""
        # Not expired
        api_key = APIKey(
            api_key_id="01HQ123456789",
            api_key="vj_test_abc123def456ghi789jkl012mno34pqr",
            organizer_id="ORG#123",
            tier=Tier.FREE,
            rate_limit_per_second=2,
            daily_quota=100,
            budget_limit_usd=10.0,
            expires_at=datetime.utcnow() + timedelta(days=30),
        )
        assert api_key.is_expired() is False

        # Expired
        api_key.expires_at = datetime.utcnow() - timedelta(days=1)
        assert api_key.is_expired() is True

        # No expiration
        api_key.expires_at = None
        assert api_key.is_expired() is False

    def test_to_response(self) -> None:
        """Test conversion to APIKeyResponse."""
        api_key = APIKey(
            api_key_id="01HQ123456789",
            api_key="vj_test_abc123def456ghi789jkl012mno34pqr",
            organizer_id="ORG#123",
            tier=Tier.FREE,
            rate_limit_per_second=2,
            daily_quota=100,
            budget_limit_usd=10.0,
            active=True,
        )
        response = api_key.to_response()

        assert isinstance(response, APIKeyResponse)
        assert response.api_key_id == "01HQ123456789"
        assert not hasattr(response, "api_key")  # Secret key excluded

    def test_to_create_response(self) -> None:
        """Test conversion to APIKeyCreateResponse."""
        api_key = APIKey(
            api_key_id="01HQ123456789",
            api_key="vj_test_abc123def456ghi789jkl012mno34pqr",
            organizer_id="ORG#123",
            tier=Tier.FREE,
            rate_limit_per_second=2,
            daily_quota=100,
            budget_limit_usd=10.0,
            active=True,
        )
        response = api_key.to_create_response()

        assert isinstance(response, APIKeyCreateResponse)
        assert response.api_key == "vj_test_abc123def456ghi789jkl012mno34pqr"
        assert response.api_key_id == "01HQ123456789"


class TestHelperFunctions:
    """Tests for helper functions."""

    def test_get_tier_defaults_free(self) -> None:
        """Test tier defaults for FREE tier."""
        defaults = get_tier_defaults(Tier.FREE)
        assert defaults["rate_limit_per_second"] == 2
        assert defaults["daily_quota"] == 100
        assert defaults["budget_limit_usd"] == 10.0

    def test_get_tier_defaults_starter(self) -> None:
        """Test tier defaults for STARTER tier."""
        defaults = get_tier_defaults(Tier.STARTER)
        assert defaults["rate_limit_per_second"] == 5
        assert defaults["daily_quota"] == 500
        assert defaults["budget_limit_usd"] == 50.0

    def test_get_tier_defaults_pro(self) -> None:
        """Test tier defaults for PRO tier."""
        defaults = get_tier_defaults(Tier.PRO)
        assert defaults["rate_limit_per_second"] == 10
        assert defaults["daily_quota"] == 2500
        assert defaults["budget_limit_usd"] == 250.0

    def test_get_tier_defaults_enterprise(self) -> None:
        """Test tier defaults for ENTERPRISE tier."""
        defaults = get_tier_defaults(Tier.ENTERPRISE)
        assert defaults["rate_limit_per_second"] == 50
        assert defaults["daily_quota"] == 999999
        assert defaults["budget_limit_usd"] == 10000.0

    def test_get_tier_defaults_returns_copy(self) -> None:
        """Test that get_tier_defaults returns a copy, not reference."""
        defaults1 = get_tier_defaults(Tier.FREE)
        defaults2 = get_tier_defaults(Tier.FREE)
        defaults1["rate_limit_per_second"] = 999
        assert defaults2["rate_limit_per_second"] == 2  # Not modified

    def test_validate_api_key_format_valid(self) -> None:
        """Test validate_api_key_format with valid keys."""
        valid_keys = [
            "vj_live_abc123def456ghi789jkl012mno34pqr",
            "vj_test_ABC123DEF456GHI789JKL012MNO34PQR",
            "vj_live_abcdefghijklmnopqrstuvwxyz123456",
        ]
        for key in valid_keys:
            assert validate_api_key_format(key) is True

    def test_validate_api_key_format_invalid(self) -> None:
        """Test validate_api_key_format with invalid keys."""
        invalid_keys = [
            "vj_prod_abc123def456ghi789jkl012mno345",
            "vj_live_abc123",
            "invalid_key",
            "",
        ]
        for key in invalid_keys:
            assert validate_api_key_format(key) is False


class TestAPIKeyValidation:
    """Tests for API key validation rules."""

    def test_rate_limit_must_be_positive(self) -> None:
        """Test that rate_limit_per_second must be > 0."""
        with pytest.raises(ValidationError):
            APIKey(
                api_key_id="01HQ123456789",
                api_key="vj_test_abc123def456ghi789jkl012mno34pqr",
                organizer_id="ORG#123",
                tier=Tier.FREE,
                rate_limit_per_second=0,
                daily_quota=100,
                budget_limit_usd=10.0,
            )

    def test_daily_quota_must_be_positive(self) -> None:
        """Test that daily_quota must be > 0."""
        with pytest.raises(ValidationError):
            APIKey(
                api_key_id="01HQ123456789",
                api_key="vj_test_abc123def456ghi789jkl012mno34pqr",
                organizer_id="ORG#123",
                tier=Tier.FREE,
                rate_limit_per_second=2,
                daily_quota=0,
                budget_limit_usd=10.0,
            )

    def test_budget_limit_must_be_non_negative(self) -> None:
        """Test that budget_limit_usd must be >= 0."""
        # Valid: 0.0
        api_key = APIKey(
            api_key_id="01HQ123456789",
            api_key="vj_test_abc123def456ghi789jkl012mno34pqr",
            organizer_id="ORG#123",
            tier=Tier.FREE,
            rate_limit_per_second=2,
            daily_quota=100,
            budget_limit_usd=0.0,
        )
        assert api_key.budget_limit_usd == 0.0

        # Invalid: negative
        with pytest.raises(ValidationError):
            APIKey(
                api_key_id="01HQ123456789",
                api_key="vj_test_abc123def456ghi789jkl012mno34pqr",
                organizer_id="ORG#123",
                tier=Tier.FREE,
                rate_limit_per_second=2,
                daily_quota=100,
                budget_limit_usd=-1.0,
            )

    def test_total_requests_must_be_non_negative(self) -> None:
        """Test that total_requests must be >= 0."""
        with pytest.raises(ValidationError):
            APIKey(
                api_key_id="01HQ123456789",
                api_key="vj_test_abc123def456ghi789jkl012mno34pqr",
                organizer_id="ORG#123",
                tier=Tier.FREE,
                rate_limit_per_second=2,
                daily_quota=100,
                budget_limit_usd=10.0,
                total_requests=-1,
            )

    def test_total_cost_must_be_non_negative(self) -> None:
        """Test that total_cost_usd must be >= 0."""
        with pytest.raises(ValidationError):
            APIKey(
                api_key_id="01HQ123456789",
                api_key="vj_test_abc123def456ghi789jkl012mno34pqr",
                organizer_id="ORG#123",
                tier=Tier.FREE,
                rate_limit_per_second=2,
                daily_quota=100,
                budget_limit_usd=10.0,
                total_cost_usd=-1.0,
            )
