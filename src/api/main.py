"""VibeJudge AI — FastAPI Application.

Main FastAPI application with Mangum handler for AWS Lambda.
"""

import os

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum

from src.api.routes import analysis, costs, hackathons, health, organizers, submissions

# Configure structured logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ]
)

logger = structlog.get_logger()

# ============================================================
# FASTAPI APPLICATION
# ============================================================

# Get stage for API Gateway path prefix
stage = os.environ.get("ENVIRONMENT", "dev")

app = FastAPI(
    title="VibeJudge AI API",
    description="AI-powered hackathon judging platform using Amazon Bedrock",
    version="1.0.0",
    root_path=f"/{stage}",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# CORS middleware
allowed_origins = os.environ.get("ALLOWED_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# ROUTE REGISTRATION
# ============================================================

# Health check (no prefix)
app.include_router(health.router)

# API v1 routes
app.include_router(organizers.router, prefix="/api/v1")
app.include_router(hackathons.router, prefix="/api/v1")
app.include_router(submissions.router, prefix="/api/v1")
app.include_router(analysis.router, prefix="/api/v1")
app.include_router(costs.router, prefix="/api/v1")

# ============================================================
# STARTUP/SHUTDOWN EVENTS
# ============================================================


@app.on_event("startup")
async def startup_event() -> None:
    """Log application startup."""
    logger.info("vibejudge_api_starting", version="1.0.0")


@app.on_event("shutdown")
async def shutdown_event() -> None:
    """Log application shutdown."""
    logger.info("vibejudge_api_shutting_down")


# ============================================================
# LAMBDA HANDLER
# ============================================================

# Mangum handler for AWS Lambda
# API Gateway adds stage prefix (/dev, /staging, /prod) which Mangum needs to strip

stage = os.environ.get("ENVIRONMENT", "dev")
handler = Mangum(app, lifespan="off", api_gateway_base_path=f"/{stage}")
