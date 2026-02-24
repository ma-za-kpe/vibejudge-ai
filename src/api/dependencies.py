"""FastAPI dependency injection for AWS services and authentication."""

import os
from typing import Annotated

import boto3
import structlog
from fastapi import Depends, HTTPException
from fastapi.security import APIKeyHeader

from src.services import (
    AnalysisService,
    CostService,
    HackathonService,
    OrganizerIntelligenceService,
    OrganizerService,
    SubmissionService,
)
from src.utils.dynamo import DynamoDBHelper

logger = structlog.get_logger()

# API Key header scheme
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


# ============================================================
# AWS SERVICE CLIENTS
# ============================================================


def get_dynamodb_table():
    """Get DynamoDB table resource."""
    table_name = os.environ.get("TABLE_NAME", "VibeJudgeTable")
    endpoint_url = os.environ.get("DYNAMODB_ENDPOINT_URL")

    if endpoint_url:
        # Local DynamoDB
        dynamodb = boto3.resource("dynamodb", endpoint_url=endpoint_url, region_name="us-east-1")
    else:
        # AWS DynamoDB
        dynamodb = boto3.resource("dynamodb")

    return dynamodb.Table(table_name)


def get_dynamodb_helper():
    """Get DynamoDB helper instance."""
    table_name = os.environ.get("TABLE_NAME", "VibeJudgeTable")
    return DynamoDBHelper(table_name)


def get_bedrock_client():
    """Get Bedrock Runtime client."""
    region = os.environ.get("AWS_REGION", "us-east-1")
    return boto3.client("bedrock-runtime", region_name=region)


def get_s3_client():
    """Get S3 client."""
    return boto3.client("s3")


# ============================================================
# SERVICE LAYER DEPENDENCIES
# ============================================================


def get_organizer_service(
    db: DynamoDBHelper = Depends(get_dynamodb_helper),
) -> OrganizerService:
    """Get organizer service instance."""
    return OrganizerService(db)


def get_hackathon_service(
    db: DynamoDBHelper = Depends(get_dynamodb_helper),
) -> HackathonService:
    """Get hackathon service instance."""
    return HackathonService(db)


def get_submission_service(
    db: DynamoDBHelper = Depends(get_dynamodb_helper),
) -> SubmissionService:
    """Get submission service instance."""
    return SubmissionService(db)


def get_analysis_service(
    db: DynamoDBHelper = Depends(get_dynamodb_helper),
) -> AnalysisService:
    """Get analysis service instance."""
    return AnalysisService(db)


def get_cost_service(
    db: DynamoDBHelper = Depends(get_dynamodb_helper),
) -> CostService:
    """Get cost service instance."""
    return CostService(db)


def get_organizer_intelligence_service(
    db: DynamoDBHelper = Depends(get_dynamodb_helper),
    hackathon_service: HackathonService = Depends(get_hackathon_service),
    submission_service: SubmissionService = Depends(get_submission_service),
) -> OrganizerIntelligenceService:
    """Get organizer intelligence service instance."""
    return OrganizerIntelligenceService(db, hackathon_service, submission_service)


# ============================================================
# TYPE ALIASES FOR DEPENDENCY INJECTION
# ============================================================

DynamoDBTable = Annotated[object, Depends(get_dynamodb_table)]
DynamoDBHelperDep = Annotated[DynamoDBHelper, Depends(get_dynamodb_helper)]
BedrockClient = Annotated[object, Depends(get_bedrock_client)]
S3Client = Annotated[object, Depends(get_s3_client)]

# Service dependencies
OrganizerServiceDep = Annotated[OrganizerService, Depends(get_organizer_service)]
HackathonServiceDep = Annotated[HackathonService, Depends(get_hackathon_service)]
SubmissionServiceDep = Annotated[SubmissionService, Depends(get_submission_service)]
AnalysisServiceDep = Annotated[AnalysisService, Depends(get_analysis_service)]
CostServiceDep = Annotated[CostService, Depends(get_cost_service)]
OrganizerIntelligenceServiceDep = Annotated[
    OrganizerIntelligenceService, Depends(get_organizer_intelligence_service)
]


# ============================================================
# AUTHENTICATION
# ============================================================


async def verify_api_key(
    organizer_service: OrganizerServiceDep,
    api_key: str | None = Depends(api_key_header),
) -> str:
    """Verify API key and return organizer ID.

    Args:
        api_key: API key from X-API-Key header
        organizer_service: Organizer service instance

    Returns:
        org_id: Organizer ID

    Raises:
        HTTPException: 401 if API key is invalid or missing
    """
    if not api_key:
        raise HTTPException(
            status_code=401,
            detail="Missing API key. Provide X-API-Key header.",
        )

    org_id = organizer_service.verify_api_key(api_key)
    if not org_id:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key",
        )

    return org_id


async def get_current_organizer(
    organizer_service: OrganizerServiceDep,
    org_id: str = Depends(verify_api_key),
) -> dict:
    """Get current organizer from database.

    Args:
        org_id: Organizer ID from verified API key
        organizer_service: Organizer service instance

    Returns:
        Organizer record dict

    Raises:
        HTTPException: 404 if organizer not found
    """
    organizer = organizer_service.get_organizer(org_id)
    if not organizer:
        raise HTTPException(
            status_code=404,
            detail="Organizer not found",
        )

    # Convert to dict for compatibility
    return organizer.model_dump()


# CurrentOrganizer type alias (must be after get_current_organizer is defined)
CurrentOrganizer = Annotated[dict, Depends(get_current_organizer)]
