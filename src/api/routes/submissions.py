"""Submission management endpoints."""

from fastapi import APIRouter, Depends, Query

from src.api.dependencies import DynamoDBTable, CurrentOrganizer
from src.models.submission import (
    SubmissionBatchCreate, SubmissionBatchCreateResponse,
    SubmissionResponse, SubmissionListResponse,
)
from src.models.costs import SubmissionCostResponse

router = APIRouter(tags=["submissions"])


@router.post("/hackathons/{hack_id}/submissions", response_model=SubmissionBatchCreateResponse, status_code=201)
async def create_submissions(
    hack_id: str,
    data: SubmissionBatchCreate,
    organizer: CurrentOrganizer,
    table: DynamoDBTable,
) -> dict:
    """Add submissions to hackathon (batch).
    
    POST /api/v1/hackathons/{hack_id}/submissions
    """
    return {"status": "not implemented"}


@router.get("/hackathons/{hack_id}/submissions", response_model=SubmissionListResponse)
async def list_submissions(
    hack_id: str,
    organizer: CurrentOrganizer,
    table: DynamoDBTable,
    limit: int = Query(50, ge=1, le=500),
    cursor: str | None = None,
) -> dict:
    """List hackathon submissions.
    
    GET /api/v1/hackathons/{hack_id}/submissions
    """
    return {"status": "not implemented"}


@router.get("/submissions/{sub_id}", response_model=SubmissionResponse)
async def get_submission(
    sub_id: str,
    organizer: CurrentOrganizer,
    table: DynamoDBTable,
) -> dict:
    """Get submission details with scores.
    
    GET /api/v1/submissions/{sub_id}
    """
    return {"status": "not implemented"}


@router.delete("/submissions/{sub_id}", status_code=204)
async def delete_submission(
    sub_id: str,
    organizer: CurrentOrganizer,
    table: DynamoDBTable,
) -> None:
    """Delete submission.
    
    DELETE /api/v1/submissions/{sub_id}
    """
    return {"status": "not implemented"}


@router.get("/submissions/{sub_id}/costs", response_model=SubmissionCostResponse)
async def get_submission_costs(
    sub_id: str,
    organizer: CurrentOrganizer,
    table: DynamoDBTable,
) -> dict:
    """Get detailed cost breakdown for submission.
    
    GET /api/v1/submissions/{sub_id}/costs
    """
    return {"status": "not implemented"}
