#!/bin/bash
# Start VibeJudge AI API with local environment

export DYNAMODB_TABLE_NAME=VibeJudgeTable
export DYNAMODB_ENDPOINT_URL=http://localhost:8000
export AWS_ACCESS_KEY_ID=dummy
export AWS_SECRET_ACCESS_KEY=dummy
export AWS_REGION=us-east-1
export LOG_LEVEL=INFO

echo "Starting VibeJudge AI API on port 8001..."
echo "Environment:"
echo "  - DynamoDB: $DYNAMODB_ENDPOINT_URL"
echo "  - Table: $DYNAMODB_TABLE_NAME"
echo ""

uvicorn src.api.main:app --reload --port 8001
