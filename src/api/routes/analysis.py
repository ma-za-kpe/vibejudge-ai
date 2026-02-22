"""Analysis job management endpoints."""

from fastapi import APIRouter, HTTPException

from src.api.dependencies import (
    AnalysisServiceDep,
    CostServiceDep,
    HackathonServiceDep,
    SubmissionServiceDep,
)
from src.models.analysis import (
    AnalysisJobResponse,
    AnalysisStatusResponse,
    AnalysisTrigger,
)
from src.models.costs import CostEstimate

router = APIRouter(tags=["analysis"])


@router.post("/hackathons/{hack_id}/analyze", response_model=AnalysisJobResponse, status_code=202)
async def trigger_analysis(
    hack_id: str,
    data: AnalysisTrigger,
    analysis_service: AnalysisServiceDep,
    hackathon_service: HackathonServiceDep,
) -> AnalysisJobResponse:
    """Trigger batch analysis for submissions.
    
    POST /api/v1/hackathons/{hack_id}/analyze
    
    Creates an analysis job and invokes the Analyzer Lambda asynchronously.
    Returns immediately with job details. Use /analyze/status to check progress.
    """
    # Verify hackathon exists
    hackathon = hackathon_service.get_hackathon(hack_id)
    if not hackathon:
        raise HTTPException(status_code=404, detail="Hackathon not found")

    try:
        return analysis_service.trigger_analysis(hack_id, data.submission_ids)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to trigger analysis: {str(e)}")


@router.get("/hackathons/{hack_id}/analyze/status", response_model=AnalysisStatusResponse)
async def get_analysis_status(
    hack_id: str,
    service: AnalysisServiceDep,
) -> AnalysisStatusResponse:
    """Get analysis job status for hackathon.
    
    GET /api/v1/hackathons/{hack_id}/analyze/status
    
    Returns the most recent analysis job status.
    """
    jobs = service.list_analysis_jobs(hack_id)

    if not jobs:
        raise HTTPException(status_code=404, detail="No analysis jobs found for this hackathon")

    # Return most recent job (jobs are sorted by created_at desc)
    latest_job = jobs[0]

    # Build progress object
    from src.models.analysis import AnalysisProgress
    progress = AnalysisProgress(
        total_submissions=latest_job.total_submissions,
        completed=latest_job.completed_submissions,
        failed=latest_job.failed_submissions,
        remaining=latest_job.total_submissions - latest_job.completed_submissions - latest_job.failed_submissions,
        percent_complete=(latest_job.completed_submissions / latest_job.total_submissions * 100) if latest_job.total_submissions > 0 else 0,
    )

    return AnalysisStatusResponse(
        job_id=latest_job.job_id,
        hack_id=latest_job.hack_id,
        status=latest_job.status,
        progress=progress,
        current_submission=None,  # Not tracked in MVP
        cost_so_far=None,  # Not tracked in MVP
        errors=[],  # Not tracked in MVP
        started_at=latest_job.started_at,
        estimated_completion=latest_job.completed_at,  # Use completed_at as estimate
    )


@router.post("/hackathons/{hack_id}/analyze/estimate", response_model=CostEstimate)
async def estimate_analysis_cost(
    hack_id: str,
    hackathon_service: HackathonServiceDep,
    cost_service: CostServiceDep,
    submission_service: SubmissionServiceDep,
) -> CostEstimate:
    """Estimate analysis cost before triggering.
    
    POST /api/v1/hackathons/{hack_id}/analyze/estimate
    """
    # Get hackathon to check agents and budget
    hackathon = hackathon_service.get_hackathon(hack_id)
    if not hackathon:
        raise HTTPException(status_code=404, detail="Hackathon not found")

    # Count pending submissions
    submissions = submission_service.list_submissions(hack_id)
    submission_count = len([s for s in submissions.submissions if s.status == "pending"])

    if submission_count == 0:
        raise HTTPException(status_code=400, detail="No pending submissions to analyze")

    try:
        agents = [a.value if hasattr(a, 'value') else a for a in hackathon.agents_enabled]
        return cost_service.estimate_analysis_cost_response(
            hack_id=hack_id,
            submission_count=submission_count,
            agents_enabled=agents,
            budget_limit_usd=hackathon.budget_limit_usd,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to estimate cost: {str(e)}")
