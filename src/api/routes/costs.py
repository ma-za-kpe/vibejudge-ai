"""Cost analytics endpoints."""

from fastapi import APIRouter, HTTPException

from src.api.dependencies import CostServiceDep, HackathonServiceDep
from src.models.costs import HackathonCostResponse

router = APIRouter(tags=["costs"])


@router.get("/hackathons/{hack_id}/costs", response_model=HackathonCostResponse)
async def get_hackathon_costs(
    hack_id: str,
    hackathon_service: HackathonServiceDep,
    cost_service: CostServiceDep,
) -> HackathonCostResponse:
    """Get aggregated cost analytics for hackathon.

    GET /api/v1/hackathons/{hack_id}/costs
    """
    # Verify hackathon exists
    hackathon = hackathon_service.get_hackathon(hack_id)
    if not hackathon:
        raise HTTPException(status_code=404, detail="Hackathon not found")

    try:
        return cost_service.get_hackathon_costs_response(hack_id, hackathon.budget_limit_usd)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get costs: {str(e)}") from e
