"""Analysis job management endpoints."""

from fastapi import APIRouter, Depends

from src.api.dependencies import DynamoDBTable, CurrentOrganizer
from src.models.analysis import (
    AnalysisTrigger, AnalysisJobResponse, AnalysisStatusResponse,
)
from src.models.costs import CostEstimate

router = APIRouter(tags=["analysis"])


@router.post("/hackathons/{hack_id}/analyze", response_model=AnalysisJobResponse, status_code=202)
async def trigger_analysis(
    hack_id: str,
    data: AnalysisTrigger,
    organizer: CurrentOrganizer,
    table: DynamoDBTable,
) -> dict:
    """Trigger batch analysis for submissions.
    
    POST /api/v1/hackathons/{hack_id}/analyze
    """
    return {"status": "not implemented"}


@router.get("/hackathons/{hack_id}/analyze/status", response_model=AnalysisStatusResponse)
async def get_analysis_status(
    hack_id: str,
    organizer: CurrentOrganizer,
    table: DynamoDBTable,
) -> dict:
    """Get analysis job status.
    
    GET /api/v1/hackathons/{hack_id}/analyze/status
    """
    return {"status": "not implemented"}


@router.post("/hackathons/{hack_id}/analyze/estimate", response_model=CostEstimate)
async def estimate_analysis_cost(
    hack_id: str,
    organizer: CurrentOrganizer,
    table: DynamoDBTable,
) -> dict:
    """Estimate analysis cost before triggering.
    
    POST /api/v1/hackathons/{hack_id}/analyze/estimate
    """
    return {"status": "not implemented"}
