"""FastAPI dependency injection for AWS services and authentication."""

import os
from typing import Annotated

import boto3
import structlog
from fastapi import Depends, HTTPException, Header
from fastapi.security import APIKeyHeader

logger = structlog.get_logger()

# API Key header scheme
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


# ============================================================
# AWS SERVICE CLIENTS
# ============================================================

def get_dynamodb_table():
    """Get DynamoDB table resource."""
    table_name = os.environ.get("DYNAMODB_TABLE_NAME", "VibeJudgeTable")
    dynamodb = boto3.resource("dynamodb")
    return dynamodb.Table(table_name)


def get_bedrock_client():
    """Get Bedrock Runtime client."""
    return boto3.client("bedrock-runtime")


def get_s3_client():
    """Get S3 client."""
    return boto3.client("s3")


# ============================================================
# AUTHENTICATION
# ============================================================

async def verify_api_key(
    api_key: str | None = Depends(api_key_header),
    table=Depends(get_dynamodb_table),
) -> str:
    """Verify API key and return organizer ID.
    
    Args:
        api_key: API key from X-API-Key header
        table: DynamoDB table
        
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
    
    # TODO: Implement API key verification
    # 1. Hash the API key
    # 2. Query DynamoDB GSI for matching api_key_hash
    # 3. Return org_id if found
    # For now, return a placeholder
    logger.warning("api_key_verification_not_implemented", api_key_prefix=api_key[:8])
    
    raise HTTPException(
        status_code=401,
        detail="Invalid API key",
    )


async def get_current_organizer(
    org_id: str = Depends(verify_api_key),
    table=Depends(get_dynamodb_table),
) -> dict:
    """Get current organizer from database.
    
    Args:
        org_id: Organizer ID from verified API key
        table: DynamoDB table
        
    Returns:
        Organizer record dict
        
    Raises:
        HTTPException: 404 if organizer not found
    """
    # TODO: Implement organizer lookup
    # Query DynamoDB for PK=ORG#{org_id}, SK=PROFILE
    logger.warning("get_current_organizer_not_implemented", org_id=org_id)
    
    raise HTTPException(
        status_code=404,
        detail="Organizer not found",
    )


# ============================================================
# TYPE ALIASES FOR DEPENDENCY INJECTION
# ============================================================

DynamoDBTable = Annotated[object, Depends(get_dynamodb_table)]
BedrockClient = Annotated[object, Depends(get_bedrock_client)]
S3Client = Annotated[object, Depends(get_s3_client)]
CurrentOrganizer = Annotated[dict, Depends(get_current_organizer)]
