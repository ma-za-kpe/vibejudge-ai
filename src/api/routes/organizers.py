"""Organizer account management endpoints."""

from fastapi import APIRouter, Depends, HTTPException

from src.api.dependencies import OrganizerServiceDep, CurrentOrganizer
from src.models.organizer import (
    OrganizerCreate, OrganizerCreateResponse,
    OrganizerLogin, OrganizerLoginResponse,
    OrganizerResponse,
)

router = APIRouter(prefix="/organizers", tags=["organizers"])


@router.post("", response_model=OrganizerCreateResponse, status_code=201)
async def create_organizer(
    data: OrganizerCreate,
    service: OrganizerServiceDep,
) -> OrganizerCreateResponse:
    """Create a new organizer account.
    
    POST /api/v1/organizers
    
    Returns API key - store it securely, it won't be shown again.
    """
    try:
        return service.create_organizer(data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create organizer: {str(e)}")


@router.post("/login", response_model=OrganizerLoginResponse)
async def login_organizer(
    data: OrganizerLogin,
    service: OrganizerServiceDep,
) -> OrganizerLoginResponse:
    """Login and regenerate API key.
    
    POST /api/v1/organizers/login
    
    Invalidates previous API key and returns a new one.
    """
    try:
        # Get organizer by email
        organizer = service.get_organizer_by_email(data.email)
        if not organizer:
            raise HTTPException(status_code=404, detail="Organizer not found")
        
        # Regenerate API key
        return service.regenerate_api_key(organizer.org_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Login failed: {str(e)}")


@router.get("/me", response_model=OrganizerResponse)
@router.get("/organizers/me", response_model=OrganizerResponse)
async def get_current_organizer_profile(
    current_organizer: CurrentOrganizer,
) -> OrganizerResponse:
    """Get current organizer profile (requires authentication).
    
    GET /api/v1/organizers/me
    
    Requires X-API-Key header.
    """
    return OrganizerResponse(**current_organizer)
