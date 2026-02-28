"""VibeJudge AI — FastAPI Application.

Main FastAPI application with Mangum handler for AWS Lambda.
"""

import os

import structlog
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from mangum import Mangum

from src.api.middleware import BudgetMiddleware, RateLimitMiddleware, SecurityLoggerMiddleware
from src.api.routes import (
    analysis,
    api_keys,
    costs,
    hackathons,
    health,
    organizers,
    public,
    submissions,
    usage,
)
from src.utils.config import settings
from src.utils.dynamo import DynamoDBHelper

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
# RATE LIMITING & SECURITY MIDDLEWARE
# ============================================================

# Initialize DynamoDB helper for middleware
# Use environment variable directly to avoid Settings default value issue
table_name = os.environ.get("TABLE_NAME", "vibejudge-dev")
db_helper = DynamoDBHelper(table_name=table_name)

# Add middleware stack (order matters - last added runs first)
# Execution order: SecurityLogger → Budget → RateLimit → Routes

# 1. Security Logger Middleware (runs last, logs all events)
app.add_middleware(
    SecurityLoggerMiddleware,
    db_helper=db_helper,
    anomaly_threshold=100,  # requests per minute
)

# 2. Budget Enforcement Middleware (runs second)
app.add_middleware(
    BudgetMiddleware,
    db_helper=db_helper,
    max_cost_per_submission=settings.max_cost_per_submission_usd,
    exempt_paths=[
        "/health",
        "/docs",
        "/openapi.json",
        "/redoc",
        "/api/v1/public/hackathons",
        "/api/v1/public/hackathons/*/submissions",  # Public submission endpoint
        "/api/v1/organizers",  # Registration endpoint
        "/api/v1/organizers/login",  # Login endpoint
        "/organizers",  # Registration endpoint (without prefix)
        "/organizers/login",  # Login endpoint (without prefix)
    ],
)

# 3. Rate Limit Middleware (runs first, fastest check)
# Note: Mangum strips stage prefix, so paths are WITHOUT /dev prefix
app.add_middleware(
    RateLimitMiddleware,
    db_helper=db_helper,
    exempt_paths=[
        "/health",
        "/docs",
        "/openapi.json",
        "/redoc",
        "/api/v1/public/hackathons",
        "/api/v1/public/hackathons/*/submissions",  # Public submission endpoint
        "/api/v1/organizers",  # Registration endpoint (with prefix)
        "/api/v1/organizers/login",  # Login endpoint (with prefix)
        "/organizers",  # Registration endpoint (without prefix)
        "/organizers/login",  # Login endpoint (without prefix)
    ],
)

# ============================================================
# ERROR HANDLERS
# ============================================================


@app.exception_handler(429)
async def rate_limit_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle rate limit exceeded errors."""
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={
            "error": "Rate limit exceeded",
            "message": "Too many requests. Please slow down and try again later.",
            "retry_after": getattr(exc, "retry_after", 60),
        },
        headers={
            "Retry-After": str(getattr(exc, "retry_after", 60)),
        },
    )


@app.exception_handler(402)
async def budget_exceeded_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle budget exceeded errors."""
    return JSONResponse(
        status_code=status.HTTP_402_PAYMENT_REQUIRED,
        content={
            "error": "Budget limit exceeded",
            "message": "Your budget limit has been reached. Please upgrade your plan or contact support.",
            "details": getattr(exc, "details", {}),
        },
    )


@app.exception_handler(401)
async def unauthorized_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle authentication errors."""
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={
            "error": "Unauthorized",
            "message": "Invalid or missing API key. Please provide a valid X-API-Key header.",
        },
        headers={
            "WWW-Authenticate": "ApiKey",
        },
    )


# ============================================================
# ROUTE REGISTRATION
# ============================================================

# Health check (no prefix)
app.include_router(health.router)

# Public endpoints (no authentication required)
app.include_router(public.router, prefix="/api/v1")

# API v1 routes (authentication required)
app.include_router(organizers.router, prefix="/api/v1")
app.include_router(hackathons.router, prefix="/api/v1")
app.include_router(submissions.router, prefix="/api/v1")
app.include_router(analysis.router, prefix="/api/v1")
app.include_router(costs.router, prefix="/api/v1")
app.include_router(api_keys.router, prefix="/api/v1")
app.include_router(usage.router, prefix="/api/v1")

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
