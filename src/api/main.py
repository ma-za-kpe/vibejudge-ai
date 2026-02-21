"""VibeJudge AI — FastAPI Application.

Main FastAPI application with Mangum handler for AWS Lambda.
"""

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum

from src.api.routes import health, organizers, hackathons, submissions, analysis, costs

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

app = FastAPI(
    title="VibeJudge AI API",
    description="AI-powered hackathon judging platform using Amazon Bedrock",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Restrict in production
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
async def startup_event():
    """Log application startup."""
    logger.info("vibejudge_api_starting", version="1.0.0")


@app.on_event("shutdown")
async def shutdown_event():
    """Log application shutdown."""
    logger.info("vibejudge_api_shutting_down")


# ============================================================
# LAMBDA HANDLER
# ============================================================

# Mangum handler for AWS Lambda
handler = Mangum(app, lifespan="off")
