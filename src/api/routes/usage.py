"""Usage analytics and reporting endpoints."""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from src.api.dependencies import CurrentOrganizer, DynamoDBHelperDep
from src.models.rate_limit import UsageSummary
from src.services.usage_tracking_service import UsageTrackingService

router = APIRouter(prefix="/usage", tags=["usage"])


def get_usage_service(db: DynamoDBHelperDep) -> UsageTrackingService:
    """Get usage tracking service instance."""
    return UsageTrackingService(db)


@router.get("/summary", response_model=UsageSummary)
async def get_usage_summary(
    current_organizer: CurrentOrganizer,
    db: DynamoDBHelperDep,
    start_date: Annotated[str, Query(description="Start date (YYYY-MM-DD)")] = None,
    end_date: Annotated[str, Query(description="End date (YYYY-MM-DD)")] = None,
) -> UsageSummary:
    """Get usage summary with optional date range.

    GET /api/v1/usage/summary?start_date=2024-01-01&end_date=2024-01-31

    Returns aggregated usage metrics for the authenticated organizer.

    Requires X-API-Key header for authentication.
    """
    try:
        service = get_usage_service(db)
        org_id = current_organizer["org_id"]

        # Parse and validate dates
        start_dt = None
        end_dt = None

        if start_date:
            try:
                start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            except ValueError as e:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid start_date format. Use YYYY-MM-DD: {str(e)}",
                ) from e

        if end_date:
            try:
                end_dt = datetime.strptime(end_date, "%Y-%m-%d")
            except ValueError as e:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid end_date format. Use YYYY-MM-DD: {str(e)}",
                ) from e

        # Validate date range
        if start_dt and end_dt and start_dt > end_dt:
            raise HTTPException(status_code=400, detail="start_date must be before end_date")

        return service.get_usage_summary(org_id, start_dt, end_dt)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get usage summary: {str(e)}") from e


@router.get("/export")
async def export_usage_csv(
    current_organizer: CurrentOrganizer,
    db: DynamoDBHelperDep,
    start_date: Annotated[str, Query(description="Start date (YYYY-MM-DD)")] = None,
    end_date: Annotated[str, Query(description="End date (YYYY-MM-DD)")] = None,
) -> StreamingResponse:
    """Export usage data as CSV.

    GET /api/v1/usage/export?start_date=2024-01-01&end_date=2024-01-31

    Returns CSV file with detailed usage records.

    Requires X-API-Key header for authentication.
    """
    try:
        service = get_usage_service(db)
        org_id = current_organizer["org_id"]

        # Parse and validate dates
        start_dt = None
        end_dt = None

        if start_date:
            try:
                start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            except ValueError as e:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid start_date format. Use YYYY-MM-DD: {str(e)}",
                ) from e

        if end_date:
            try:
                end_dt = datetime.strptime(end_date, "%Y-%m-%d")
            except ValueError as e:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid end_date format. Use YYYY-MM-DD: {str(e)}",
                ) from e

        # Validate date range
        if start_dt and end_dt and start_dt > end_dt:
            raise HTTPException(status_code=400, detail="start_date must be before end_date")

        # Generate CSV content
        csv_content = service.export_usage_csv(org_id, start_dt, end_dt)

        # Return as streaming response
        return StreamingResponse(
            iter([csv_content]),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=usage_export_{org_id}_{start_date or 'all'}_{end_date or 'all'}.csv"
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to export usage data: {str(e)}") from e
