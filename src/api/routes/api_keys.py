"""API key management endpoints."""

from fastapi import APIRouter, HTTPException

from src.api.dependencies import CurrentOrganizer, DynamoDBHelperDep
from src.models.api_key import (
    APIKeyCreate,
    APIKeyCreateResponse,
    APIKeyListResponse,
    APIKeyResponse,
)
from src.services.api_key_service import APIKeyService

router = APIRouter(prefix="/api-keys", tags=["api-keys"])


def get_api_key_service(db: DynamoDBHelperDep) -> APIKeyService:
    """Get API key service instance."""
    return APIKeyService(db, environment="live")


@router.post("", response_model=APIKeyCreateResponse, status_code=201)
async def create_api_key(
    data: APIKeyCreate,
    current_organizer: CurrentOrganizer,
    db: DynamoDBHelperDep,
) -> APIKeyCreateResponse:
    """Create a new API key.

    POST /api/v1/api-keys

    Returns the secret API key - store it securely, it will not be shown again.

    Requires X-API-Key header for authentication.
    """
    try:
        service = get_api_key_service(db)
        org_id = current_organizer["org_id"]

        # Create API key with organizer ownership
        api_key = service.create_api_key(
            organizer_id=org_id,
            hackathon_id=data.hackathon_id,
            tier=data.tier,
            expires_at=data.expires_at,
            rate_limit=data.rate_limit_per_second,
            daily_quota=data.daily_quota,
            budget_limit_usd=data.budget_limit_usd,
        )

        return api_key

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create API key: {str(e)}") from e


@router.get("", response_model=APIKeyListResponse)
async def list_api_keys(
    current_organizer: CurrentOrganizer,
    db: DynamoDBHelperDep,
) -> APIKeyListResponse:
    """List all API keys for the authenticated organizer.

    GET /api/v1/api-keys

    Returns all API keys owned by the organizer (excludes secret keys).

    Requires X-API-Key header for authentication.
    """
    try:
        service = get_api_key_service(db)
        org_id = current_organizer["org_id"]

        return service.list_api_keys(org_id)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list API keys: {str(e)}") from e


@router.get("/{key_id}", response_model=APIKeyResponse)
async def get_api_key(
    key_id: str,
    current_organizer: CurrentOrganizer,
    db: DynamoDBHelperDep,
) -> APIKeyResponse:
    """Get API key details by ID.

    GET /api/v1/api-keys/{key_id}

    Returns API key details (excludes secret key).

    Requires X-API-Key header for authentication.
    """
    try:
        service = get_api_key_service(db)

        # Get API key
        api_key = service.get_api_key_by_id(key_id)
        if not api_key:
            raise HTTPException(status_code=404, detail="API key not found")

        # Verify ownership
        if api_key.organizer_id != current_organizer["org_id"]:
            raise HTTPException(
                status_code=403,
                detail="You do not have permission to access this API key",
            )

        return api_key

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get API key: {str(e)}") from e


@router.post("/{key_id}/rotate", response_model=APIKeyCreateResponse)
async def rotate_api_key(
    key_id: str,
    current_organizer: CurrentOrganizer,
    db: DynamoDBHelperDep,
) -> APIKeyCreateResponse:
    """Rotate API key with grace period.

    POST /api/v1/api-keys/{key_id}/rotate

    Creates a new API key and marks the old one as deprecated.
    The old key remains valid for 7 days (grace period).

    Returns the new secret API key - store it securely, it will not be shown again.

    Requires X-API-Key header for authentication.
    """
    try:
        service = get_api_key_service(db)

        # Get existing key to verify ownership
        existing_key = service.get_api_key_by_id(key_id)
        if not existing_key:
            raise HTTPException(status_code=404, detail="API key not found")

        # Verify ownership
        if existing_key.organizer_id != current_organizer["org_id"]:
            raise HTTPException(
                status_code=403,
                detail="You do not have permission to rotate this API key",
            )

        # Rotate the key
        new_key, old_key = service.rotate_api_key(key_id)

        # Return new key with secret (shown only once)
        return new_key.to_create_response()

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to rotate API key: {str(e)}") from e


@router.delete("/{key_id}", status_code=204)
async def revoke_api_key(
    key_id: str,
    current_organizer: CurrentOrganizer,
    db: DynamoDBHelperDep,
) -> None:
    """Revoke API key (soft delete).

    DELETE /api/v1/api-keys/{key_id}

    Sets the API key as inactive. The key will no longer be valid for authentication.
    This is a soft delete - the key record remains in the database for audit purposes.

    Requires X-API-Key header for authentication.
    """
    try:
        service = get_api_key_service(db)

        # Get existing key to verify ownership
        existing_key = service.get_api_key_by_id(key_id)
        if not existing_key:
            raise HTTPException(status_code=404, detail="API key not found")

        # Verify ownership
        if existing_key.organizer_id != current_organizer["org_id"]:
            raise HTTPException(
                status_code=403,
                detail="You do not have permission to revoke this API key",
            )

        # Revoke the key
        success = service.revoke_api_key(key_id)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to revoke API key")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to revoke API key: {str(e)}") from e
