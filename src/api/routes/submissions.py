"""Submission management endpoints."""

from fastapi import APIRouter, HTTPException, Query

from src.api.dependencies import (
    CostServiceDep,
    CurrentOrganizer,
    HackathonServiceDep,
    SubmissionServiceDep,
)
from src.models.costs import CostRecord, SubmissionCostResponse
from src.models.submission import (
    IndividualScorecardsResponse,
    ScorecardResponse,
    SubmissionBatchCreate,
    SubmissionBatchCreateResponse,
    SubmissionListResponse,
    SubmissionResponse,
)

router = APIRouter(tags=["submissions"])


@router.post(
    "/hackathons/{hack_id}/submissions",
    response_model=SubmissionBatchCreateResponse,
    status_code=201,
)
async def create_submissions(
    hack_id: str,
    data: SubmissionBatchCreate,
    submission_service: SubmissionServiceDep,
    hackathon_service: HackathonServiceDep,
) -> SubmissionBatchCreateResponse:
    """Add submissions to hackathon (batch).

    POST /api/v1/hackathons/{hack_id}/submissions
    """
    # Verify hackathon exists
    hackathon = hackathon_service.get_hackathon(hack_id)
    if not hackathon:
        raise HTTPException(status_code=404, detail="Hackathon not found")

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


@router.get("/hackathons/{hack_id}/submissions", response_model=SubmissionListResponse)
async def list_submissions(
    hack_id: str,
    service: SubmissionServiceDep,
    limit: int = Query(50, ge=1, le=500),
    cursor: str | None = None,
) -> SubmissionListResponse:
    """List hackathon submissions.

    GET /api/v1/hackathons/{hack_id}/submissions
    """
    try:
        return service.list_submissions(hack_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list submissions: {str(e)}") from e


@router.get("/submissions/{sub_id}", response_model=SubmissionResponse)
async def get_submission(
    sub_id: str,
    service: SubmissionServiceDep,
) -> SubmissionResponse:
    """Get submission details with scores.

    GET /api/v1/submissions/{sub_id}
    """
    submission = service.get_submission(sub_id)
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    return submission


@router.delete("/submissions/{sub_id}", status_code=204)
async def delete_submission(
    sub_id: str,
    service: SubmissionServiceDep,
    hackathon_service: HackathonServiceDep,
    current_organizer: CurrentOrganizer,
) -> None:
    """Delete submission.

    DELETE /api/v1/submissions/{sub_id}

    Requires X-API-Key header for authentication.
    """
    # Get submission to extract hack_id
    submission = service.get_submission(sub_id)
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    # Verify hackathon ownership
    hackathon = hackathon_service.get_hackathon(submission.hack_id)
    if not hackathon:
        raise HTTPException(status_code=404, detail="Hackathon not found")

    if hackathon.org_id != current_organizer["org_id"]:
        raise HTTPException(
            status_code=403, detail="You do not have permission to delete this submission"
        )

    success = service.delete_submission(submission.hack_id, sub_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete submission")


@router.get("/submissions/{sub_id}/costs", response_model=SubmissionCostResponse)
async def get_submission_costs(
    sub_id: str,
    cost_service: CostServiceDep,
    submission_service: SubmissionServiceDep,
    hackathon_service: HackathonServiceDep,
    current_organizer: CurrentOrganizer,
) -> SubmissionCostResponse:
    """Get detailed cost breakdown for submission.

    GET /api/v1/submissions/{sub_id}/costs

    Requires X-API-Key header for authentication.
    """
    # Get submission to extract hack_id
    submission = submission_service.get_submission(sub_id)
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    # Verify hackathon ownership
    hackathon = hackathon_service.get_hackathon(submission.hack_id)
    if not hackathon:
        raise HTTPException(status_code=404, detail="Hackathon not found")

    if hackathon.org_id != current_organizer["org_id"]:
        raise HTTPException(
            status_code=403, detail="You do not have permission to access this submission's costs"
        )

    try:
        cost_data = cost_service.get_submission_costs(sub_id)

        # Convert dict records to CostRecord models
        agent_records = []
        for record in cost_data.get("agent_costs", []):
            agent_records.append(
                CostRecord(
                    sub_id=record["sub_id"],
                    hack_id=record.get("hack_id", ""),
                    agent_name=record["agent_name"],
                    model_id=record["model_id"],
                    input_tokens=record["input_tokens"],
                    output_tokens=record["output_tokens"],
                    total_tokens=record["total_tokens"],
                    input_cost_usd=record["input_cost_usd"],
                    output_cost_usd=record["output_cost_usd"],
                    total_cost_usd=record["total_cost_usd"],
                    latency_ms=record.get("latency_ms", 0),
                    cache_read_tokens=record.get("cache_read_tokens", 0),
                    cache_write_tokens=record.get("cache_write_tokens", 0),
                )
            )

        return SubmissionCostResponse(
            sub_id=cost_data["sub_id"],
            total_cost_usd=cost_data["total_cost_usd"],
            total_tokens=cost_data["total_tokens"],
            total_input_tokens=sum(r.input_tokens for r in agent_records),
            total_output_tokens=sum(r.output_tokens for r in agent_records),
            analysis_duration_ms=0,  # Will be tracked in orchestrator
            agents=agent_records,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get costs: {str(e)}") from e


@router.get(
    "/submissions/{sub_id}/individual-scorecards", response_model=IndividualScorecardsResponse
)
async def get_individual_scorecards(
    sub_id: str,
    submission_service: SubmissionServiceDep,
    hackathon_service: HackathonServiceDep,
    current_organizer: CurrentOrganizer,
) -> IndividualScorecardsResponse:
    """Get individual contributor scorecards for submission.

    GET /api/v1/submissions/{sub_id}/individual-scorecards

    Requires X-API-Key header for authentication.
    Accessible by organizer who owns the hackathon or team members (future).
    """
    # Get submission to extract hack_id
    submission = submission_service.get_submission(sub_id)
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    # Verify hackathon ownership
    hackathon = hackathon_service.get_hackathon(submission.hack_id)
    if not hackathon:
        raise HTTPException(status_code=404, detail="Hackathon not found")

    if hackathon.org_id != current_organizer["org_id"]:
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to access this submission's scorecards",
        )

    # Get individual scorecards
    scorecards = submission_service.get_individual_scorecards(sub_id)
    if scorecards is None:
        raise HTTPException(status_code=404, detail="Submission not found")

    return IndividualScorecardsResponse(
        sub_id=submission.sub_id,
        hack_id=submission.hack_id,
        team_name=submission.team_name,
        scorecards=scorecards,
        total_count=len(scorecards),
    )


@router.get("/submissions/{sub_id}/scorecard", response_model=ScorecardResponse)
async def get_submission_scorecard(
    sub_id: str,
    submission_service: SubmissionServiceDep,
) -> ScorecardResponse:
    """Get detailed scorecard for submission with team dynamics, strategy, and feedback.

    GET /api/v1/submissions/{sub_id}/scorecard

    Returns comprehensive scorecard including:
    - Agent scores with detailed evidence
    - Team dynamics analysis
    - Strategy analysis
    - Actionable feedback with code examples
    """
    scorecard = submission_service.get_submission_scorecard(sub_id)
    if scorecard is None:
        raise HTTPException(status_code=404, detail="Submission not found")

    return scorecard  # type: ignore[return-value]
