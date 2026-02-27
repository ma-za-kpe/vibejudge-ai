"""Public endpoints (no authentication required)."""

from fastapi import APIRouter, HTTPException

from src.api.dependencies import HackathonServiceDep, SubmissionServiceDep
from src.models.hackathon import PublicHackathonInfo, PublicHackathonListResponse
from src.models.submission import (
    SubmissionBatchCreate,
    SubmissionBatchCreateResponse,
)

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


@router.post(
    "/hackathons/{hack_id}/submissions",
    response_model=SubmissionBatchCreateResponse,
    status_code=201,
)
async def create_public_submission(
    hack_id: str,
    data: SubmissionBatchCreate,
    submission_service: SubmissionServiceDep,
    hackathon_service: HackathonServiceDep,
) -> SubmissionBatchCreateResponse:
    """Submit to hackathon (public endpoint, no authentication required).

    POST /api/v1/public/hackathons/{hack_id}/submissions

    Allows teams to submit their GitHub repositories without authentication.
    This is the public-facing submission portal for hackathon participants.
    """
    # Verify hackathon exists and is accepting submissions
    hackathon = hackathon_service.get_hackathon(hack_id)
    if not hackathon:
        raise HTTPException(status_code=404, detail="Hackathon not found")

    # Only allow submissions to CONFIGURED hackathons
    if hackathon.status.value != "configured":
        raise HTTPException(
            status_code=400,
            detail=f"Hackathon is not accepting submissions (status: {hackathon.status.value})",
        )

    try:
        result = submission_service.create_submissions(hack_id, data)

        # Update hackathon submission count
        for _ in range(result.created):
            hackathon_service.increment_submission_count(hack_id)

        return result
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to create submissions: {str(e)}"
        ) from e
