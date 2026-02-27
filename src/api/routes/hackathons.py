"""Hackathon management endpoints."""

from fastapi import APIRouter, HTTPException, Query

from src.api.dependencies import (
    CurrentOrganizer,
    HackathonServiceDep,
    OrganizerIntelligenceServiceDep,
    SubmissionServiceDep,
)
from src.models.common import Recommendation
from src.models.dashboard import OrganizerDashboard
from src.models.hackathon import (
    HackathonCreate,
    HackathonListResponse,
    HackathonResponse,
    HackathonUpdate,
)
from src.models.leaderboard import (
    LeaderboardEntry,
    LeaderboardHackathonInfo,
    LeaderboardResponse,
    LeaderboardStats,
)

router = APIRouter(prefix="/hackathons", tags=["hackathons"])


@router.post("", response_model=HackathonResponse, status_code=201)
async def create_hackathon(
    data: HackathonCreate,
    service: HackathonServiceDep,
    current_organizer: CurrentOrganizer,
) -> HackathonResponse:
    """Create a new hackathon.

    POST /api/v1/hackathons

    Requires X-API-Key header for authentication.
    """
    try:
        org_id = current_organizer["org_id"]
        return service.create_hackathon(org_id, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create hackathon: {str(e)}") from e


@router.get("", response_model=HackathonListResponse)
async def list_hackathons(
    service: HackathonServiceDep,
    current_organizer: CurrentOrganizer,
    limit: int = Query(20, ge=1, le=100),
    cursor: str | None = None,
) -> HackathonListResponse:
    """List organizer's hackathons.

    GET /api/v1/hackathons

    Requires X-API-Key header for authentication.
    """
    try:
        org_id = current_organizer["org_id"]
        return service.list_hackathons(org_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list hackathons: {str(e)}") from e


@router.get("/{hack_id}", response_model=HackathonResponse)
async def get_hackathon(
    hack_id: str,
    service: HackathonServiceDep,
    current_organizer: CurrentOrganizer,
) -> HackathonResponse:
    """Get hackathon details.

    GET /api/v1/hackathons/{hack_id}

    Requires X-API-Key header for authentication.
    """
    hackathon = service.get_hackathon(hack_id)
    if not hackathon:
        raise HTTPException(status_code=404, detail="Hackathon not found")

    # Ownership verification
    if hackathon.org_id != current_organizer["org_id"]:
        raise HTTPException(
            status_code=403, detail="You do not have permission to access this hackathon"
        )

    return hackathon


@router.put("/{hack_id}", response_model=HackathonResponse)
async def update_hackathon(
    hack_id: str,
    data: HackathonUpdate,
    service: HackathonServiceDep,
    current_organizer: CurrentOrganizer,
) -> HackathonResponse:
    """Update hackathon configuration.

    PUT /api/v1/hackathons/{hack_id}

    Requires X-API-Key header for authentication.
    """
    try:
        # Get hackathon first to verify ownership
        hackathon = service.get_hackathon(hack_id)
        if not hackathon:
            raise HTTPException(status_code=404, detail="Hackathon not found")

        # Ownership verification
        if hackathon.org_id != current_organizer["org_id"]:
            raise HTTPException(
                status_code=403, detail="You do not have permission to access this hackathon"
            )

        return service.update_hackathon(hack_id, data)
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update hackathon: {str(e)}") from e


@router.post("/{hack_id}/activate", response_model=HackathonResponse)
async def activate_hackathon(
    hack_id: str,
    service: HackathonServiceDep,
    current_organizer: CurrentOrganizer,
) -> HackathonResponse:
    """Activate hackathon (transition from DRAFT to CONFIGURED).

    POST /api/v1/hackathons/{hack_id}/activate

    Requires X-API-Key header for authentication.
    """
    try:
        org_id = current_organizer["org_id"]
        return service.activate_hackathon(hack_id, org_id)
    except ValueError as e:
        error_msg = str(e)
        if "not found" in error_msg:
            raise HTTPException(status_code=404, detail=error_msg) from e
        elif "permission" in error_msg:
            raise HTTPException(status_code=403, detail=error_msg) from e
        else:
            raise HTTPException(status_code=400, detail=error_msg) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to activate hackathon: {str(e)}") from e


@router.delete("/{hack_id}", status_code=204)
async def delete_hackathon(
    hack_id: str,
    service: HackathonServiceDep,
    current_organizer: CurrentOrganizer,
) -> None:
    """Delete hackathon (archive).

    DELETE /api/v1/hackathons/{hack_id}

    Requires X-API-Key header for authentication.
    """
    # Get hackathon first to verify ownership
    hackathon = service.get_hackathon(hack_id)
    if not hackathon:
        raise HTTPException(status_code=404, detail="Hackathon not found")

    # Ownership verification
    if hackathon.org_id != current_organizer["org_id"]:
        raise HTTPException(
            status_code=403, detail="You do not have permission to access this hackathon"
        )

    org_id = current_organizer["org_id"]
    success = service.delete_hackathon(hack_id, org_id)
    if not success:
        raise HTTPException(status_code=404, detail="Hackathon not found")
@router.get("/{hack_id}/stats")
async def get_hackathon_stats(
    hack_id: str,
    hackathon_service: HackathonServiceDep,
    submission_service: SubmissionServiceDep,
) -> dict:
    """Get hackathon statistics.

    GET /api/v1/hackathons/{hack_id}/stats

    Returns submission counts and participant statistics.
    """
    # Verify hackathon exists
    hackathon = hackathon_service.get_hackathon(hack_id)
    if not hackathon:
        raise HTTPException(status_code=404, detail="Hackathon not found")

    # Get all submissions for this hackathon
    submission_response = submission_service.list_submissions(hack_id)
    submissions = submission_response.submissions

    # Calculate statistics
    submission_count = len(submissions)
    verified_count = sum(1 for sub in submissions if sub.status == "verified")
    pending_count = sum(1 for sub in submissions if sub.status == "pending")

    # Participant count not available in list view (would need full submission details)
    participant_count = 0

    return {
        "submission_count": submission_count,
        "verified_count": verified_count,
        "pending_count": pending_count,
        "participant_count": participant_count,
        "hackathon_status": hackathon.status,
    }



@router.get("/{hack_id}/leaderboard", response_model=LeaderboardResponse)
async def get_leaderboard(
    hack_id: str,
    hackathon_service: HackathonServiceDep,
    submission_service: SubmissionServiceDep,
) -> LeaderboardResponse:
    """Get hackathon leaderboard.

    GET /api/v1/hackathons/{hack_id}/leaderboard
    """
    # Get hackathon details
    hackathon = hackathon_service.get_hackathon(hack_id)
    if not hackathon:
        raise HTTPException(status_code=404, detail="Hackathon not found")

    # Get all submissions with scores
    all_submissions = submission_service.list_submissions(hack_id)
    scored_submissions = [s for s in all_submissions.submissions if s.overall_score is not None]

    if not scored_submissions:
        raise HTTPException(status_code=400, detail="No scored submissions available")

    # Sort by overall_score descending
    sorted_submissions = sorted(
        scored_submissions, key=lambda x: x.overall_score or 0, reverse=True
    )

    # Build leaderboard entries
    leaderboard_entries = []
    for rank, submission in enumerate(sorted_submissions, start=1):
        leaderboard_entries.append(
            LeaderboardEntry(
                rank=rank,
                sub_id=submission.sub_id,
                team_name=submission.team_name,
                overall_score=submission.overall_score or 0.0,
                dimension_scores={},  # Not available in list view - get full submission for details
                recommendation=Recommendation.SOLID_SUBMISSION,  # Default - not available in list view
            )
        )

    # Calculate statistics
    scores = [s.overall_score or 0.0 for s in scored_submissions]
    mean_score = sum(scores) / len(scores) if scores else 0.0
    sorted_scores = sorted(scores)
    median_score = sorted_scores[len(sorted_scores) // 2] if sorted_scores else 0.0

    # Calculate standard deviation
    if len(scores) > 1:
        variance = sum((x - mean_score) ** 2 for x in scores) / len(scores)
        std_dev = variance**0.5
    else:
        std_dev = 0.0

    # Score distribution
    distribution = {
        "90-100": sum(1 for s in scores if 90 <= s <= 100),
        "80-89": sum(1 for s in scores if 80 <= s < 90),
        "70-79": sum(1 for s in scores if 70 <= s < 80),
        "60-69": sum(1 for s in scores if 60 <= s < 70),
        "0-59": sum(1 for s in scores if s < 60),
    }

    statistics = LeaderboardStats(
        mean_score=mean_score,
        median_score=median_score,
        std_dev=std_dev,
        highest_score=max(scores) if scores else 0.0,
        lowest_score=min(scores) if scores else 0.0,
        score_distribution=distribution,
    )

    # Build hackathon info
    hackathon_info = LeaderboardHackathonInfo(
        hack_id=hack_id,
        name=hackathon.name,
        submission_count=len(all_submissions.submissions),
        analyzed_count=len(scored_submissions),
        ai_policy_mode=hackathon.ai_policy_mode.value
        if hasattr(hackathon.ai_policy_mode, "value")
        else str(hackathon.ai_policy_mode),
    )

    return LeaderboardResponse(
        hackathon=hackathon_info,
        leaderboard=leaderboard_entries,
        statistics=statistics,
    )


@router.get("/{hack_id}/intelligence", response_model=OrganizerDashboard)
async def get_organizer_intelligence(
    hack_id: str,
    hackathon_service: HackathonServiceDep,
    intelligence_service: OrganizerIntelligenceServiceDep,
    current_organizer: CurrentOrganizer,
) -> OrganizerDashboard:
    """Get organizer intelligence dashboard for hackathon.

    GET /api/v1/hackathons/{hack_id}/intelligence

    Returns aggregated insights including:
    - Top performers
    - Hiring intelligence by role
    - Technology trends
    - Common issues with workshop recommendations
    - Prize recommendations
    - Standout moments
    - Next hackathon recommendations
    - Sponsor follow-up actions

    Requires X-API-Key header for authentication.
    """
    # Get hackathon first to verify ownership
    hackathon = hackathon_service.get_hackathon(hack_id)
    if not hackathon:
        raise HTTPException(status_code=404, detail="Hackathon not found")

    # Ownership verification
    if hackathon.org_id != current_organizer["org_id"]:
        raise HTTPException(
            status_code=403, detail="You do not have permission to access this hackathon"
        )

    try:
        dashboard = intelligence_service.generate_dashboard(hack_id)
        return dashboard
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to generate intelligence dashboard: {str(e)}"
        ) from e
