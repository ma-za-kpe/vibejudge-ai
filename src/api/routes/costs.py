"""Cost analytics endpoints."""

from fastapi import APIRouter, Depends

from src.api.dependencies import DynamoDBTable, CurrentOrganizer
from src.models.costs import HackathonCostResponse

router = APIRouter(tags=["costs"])


@router.get("/hackathons/{hack_id}/costs", response_model=HackathonCostResponse)
async def get_hackathon_costs(
    hack_id: str,
    organizer: CurrentOrganizer,
    table: DynamoDBTable,
) -> dict:
    """Get aggregated cost analytics for hackathon.
    
    GET /api/v1/hackathons/{hack_id}/costs
    """
    return {"status": "not implemented"}
