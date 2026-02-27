"""Unit tests for API key service."""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from src.models.api_key import Tier
from src.services.api_key_service import APIKeyService


@pytest.fixture
def mock_db():
    """Create mock DynamoDB helper."""
    db = MagicMock()
    db.table = MagicMock()
    db._serialize_item = MagicMock(side_effect=lambda x: x)
    return db


@pytest.fixture
def api_key_service(mock_db):
    """Create API key service with mock DB."""
    return APIKeyService(db_helper=mock_db, environment="test")


class TestAPIKeyGeneration:
    """Tests for API key generation."""

    def test_generate_secure_key_format(self, api_key_service):
        """Test that generated keys match the required format."""
        key = api_key_service._generate_secure_key()

        # Check format: vj_test_{32-char-base64}
        assert key.startswith("vj_test_")
        parts = key.split("_")
        assert len(parts) == 3
        assert parts[1] == "test"
        assert len(parts[2]) == 32

    def test_generate_secure_key_uniqueness(self, api_key_service):
        """Test that generated keys are unique."""
        keys = [api_key_service._generate_secure_key() for _ in range(1000)]
        assert len(keys) == len(set(keys)), "Generated keys should be unique"

    def test_generate_secure_key_base64_chars(self, api_key_service):
        """Test that generated keys use valid base64 characters."""
        key = api_key_service._generate_secure_key()
        base64_part = key.split("_")[2]

        # URL-safe base64 uses: A-Z, a-z, 0-9, -, _
        valid_chars = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_+/")
        assert all(c in valid_chars for c in base64_part)

    def test_generate_secure_key_live_environment(self, mock_db):
        """Test key generation with live environment."""
        service = APIKeyService(db_helper=mock_db, environment="live")
        key = service._generate_secure_key()

        assert key.startswith("vj_live_")


class TestCreateAPIKey:
    """Tests for API key creation."""

    @patch("src.services.api_key_service.generate_id")
    def test_create_api_key_with_defaults(self, mock_generate_id, api_key_service, mock_db):
        """Test creating API key with tier defaults."""
        mock_generate_id.return_value = "test_key_id_123"
        mock_db.table.put_item.return_value = None

        result = api_key_service.create_api_key(
            organizer_id="org_123",
            tier=Tier.FREE,
        )

        # Check response
        assert result.api_key_id == "test_key_id_123"
        assert result.api_key.startswith("vj_test_")
        assert result.organizer_id == "org_123"
        assert result.tier == Tier.FREE
        assert result.rate_limit_per_second == 2  # FREE tier default
        assert result.daily_quota == 100  # FREE tier default
        assert result.budget_limit_usd == 10.0  # FREE tier default
        assert result.active is True
        assert result.deprecated is False

        # Check DB was called
        mock_db.table.put_item.assert_called_once()

    @patch("src.services.api_key_service.generate_id")
    def test_create_api_key_with_custom_limits(self, mock_generate_id, api_key_service, mock_db):
        """Test creating API key with custom limits."""
        mock_generate_id.return_value = "test_key_id_456"
        mock_db.table.put_item.return_value = None

        result = api_key_service.create_api_key(
            organizer_id="org_456",
            tier=Tier.PRO,
            rate_limit=20,
            daily_quota=5000,
            budget_limit_usd=500.0,
        )

        # Check custom limits were used
        assert result.rate_limit_per_second == 20
        assert result.daily_quota == 5000
        assert result.budget_limit_usd == 500.0

    @patch("src.services.api_key_service.generate_id")
    def test_create_api_key_with_hackathon_scope(self, mock_generate_id, api_key_service, mock_db):
        """Test creating API key scoped to hackathon."""
        mock_generate_id.return_value = "test_key_id_789"
        mock_db.table.put_item.return_value = None

        result = api_key_service.create_api_key(
            organizer_id="org_789",
            hackathon_id="hack_123",
            tier=Tier.STARTER,
        )

        assert result.hackathon_id == "hack_123"

    @patch("src.services.api_key_service.generate_id")
    def test_create_api_key_with_expiration(self, mock_generate_id, api_key_service, mock_db):
        """Test creating API key with expiration."""
        mock_generate_id.return_value = "test_key_id_exp"
        mock_db.table.put_item.return_value = None

        expires_at = datetime.utcnow() + timedelta(days=30)
        result = api_key_service.create_api_key(
            organizer_id="org_exp",
            tier=Tier.FREE,
            expires_at=expires_at,
        )

        assert result.expires_at == expires_at

    @patch("src.services.api_key_service.generate_id")
    def test_create_api_key_db_failure(self, mock_generate_id, api_key_service, mock_db):
        """Test handling of database failure during creation."""
        mock_generate_id.return_value = "test_key_id_fail"
        mock_db.table.put_item.side_effect = Exception("DB error")

        with pytest.raises(RuntimeError, match="Failed to create API key"):
            api_key_service.create_api_key(
                organizer_id="org_fail",
                tier=Tier.FREE,
            )


class TestValidateAPIKey:
    """Tests for API key validation."""

    def test_validate_api_key_success(self, api_key_service, mock_db):
        """Test successful API key validation."""
        now = datetime.utcnow()
        mock_db.table.scan.return_value = {
            "Items": [
                {
                    "api_key_id": "key_123",
                    "api_key": "vj_test_abcdefghijklmnopqrstuvwxyz12",
                    "organizer_id": "org_123",
                    "tier": "free",
                    "rate_limit_per_second": 2,
                    "daily_quota": 100,
                    "budget_limit_usd": 10.0,
                    "active": True,
                    "created_at": now,
                    "updated_at": now,
                    "deprecated": False,
                    "total_requests": 0,
                    "total_cost_usd": 0.0,
                }
            ]
        }

        result = api_key_service.validate_api_key("vj_test_abcdefghijklmnopqrstuvwxyz12")

        assert result is not None
        assert result.api_key_id == "key_123"
        assert result.active is True

    def test_validate_api_key_not_found(self, api_key_service, mock_db):
        """Test validation of non-existent API key."""
        mock_db.table.scan.return_value = {"Items": []}

        result = api_key_service.validate_api_key("vj_test_nonexistent")

        assert result is None

    def test_validate_api_key_inactive(self, api_key_service, mock_db):
        """Test validation of inactive API key."""
        now = datetime.utcnow()
        mock_db.table.scan.return_value = {
            "Items": [
                {
                    "api_key_id": "key_inactive",
                    "api_key": "vj_test_inactivekey1234567890abcd",
                    "organizer_id": "org_123",
                    "tier": "free",
                    "rate_limit_per_second": 2,
                    "daily_quota": 100,
                    "budget_limit_usd": 10.0,
                    "active": False,  # Inactive
                    "created_at": now,
                    "updated_at": now,
                    "deprecated": False,
                    "total_requests": 0,
                    "total_cost_usd": 0.0,
                }
            ]
        }

        result = api_key_service.validate_api_key("vj_test_inactivekey1234567890abcd")

        assert result is None

    def test_validate_api_key_expired(self, api_key_service, mock_db):
        """Test validation of expired API key."""
        now = datetime.utcnow()
        past = now - timedelta(days=1)
        mock_db.table.scan.return_value = {
            "Items": [
                {
                    "api_key_id": "key_expired",
                    "api_key": "vj_test_expiredkey1234567890abcd",
                    "organizer_id": "org_123",
                    "tier": "free",
                    "rate_limit_per_second": 2,
                    "daily_quota": 100,
                    "budget_limit_usd": 10.0,
                    "active": True,
                    "created_at": now,
                    "updated_at": now,
                    "expires_at": past,  # Expired
                    "deprecated": False,
                    "total_requests": 0,
                    "total_cost_usd": 0.0,
                }
            ]
        }

        result = api_key_service.validate_api_key("vj_test_expiredkey1234567890abcd")

        assert result is None


class TestRotateAPIKey:
    """Tests for API key rotation."""

    @patch("src.services.api_key_service.generate_id")
    def test_rotate_api_key_success(self, mock_generate_id, api_key_service, mock_db):
        """Test successful API key rotation."""
        mock_generate_id.return_value = "new_key_id"
        now = datetime.utcnow()

        # Mock getting old key
        mock_db.table.get_item.return_value = {
            "Item": {
                "api_key_id": "old_key_id",
                "api_key": "vj_test_oldkey1234567890abcdefgh",
                "organizer_id": "org_123",
                "hackathon_id": "hack_123",
                "tier": "pro",
                "rate_limit_per_second": 10,
                "daily_quota": 2500,
                "budget_limit_usd": 250.0,
                "active": True,
                "created_at": now,
                "updated_at": now,
                "deprecated": False,
                "total_requests": 100,
                "total_cost_usd": 5.0,
            }
        }

        # Mock creating new key
        mock_db.table.put_item.return_value = None
        mock_db.table.update_item.return_value = None

        new_key, old_key = api_key_service.rotate_api_key("old_key_id")

        # Check new key
        assert new_key.api_key_id == "new_key_id"
        assert new_key.organizer_id == "org_123"
        assert new_key.tier == Tier.PRO
        assert new_key.active is True
        assert new_key.deprecated is False

        # Check old key
        assert old_key.api_key_id == "old_key_id"
        assert old_key.deprecated is True
        assert old_key.deprecated_at is not None

        # Check update was called
        mock_db.table.update_item.assert_called_once()

    def test_rotate_api_key_not_found(self, api_key_service, mock_db):
        """Test rotation of non-existent API key."""
        mock_db.table.get_item.return_value = {}

        with pytest.raises(ValueError, match="API key not found"):
            api_key_service.rotate_api_key("nonexistent_key")


class TestRevokeAPIKey:
    """Tests for API key revocation."""

    def test_revoke_api_key_success(self, api_key_service, mock_db):
        """Test successful API key revocation."""
        mock_db.table.update_item.return_value = None

        result = api_key_service.revoke_api_key("key_to_revoke")

        assert result is True
        mock_db.table.update_item.assert_called_once()

        # Check that active was set to False
        call_args = mock_db.table.update_item.call_args
        assert call_args[1]["ExpressionAttributeValues"][":active"] is False

    def test_revoke_api_key_failure(self, api_key_service, mock_db):
        """Test handling of revocation failure."""
        mock_db.table.update_item.side_effect = Exception("DB error")

        result = api_key_service.revoke_api_key("key_to_revoke")

        assert result is False


class TestListAPIKeys:
    """Tests for listing API keys."""

    def test_list_api_keys_success(self, api_key_service, mock_db):
        """Test successful listing of API keys."""
        now = datetime.utcnow()
        mock_db.table.query.return_value = {
            "Items": [
                {
                    "api_key_id": "key_1",
                    "api_key": "vj_test_key1234567890abcdefghijk",
                    "organizer_id": "org_123",
                    "tier": "free",
                    "rate_limit_per_second": 2,
                    "daily_quota": 100,
                    "budget_limit_usd": 10.0,
                    "active": True,
                    "created_at": now,
                    "updated_at": now,
                    "deprecated": False,
                    "total_requests": 10,
                    "total_cost_usd": 0.5,
                },
                {
                    "api_key_id": "key_2",
                    "api_key": "vj_test_key2345678901bcdefghijkl",
                    "organizer_id": "org_123",
                    "tier": "pro",
                    "rate_limit_per_second": 10,
                    "daily_quota": 2500,
                    "budget_limit_usd": 250.0,
                    "active": True,
                    "created_at": now,
                    "updated_at": now,
                    "deprecated": False,
                    "total_requests": 50,
                    "total_cost_usd": 2.5,
                },
            ]
        }

        result = api_key_service.list_api_keys("org_123")

        assert result.total == 2
        assert len(result.api_keys) == 2
        assert result.api_keys[0].api_key_id == "key_1"
        assert result.api_keys[1].api_key_id == "key_2"

    def test_list_api_keys_empty(self, api_key_service, mock_db):
        """Test listing when no API keys exist."""
        mock_db.table.query.return_value = {"Items": []}

        result = api_key_service.list_api_keys("org_no_keys")

        assert result.total == 0
        assert len(result.api_keys) == 0

    def test_list_api_keys_db_error(self, api_key_service, mock_db):
        """Test handling of database error during listing."""
        mock_db.table.query.side_effect = Exception("DB error")

        result = api_key_service.list_api_keys("org_error")

        assert result.total == 0
        assert len(result.api_keys) == 0


class TestGetAPIKeyByID:
    """Tests for getting API key by ID."""

    def test_get_api_key_by_id_success(self, api_key_service, mock_db):
        """Test successful retrieval of API key by ID."""
        now = datetime.utcnow()
        mock_db.table.get_item.return_value = {
            "Item": {
                "api_key_id": "key_123",
                "api_key": "vj_test_key123456789abcdefghijkl",
                "organizer_id": "org_123",
                "tier": "starter",
                "rate_limit_per_second": 5,
                "daily_quota": 500,
                "budget_limit_usd": 50.0,
                "active": True,
                "created_at": now,
                "updated_at": now,
                "deprecated": False,
                "total_requests": 25,
                "total_cost_usd": 1.25,
            }
        }

        result = api_key_service.get_api_key_by_id("key_123")

        assert result is not None
        assert result.api_key_id == "key_123"
        assert result.tier == Tier.STARTER

    def test_get_api_key_by_id_not_found(self, api_key_service, mock_db):
        """Test retrieval of non-existent API key."""
        mock_db.table.get_item.return_value = {}

        result = api_key_service.get_api_key_by_id("nonexistent")

        assert result is None

    def test_get_api_key_by_id_db_error(self, api_key_service, mock_db):
        """Test handling of database error during retrieval."""
        mock_db.table.get_item.side_effect = Exception("DB error")

        result = api_key_service.get_api_key_by_id("key_error")

        assert result is None


class TestHelperFunctions:
    """Tests for helper functions."""

    def test_get_default_limits_for_tier_free(self):
        """Test getting default limits for FREE tier."""
        from src.services.api_key_service import get_default_limits_for_tier

        limits = get_default_limits_for_tier(Tier.FREE)

        assert limits["rate_limit_per_second"] == 2
        assert limits["daily_quota"] == 100
        assert limits["budget_limit_usd"] == 10.0

    def test_get_default_limits_for_tier_enterprise(self):
        """Test getting default limits for ENTERPRISE tier."""
        from src.services.api_key_service import get_default_limits_for_tier

        limits = get_default_limits_for_tier(Tier.ENTERPRISE)

        assert limits["rate_limit_per_second"] == 50
        assert limits["daily_quota"] == 999999
        assert limits["budget_limit_usd"] == 10000.0
