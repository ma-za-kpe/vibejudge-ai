#!/bin/bash
# Start local development environment

set -e

echo "=========================================="
echo "VibeJudge AI - Local Development Setup"
echo "=========================================="
echo ""

# Check if DynamoDB is running
echo "Checking DynamoDB..."
if docker ps | grep -q dynamodb-local; then
    echo "✅ DynamoDB is running"
else
    echo "❌ DynamoDB is not running"
    echo "Starting DynamoDB..."
    docker run -d -p 8000:8000 --name dynamodb-local amazon/dynamodb-local
    sleep 3
    echo "✅ DynamoDB started"
fi

# Check if table exists
echo ""
echo "Checking DynamoDB table..."
if AWS_ACCESS_KEY_ID=dummy AWS_SECRET_ACCESS_KEY=dummy aws dynamodb describe-table \
    --table-name VibeJudgeTable \
    --endpoint-url http://localhost:8000 \
    --region us-east-1 &>/dev/null; then
    echo "✅ Table exists"
else
    echo "❌ Table does not exist"
    echo "Creating table..."
    AWS_ACCESS_KEY_ID=dummy AWS_SECRET_ACCESS_KEY=dummy aws dynamodb create-table \
        --table-name VibeJudgeTable \
        --attribute-definitions \
            AttributeName=PK,AttributeType=S \
            AttributeName=SK,AttributeType=S \
            AttributeName=GSI1PK,AttributeType=S \
            AttributeName=GSI1SK,AttributeType=S \
            AttributeName=GSI2PK,AttributeType=S \
            AttributeName=GSI2SK,AttributeType=S \
        --key-schema \
            AttributeName=PK,KeyType=HASH \
            AttributeName=SK,KeyType=RANGE \
        --provisioned-throughput \
            ReadCapacityUnits=5,WriteCapacityUnits=5 \
        --global-secondary-indexes \
            "[{\"IndexName\":\"GSI1\",\"KeySchema\":[{\"AttributeName\":\"GSI1PK\",\"KeyType\":\"HASH\"},{\"AttributeName\":\"GSI1SK\",\"KeyType\":\"RANGE\"}],\"Projection\":{\"ProjectionType\":\"ALL\"},\"ProvisionedThroughput\":{\"ReadCapacityUnits\":5,\"WriteCapacityUnits\":5}},{\"IndexName\":\"GSI2\",\"KeySchema\":[{\"AttributeName\":\"GSI2PK\",\"KeyType\":\"HASH\"},{\"AttributeName\":\"GSI2SK\",\"KeyType\":\"RANGE\"}],\"Projection\":{\"ProjectionType\":\"KEYS_ONLY\"},\"ProvisionedThroughput\":{\"ReadCapacityUnits\":5,\"WriteCapacityUnits\":5}}]" \
        --endpoint-url http://localhost:8000 \
        --region us-east-1 > /dev/null
    echo "✅ Table created"
fi

echo ""
echo "=========================================="
echo "Starting FastAPI server on port 8001..."
echo "=========================================="
echo ""
echo "API will be available at:"
echo "  - http://localhost:8001"
echo "  - http://localhost:8001/docs (Swagger UI)"
echo ""
echo "Press Ctrl+C to stop"
echo ""

# Start uvicorn
uvicorn src.api.main:app --reload --port 8001
