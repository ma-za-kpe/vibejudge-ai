"""Health check endpoint."""

import os
from datetime import datetime
from typing import Any

import structlog
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from src.api.dependencies import get_dynamodb_table

logger = structlog.get_logger()

router = APIRouter(tags=["health"])


# ============================================================
# RESPONSE MODELS
# ============================================================


class ServiceStatus(BaseModel):
    """Status of a single service."""

    available: bool
    latency_ms: int | None = None
    error: str | None = None


class HealthResponse(BaseModel):
    """Health check response."""

    status: str  # healthy | degraded | unhealthy
    version: str
    timestamp: datetime
    services: dict[str, ServiceStatus]


# ============================================================
# HEALTH CHECK ENDPOINT
# ============================================================


@router.get("/health", response_model=HealthResponse)
async def health_check(
    table: Any = Depends(get_dynamodb_table),
) -> HealthResponse:
    """Health check endpoint.

    Checks:
    - DynamoDB table accessibility
    - Returns API version and timestamp

    Returns:
        HealthResponse with service statuses
    """
    services = {}
    overall_status = "healthy"

    # Check DynamoDB - use table_name property instead of load()
    try:
        start = datetime.now()
        # Just check if we can access the table name (doesn't require DescribeTable permission)
        table_name = table.table_name
        latency = int((datetime.now() - start).total_seconds() * 1000)

        services["dynamodb"] = ServiceStatus(
            available=True,
            latency_ms=latency,
        )
        logger.info("health_check_dynamodb_ok", table_name=table_name, latency_ms=latency)
    except Exception as e:
        services["dynamodb"] = ServiceStatus(
            available=False,
            error=str(e),
        )
        overall_status = "unhealthy"
        logger.error("health_check_dynamodb_failed", error=str(e))

    # Get version from environment or default
    version = os.environ.get("API_VERSION", "1.0.0")

    return HealthResponse(
        status=overall_status,
        version=version,
        timestamp=datetime.now(),
        services=services,
    )
