"""Health check endpoint."""

import os
from datetime import datetime

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from src.api.dependencies import get_dynamodb_table, get_bedrock_client

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
    table=Depends(get_dynamodb_table),
    bedrock=Depends(get_bedrock_client),
) -> HealthResponse:
    """Health check endpoint.
    
    Checks:
    - DynamoDB table accessibility
    - Bedrock service availability
    - Returns API version and timestamp
    
    Returns:
        HealthResponse with service statuses
    """
    services = {}
    overall_status = "healthy"
    
    # Check DynamoDB
    try:
        start = datetime.utcnow()
        # Simple table describe to check connectivity
        table.load()
        latency = int((datetime.utcnow() - start).total_seconds() * 1000)
        
        services["dynamodb"] = ServiceStatus(
            available=True,
            latency_ms=latency,
        )
        logger.info("health_check_dynamodb_ok", latency_ms=latency)
    except Exception as e:
        services["dynamodb"] = ServiceStatus(
            available=False,
            error=str(e),
        )
        overall_status = "unhealthy"
        logger.error("health_check_dynamodb_failed", error=str(e))
    
    # Check Bedrock
    try:
        start = datetime.utcnow()
        # List foundation models to verify Bedrock access
        bedrock.list_foundation_models(
            byProvider="amazon",
            byOutputModality="TEXT",
        )
        latency = int((datetime.utcnow() - start).total_seconds() * 1000)
        
        services["bedrock"] = ServiceStatus(
            available=True,
            latency_ms=latency,
        )
        logger.info("health_check_bedrock_ok", latency_ms=latency)
    except Exception as e:
        services["bedrock"] = ServiceStatus(
            available=False,
            error=str(e),
        )
        # Bedrock failure is degraded, not unhealthy (API still works)
        if overall_status == "healthy":
            overall_status = "degraded"
        logger.error("health_check_bedrock_failed", error=str(e))
    
    # Get version from environment or default
    version = os.environ.get("API_VERSION", "1.0.0")
    
    return HealthResponse(
        status=overall_status,
        version=version,
        timestamp=datetime.utcnow(),
        services=services,
    )
