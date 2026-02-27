"""Integration tests for API key management endpoints.

Tests the following endpoints:
- POST /api/v1/api-keys (create API key)
- GET /api/v1/api-keys (list API keys)
- GET /api/v1/api-keys/{key_id} (get API key details)
- POST /api/v1/api-keys/{key_id}/rotate (rotate API key)
- DELETE /api/v1/api-keys/{key_id} (revoke API key)
"""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.models.api_key import (
    APIKey,
    APIKeyListResponse,
    Tier,
)

# ============================================================
# FIXTURES
# ============================================================


@pytest.fixture
def mock_aws_credentials(monkeypatch):
    """Mock AWS credentials to prevent boto3 from trying to load real credentials."""
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SECURITY_TOKEN", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("TABLE_NAME", "VibeJudgeTable")


@pytest.fixture
def mock_services(mock_aws_credentials):
    """Mock all service dependencies."""
    with (
        patch("src.api.dependencies.get_organizer_service") as mock_org_service,
        patch("src.api.routes.api_keys.get_api_key_service") as mock_api_key_service,
    ):
        # Mock organizer service for auth
        org_service = MagicMock()
        org_service.verify_api_key.return_value = "org_123"
        org_service.get_organizer.return_value = MagicMock(
            org_id="org_123",
            email="test@example.com",
            model_dump=lambda: {"org_id": "org_123", "email": "test@example.com"},
        )
        mock_org_service.return_value = org_service

        # Mock API key service
        api_key_service = MagicMock()
        mock_api_key_service.return_value = api_key_service

        yield {
            "organizer": org_service,
            "api_key": api_key_service,
        }


@pytest.fixture
def sample_api_key():
    """Sample API key for testing."""
    now = datetime.utcnow()
    return APIKey(
        api_key_id="key_123",
        api_key="vj_live_abcdefghijklmnopqrstuvwxyz123456",
        organizer_id="org_123",
        hackathon_id=None,
        tier=Tier.FREE,
        rate_limit_per_second=2,
        daily_quota=100,
        budget_limit_usd=10.0,
        active=True,
        created_at=now,
        updated_at=now,
        expires_at=None,
        deprecated=False,
        total_requests=0,
        total_cost_usd=0.0,
    )


@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)


# ============================================================
# TESTS: CREATE API KEY
# ============================================================


def test_create_api_key_success(client, mock_services, sample_api_key):
    """Test successful API key creation."""
    # Setup mock
    create_response = sample_api_key.to_create_response()
    mock_services["api_key"].create_api_key.return_value = create_response

    # Make request
    response = client.post(
        "/api/v1/api-keys",
        json={
            "tier": "FREE",
            "hackathon_id": None,
            "expires_at": None,
        },
        headers={"X-API-Key": "test_key"},
    )

    # Assertions
    assert response.status_code == 201
    data = response.json()
    assert data["api_key_id"] == "key_123"
    assert data["api_key"] == "vj_live_abcdefghijklmnopqrstuvwxyz123456"
    assert data["organizer_id"] == "org_123"
    assert data["tier"] == "FREE"
    assert data["rate_limit_per_second"] == 2
    assert data["daily_quota"] == 100
    assert data["budget_limit_usd"] == 10.0
    assert data["active"] is True

    # Verify service was called correctly
    mock_services["api_key"].create_api_key.assert_called_once()
    call_kwargs = mock_services["api_key"].create_api_key.call_args.kwargs
    assert call_kwargs["organizer_id"] == "org_123"
    assert call_kwargs["tier"] == Tier.FREE


def test_create_api_key_with_custom_limits(client, mock_services, sample_api_key):
    """Test API key creation with custom rate limits and quota."""
    # Setup mock with custom limits
    custom_key = sample_api_key.model_copy()
    custom_key.rate_limit_per_second = 10
    custom_key.daily_quota = 500
    custom_key.budget_limit_usd = 50.0
    create_response = custom_key.to_create_response()
    mock_services["api_key"].create_api_key.return_value = create_response

    # Make request
    response = client.post(
        "/api/v1/api-keys",
        json={
            "tier": "PRO",
            "rate_limit_per_second": 10,
            "daily_quota": 500,
            "budget_limit_usd": 50.0,
        },
        headers={"X-API-Key": "test_key"},
    )

    # Assertions
    assert response.status_code == 201
    data = response.json()
    assert data["rate_limit_per_second"] == 10
    assert data["daily_quota"] == 500
    assert data["budget_limit_usd"] == 50.0


def test_create_api_key_with_expiration(client, mock_services, sample_api_key):
    """Test API key creation with expiration date."""
    # Setup mock with expiration
    expires_at = datetime.utcnow() + timedelta(days=30)
    custom_key = sample_api_key.model_copy()
    custom_key.expires_at = expires_at
    create_response = custom_key.to_create_response()
    mock_services["api_key"].create_api_key.return_value = create_response

    # Make request
    response = client.post(
        "/api/v1/api-keys",
        json={
            "tier": "FREE",
            "expires_at": expires_at.isoformat(),
        },
        headers={"X-API-Key": "test_key"},
    )

    # Assertions
    assert response.status_code == 201
    data = response.json()
    assert data["expires_at"] is not None


def test_create_api_key_missing_auth(client, mock_services):
    """Test API key creation without authentication."""
    response = client.post(
        "/api/v1/api-keys",
        json={"tier": "FREE"},
    )

    assert response.status_code == 401


def test_create_api_key_service_error(client, mock_services):
    """Test API key creation with service error."""
    # Setup mock to raise error
    mock_services["api_key"].create_api_key.side_effect = ValueError("Invalid tier")

    # Make request
    response = client.post(
        "/api/v1/api-keys",
        json={"tier": "INVALID"},
        headers={"X-API-Key": "test_key"},
    )

    # Assertions
    assert response.status_code == 400
    assert "Invalid tier" in response.json()["detail"]


# ============================================================
# TESTS: LIST API KEYS
# ============================================================


def test_list_api_keys_success(client, mock_services, sample_api_key):
    """Test successful API key listing."""
    # Setup mock
    api_key_response = sample_api_key.to_response()
    list_response = APIKeyListResponse(
        api_keys=[api_key_response],
        total=1,
    )
    mock_services["api_key"].list_api_keys.return_value = list_response

    # Make request
    response = client.get(
        "/api/v1/api-keys",
        headers={"X-API-Key": "test_key"},
    )

    # Assertions
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert len(data["api_keys"]) == 1
    assert data["api_keys"][0]["api_key_id"] == "key_123"
    # Secret key should not be in response
    assert "api_key" not in data["api_keys"][0]

    # Verify service was called correctly
    mock_services["api_key"].list_api_keys.assert_called_once_with("org_123")


def test_list_api_keys_empty(client, mock_services):
    """Test listing API keys when none exist."""
    # Setup mock
    list_response = APIKeyListResponse(api_keys=[], total=0)
    mock_services["api_key"].list_api_keys.return_value = list_response

    # Make request
    response = client.get(
        "/api/v1/api-keys",
        headers={"X-API-Key": "test_key"},
    )

    # Assertions
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert len(data["api_keys"]) == 0


def test_list_api_keys_missing_auth(client, mock_services):
    """Test listing API keys without authentication."""
    response = client.get("/api/v1/api-keys")

    assert response.status_code == 401


# ============================================================
# TESTS: GET API KEY BY ID
# ============================================================


def test_get_api_key_success(client, mock_services, sample_api_key):
    """Test successful API key retrieval by ID."""
    # Setup mock
    api_key_response = sample_api_key.to_response()
    mock_services["api_key"].get_api_key_by_id.return_value = api_key_response

    # Make request
    response = client.get(
        "/api/v1/api-keys/key_123",
        headers={"X-API-Key": "test_key"},
    )

    # Assertions
    assert response.status_code == 200
    data = response.json()
    assert data["api_key_id"] == "key_123"
    assert data["organizer_id"] == "org_123"
    # Secret key should not be in response
    assert "api_key" not in data

    # Verify service was called correctly
    mock_services["api_key"].get_api_key_by_id.assert_called_once_with("key_123")


def test_get_api_key_not_found(client, mock_services):
    """Test getting non-existent API key."""
    # Setup mock
    mock_services["api_key"].get_api_key_by_id.return_value = None

    # Make request
    response = client.get(
        "/api/v1/api-keys/nonexistent",
        headers={"X-API-Key": "test_key"},
    )

    # Assertions
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_get_api_key_wrong_owner(client, mock_services, sample_api_key):
    """Test getting API key owned by different organizer."""
    # Setup mock with different owner
    api_key_response = sample_api_key.to_response()
    api_key_response.organizer_id = "org_different"
    mock_services["api_key"].get_api_key_by_id.return_value = api_key_response

    # Make request
    response = client.get(
        "/api/v1/api-keys/key_123",
        headers={"X-API-Key": "test_key"},
    )

    # Assertions
    assert response.status_code == 403
    assert "permission" in response.json()["detail"].lower()


# ============================================================
# TESTS: ROTATE API KEY
# ============================================================


def test_rotate_api_key_success(client, mock_services, sample_api_key):
    """Test successful API key rotation."""
    # Setup mock
    existing_key_response = sample_api_key.to_response()
    mock_services["api_key"].get_api_key_by_id.return_value = existing_key_response

    # Create new key for rotation
    new_key = sample_api_key.model_copy()
    new_key.api_key_id = "key_new"
    new_key.api_key = "vj_live_newkeynewkeynewkeynewkeynewk"
    mock_services["api_key"].rotate_api_key.return_value = (new_key, sample_api_key)

    # Make request
    response = client.post(
        "/api/v1/api-keys/key_123/rotate",
        headers={"X-API-Key": "test_key"},
    )

    # Assertions
    assert response.status_code == 200
    data = response.json()
    assert data["api_key_id"] == "key_new"
    assert data["api_key"] == "vj_live_newkeynewkeynewkeynewkeynewk"

    # Verify service was called correctly
    mock_services["api_key"].rotate_api_key.assert_called_once_with("key_123")


def test_rotate_api_key_not_found(client, mock_services):
    """Test rotating non-existent API key."""
    # Setup mock
    mock_services["api_key"].get_api_key_by_id.return_value = None

    # Make request
    response = client.post(
        "/api/v1/api-keys/nonexistent/rotate",
        headers={"X-API-Key": "test_key"},
    )

    # Assertions
    assert response.status_code == 404


def test_rotate_api_key_wrong_owner(client, mock_services, sample_api_key):
    """Test rotating API key owned by different organizer."""
    # Setup mock with different owner
    api_key_response = sample_api_key.to_response()
    api_key_response.organizer_id = "org_different"
    mock_services["api_key"].get_api_key_by_id.return_value = api_key_response

    # Make request
    response = client.post(
        "/api/v1/api-keys/key_123/rotate",
        headers={"X-API-Key": "test_key"},
    )

    # Assertions
    assert response.status_code == 403
    assert "permission" in response.json()["detail"].lower()


# ============================================================
# TESTS: REVOKE API KEY
# ============================================================


def test_revoke_api_key_success(client, mock_services, sample_api_key):
    """Test successful API key revocation."""
    # Setup mock
    existing_key_response = sample_api_key.to_response()
    mock_services["api_key"].get_api_key_by_id.return_value = existing_key_response
    mock_services["api_key"].revoke_api_key.return_value = True

    # Make request
    response = client.delete(
        "/api/v1/api-keys/key_123",
        headers={"X-API-Key": "test_key"},
    )

    # Assertions
    assert response.status_code == 204

    # Verify service was called correctly
    mock_services["api_key"].revoke_api_key.assert_called_once_with("key_123")


def test_revoke_api_key_not_found(client, mock_services):
    """Test revoking non-existent API key."""
    # Setup mock
    mock_services["api_key"].get_api_key_by_id.return_value = None

    # Make request
    response = client.delete(
        "/api/v1/api-keys/nonexistent",
        headers={"X-API-Key": "test_key"},
    )

    # Assertions
    assert response.status_code == 404


def test_revoke_api_key_wrong_owner(client, mock_services, sample_api_key):
    """Test revoking API key owned by different organizer."""
    # Setup mock with different owner
    api_key_response = sample_api_key.to_response()
    api_key_response.organizer_id = "org_different"
    mock_services["api_key"].get_api_key_by_id.return_value = api_key_response

    # Make request
    response = client.delete(
        "/api/v1/api-keys/key_123",
        headers={"X-API-Key": "test_key"},
    )

    # Assertions
    assert response.status_code == 403
    assert "permission" in response.json()["detail"].lower()


def test_revoke_api_key_service_failure(client, mock_services, sample_api_key):
    """Test API key revocation with service failure."""
    # Setup mock
    existing_key_response = sample_api_key.to_response()
    mock_services["api_key"].get_api_key_by_id.return_value = existing_key_response
    mock_services["api_key"].revoke_api_key.return_value = False

    # Make request
    response = client.delete(
        "/api/v1/api-keys/key_123",
        headers={"X-API-Key": "test_key"},
    )

    # Assertions
    assert response.status_code == 500
    assert "Failed to revoke" in response.json()["detail"]


# ============================================================
# TESTS: AUTHENTICATION AND AUTHORIZATION
# ============================================================


def test_all_endpoints_require_auth(client, mock_services):
    """Test that all API key endpoints require authentication."""
    endpoints = [
        ("POST", "/api/v1/api-keys", {"tier": "FREE"}),
        ("GET", "/api/v1/api-keys", None),
        ("GET", "/api/v1/api-keys/key_123", None),
        ("POST", "/api/v1/api-keys/key_123/rotate", None),
        ("DELETE", "/api/v1/api-keys/key_123", None),
    ]

    for method, url, json_data in endpoints:
        if method == "POST":
            response = client.post(url, json=json_data)
        elif method == "GET":
            response = client.get(url)
        elif method == "DELETE":
            response = client.delete(url)

        assert response.status_code == 401, f"{method} {url} should require auth"


def test_secret_key_visibility(client, mock_services, sample_api_key):
    """Test that secret key is only visible on creation."""
    # Test 1: Secret key visible on creation
    create_response = sample_api_key.to_create_response()
    mock_services["api_key"].create_api_key.return_value = create_response

    response = client.post(
        "/api/v1/api-keys",
        json={"tier": "FREE"},
        headers={"X-API-Key": "test_key"},
    )

    assert response.status_code == 201
    assert "api_key" in response.json()

    # Test 2: Secret key NOT visible in list
    api_key_response = sample_api_key.to_response()
    list_response = APIKeyListResponse(api_keys=[api_key_response], total=1)
    mock_services["api_key"].list_api_keys.return_value = list_response

    response = client.get(
        "/api/v1/api-keys",
        headers={"X-API-Key": "test_key"},
    )

    assert response.status_code == 200
    assert "api_key" not in response.json()["api_keys"][0]

    # Test 3: Secret key NOT visible in get by ID
    mock_services["api_key"].get_api_key_by_id.return_value = api_key_response

    response = client.get(
        "/api/v1/api-keys/key_123",
        headers={"X-API-Key": "test_key"},
    )

    assert response.status_code == 200
    assert "api_key" not in response.json()
