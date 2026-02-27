"""Public endpoints (no authentication required)."""

from fastapi import APIRouter, HTTPException

from src.api.dependencies import HackathonServiceDep
from src.models.hackathon import PublicHackathonInfo, PublicHackathonListResponse

router = APIRouter(prefix="/public", tags=["public"])


@router.get("/hackathons", response_model=PublicHackathonListResponse)
async def list_public_hackathons(
    service: HackathonServiceDep,
) -> PublicHackathonListResponse:
    """List public hackathons (no authentication required).

    GET /api/v1/public/hackathons

    Returns only CONFIGURED hackathons with minimal public information.
    No API key required - this is a public endpoint for submission portals.
    """
    try:
        all_hackathons = service.list_all_configured_hackathons()

        public_hackathons = [
            PublicHackathonInfo(
                hack_id=h.hack_id,
                name=h.name,
                description=h.description,
                start_date=h.start_date,
                end_date=h.end_date,
                submission_count=h.submission_count,
            )
            for h in all_hackathons
        ]

        return PublicHackathonListResponse(hackathons=public_hackathons)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to list public hackathons: {str(e)}"
        ) from e
