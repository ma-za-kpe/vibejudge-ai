#!/usr/bin/env bash

# VibeJudge AI - Streamlit Dashboard Deployment Script
# This script automates the deployment of the Streamlit dashboard to AWS ECS Fargate
# Usage: ./deploy.sh <environment>
# Example: ./deploy.sh dev

set -e  # Exit immediately on any command failure

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Print functions
print_error() {
    echo -e "${RED}ERROR: $1${NC}" >&2
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}→ $1${NC}"
}

# Validate command-line arguments
if [ $# -ne 1 ]; then
    print_error "Invalid number of arguments"
    echo "Usage: $0 <environment>"
    echo "Example: $0 dev"
    echo "Valid environments: dev, prod"
    exit 1
fi

ENVIRONMENT=$1

# Validate environment value
if [ "$ENVIRONMENT" != "dev" ] && [ "$ENVIRONMENT" != "prod" ]; then
    print_error "Invalid environment: $ENVIRONMENT"
    echo "Valid environments: dev, prod"
    exit 1
fi

print_info "Starting deployment for environment: $ENVIRONMENT"
echo ""

# ============================================================================
# PREREQUISITE VALIDATION
# ============================================================================

print_info "Validating prerequisites..."
echo ""

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    print_error "AWS CLI is not installed"
    echo "Please install AWS CLI: https://aws.amazon.com/cli/"
    exit 1
fi
print_success "AWS CLI is installed ($(aws --version))"

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed"
    echo "Please install Docker: https://docs.docker.com/get-docker/"
    exit 1
fi
print_success "Docker is installed ($(docker --version))"

# Check if Docker daemon is running
if ! docker info &> /dev/null; then
    print_error "Docker daemon is not running"
    echo "Please start Docker daemon and try again"
    exit 1
fi
print_success "Docker daemon is running"

# Check if SAM CLI is installed
if ! command -v sam &> /dev/null; then
    print_error "SAM CLI is not installed"
    echo "Please install SAM CLI: https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html"
    exit 1
fi

# Check SAM CLI version (require 1.100+)
SAM_VERSION=$(sam --version | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)
SAM_MAJOR=$(echo "$SAM_VERSION" | cut -d. -f1)
SAM_MINOR=$(echo "$SAM_VERSION" | cut -d. -f2)

if [ "$SAM_MAJOR" -lt 1 ] || ([ "$SAM_MAJOR" -eq 1 ] && [ "$SAM_MINOR" -lt 100 ]); then
    print_error "SAM CLI version $SAM_VERSION is too old (require 1.100+)"
    echo "Please upgrade SAM CLI: https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html"
    exit 1
fi
print_success "SAM CLI is installed (version $SAM_VERSION)"

# Check if Git is installed
if ! command -v git &> /dev/null; then
    print_error "Git is not installed"
    echo "Please install Git: https://git-scm.com/downloads"
    exit 1
fi
print_success "Git is installed ($(git --version))"

# Verify we're in a Git repository
if ! git rev-parse --git-dir &> /dev/null; then
    print_error "Not in a Git repository"
    echo "Please run this script from the project root directory"
    exit 1
fi
print_success "Git repository detected"

echo ""
print_success "All prerequisites validated successfully!"
echo ""

# ============================================================================
# DOCKER BUILD AND TAG
# ============================================================================

print_info "Building and tagging Docker image..."
echo ""

# Get current Git commit SHA
GIT_COMMIT_SHA=$(git rev-parse --short HEAD)
if [ -z "$GIT_COMMIT_SHA" ]; then
    print_error "Failed to get Git commit SHA"
    exit 1
fi
print_success "Git commit SHA: $GIT_COMMIT_SHA"

# Build Docker image with commit SHA tag
print_info "Building Docker image for linux/amd64 platform: vibejudge-dashboard:$GIT_COMMIT_SHA"
if ! docker build --platform linux/amd64 -t "vibejudge-dashboard:$GIT_COMMIT_SHA" -f Dockerfile .; then
    print_error "Docker build failed"
    exit 1
fi
print_success "Docker image built successfully"

# Tag image with "latest"
print_info "Tagging image as 'latest'"
if ! docker tag "vibejudge-dashboard:$GIT_COMMIT_SHA" "vibejudge-dashboard:latest"; then
    print_error "Failed to tag image as 'latest'"
    exit 1
fi
print_success "Image tagged with both $GIT_COMMIT_SHA and latest"

echo ""
print_success "Docker build and tag completed successfully!"
echo ""

# ============================================================================
# ECR AUTHENTICATION AND PUSH
# ============================================================================

print_info "Authenticating with ECR and pushing images..."
echo ""

# Get AWS account ID
print_info "Getting AWS account ID..."
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text 2>&1)
if [ $? -ne 0 ]; then
    print_error "Failed to get AWS account ID"
    echo "Error: $AWS_ACCOUNT_ID"
    echo "Please ensure AWS CLI is configured with valid credentials"
    exit 1
fi
print_success "AWS Account ID: $AWS_ACCOUNT_ID"

# Get AWS region (default to us-east-1 if not configured)
AWS_REGION=$(aws configure get region 2>/dev/null || echo "us-east-1")
print_success "AWS Region: $AWS_REGION"

# Construct ECR repository URI
ECR_REPOSITORY_NAME="vibejudge-dashboard"
ECR_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPOSITORY_NAME}"
print_success "ECR Repository URI: $ECR_URI"

# Authenticate Docker with ECR
print_info "Authenticating Docker with ECR..."
if ! aws ecr get-login-password --region "$AWS_REGION" | docker login --username AWS --password-stdin "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com" 2>&1; then
    print_error "Failed to authenticate with ECR"
    echo "Please ensure:"
    echo "  1. ECR repository exists (will be created by SAM template)"
    echo "  2. AWS credentials have ECR permissions"
    echo "  3. Docker daemon is running"
    exit 1
fi
print_success "Successfully authenticated with ECR"

# Tag images with ECR URI
print_info "Tagging images for ECR..."
if ! docker tag "vibejudge-dashboard:$GIT_COMMIT_SHA" "${ECR_URI}:${GIT_COMMIT_SHA}"; then
    print_error "Failed to tag image with commit SHA"
    exit 1
fi
print_success "Tagged image: ${ECR_URI}:${GIT_COMMIT_SHA}"

if ! docker tag "vibejudge-dashboard:$GIT_COMMIT_SHA" "${ECR_URI}:latest"; then
    print_error "Failed to tag image with 'latest'"
    exit 1
fi
print_success "Tagged image: ${ECR_URI}:latest"

# Push image with commit SHA tag
print_info "Pushing image with commit SHA tag..."
if ! docker push "${ECR_URI}:${GIT_COMMIT_SHA}"; then
    print_error "Failed to push image with commit SHA tag"
    echo "If the ECR repository doesn't exist, deploy the SAM template first:"
    echo "  sam deploy --config-env $ENVIRONMENT --guided"
    exit 1
fi
print_success "Successfully pushed ${ECR_URI}:${GIT_COMMIT_SHA}"

# Push image with "latest" tag
print_info "Pushing image with 'latest' tag..."
if ! docker push "${ECR_URI}:latest"; then
    print_error "Failed to push image with 'latest' tag"
    exit 1
fi
print_success "Successfully pushed ${ECR_URI}:latest"

echo ""
print_success "ECR authentication and push completed successfully!"
echo ""

# ============================================================================
# SAM DEPLOYMENT
# ============================================================================

print_info "Deploying infrastructure with SAM..."
echo ""

# Deploy SAM template with config-env parameter and ImageTag parameter
print_info "Running sam deploy for environment: $ENVIRONMENT"
print_info "Using ImageTag: $GIT_COMMIT_SHA"

if ! sam deploy \
    --config-env "$ENVIRONMENT" \
    --parameter-overrides "ImageTag=${GIT_COMMIT_SHA}" \
    --no-fail-on-empty-changeset; then
    print_error "SAM deployment failed"
    echo "Please check the CloudFormation console for details"
    exit 1
fi

print_success "SAM deployment completed successfully!"
echo ""

# ============================================================================
# ECS SERVICE STABILIZATION WAIT
# ============================================================================

print_info "Waiting for ECS service to stabilize..."
echo ""

# Construct cluster and service names based on environment
CLUSTER_NAME="vibejudge-cluster-${ENVIRONMENT}"
SERVICE_NAME="vibejudge-dashboard-service-${ENVIRONMENT}"

print_success "ECS Cluster: $CLUSTER_NAME"
print_success "ECS Service: $SERVICE_NAME"

# Wait for ECS service to stabilize (15 minute timeout)
print_info "Waiting for service to stabilize (timeout: 15 minutes)..."
print_info "This may take several minutes as tasks start and pass health checks..."
echo ""

# Use AWS CLI wait command with timeout
# Note: aws ecs wait has a built-in timeout of 40 attempts * 15 seconds = 10 minutes
# We'll use timeout command to enforce 15 minute limit
if command -v timeout &> /dev/null; then
    # Linux/Mac with timeout command
    if timeout 900 aws ecs wait services-stable \
        --cluster "$CLUSTER_NAME" \
        --services "$SERVICE_NAME" \
        --region "$AWS_REGION"; then
        print_success "ECS service stabilized successfully!"
    else
        EXIT_CODE=$?
        if [ $EXIT_CODE -eq 124 ]; then
            print_error "Service failed to stabilize within 15 minutes (timeout)"
        else
            print_error "Service failed to stabilize (exit code: $EXIT_CODE)"
        fi
        echo ""
        echo "Troubleshooting steps:"
        echo "  1. Check ECS service status:"
        echo "     aws ecs describe-services --cluster $CLUSTER_NAME --services $SERVICE_NAME --region $AWS_REGION"
        echo "  2. Check task status:"
        echo "     aws ecs list-tasks --cluster $CLUSTER_NAME --service-name $SERVICE_NAME --region $AWS_REGION"
        echo "  3. Check CloudWatch logs:"
        echo "     aws logs tail /ecs/vibejudge-dashboard --follow --region $AWS_REGION"
        echo "  4. Check ALB target health:"
        echo "     aws elbv2 describe-target-health --target-group-arn <target-group-arn> --region $AWS_REGION"
        exit 1
    fi
else
    # Fallback without timeout command (Windows/Git Bash)
    print_info "Note: 'timeout' command not available, using default AWS CLI timeout (10 minutes)"
    if aws ecs wait services-stable \
        --cluster "$CLUSTER_NAME" \
        --services "$SERVICE_NAME" \
        --region "$AWS_REGION"; then
        print_success "ECS service stabilized successfully!"
    else
        print_error "Service failed to stabilize"
        echo ""
        echo "Troubleshooting steps:"
        echo "  1. Check ECS service status:"
        echo "     aws ecs describe-services --cluster $CLUSTER_NAME --services $SERVICE_NAME --region $AWS_REGION"
        echo "  2. Check task status:"
        echo "     aws ecs list-tasks --cluster $CLUSTER_NAME --service-name $SERVICE_NAME --region $AWS_REGION"
        echo "  3. Check CloudWatch logs:"
        echo "     aws logs tail /ecs/vibejudge-dashboard --follow --region $AWS_REGION"
        echo "  4. Check ALB target health:"
        echo "     aws elbv2 describe-target-health --target-group-arn <target-group-arn> --region $AWS_REGION"
        exit 1
    fi
fi

echo ""
print_success "ECS service stabilization completed successfully!"
echo ""

# ============================================================================
# OUTPUT DISPLAY
# ============================================================================

print_info "Retrieving deployment outputs..."
echo ""

# Construct CloudFormation stack name based on environment
STACK_NAME="vibejudge-dashboard-${ENVIRONMENT}"
print_success "CloudFormation Stack: $STACK_NAME"

# Query CloudFormation stack outputs for ALB DNS name
print_info "Querying stack outputs..."
ALB_DNS=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --region "$AWS_REGION" \
    --query 'Stacks[0].Outputs[?OutputKey==`LoadBalancerDNS`].OutputValue' \
    --output text 2>&1)

if [ $? -ne 0 ]; then
    print_error "Failed to retrieve ALB DNS name from CloudFormation stack"
    echo "Error: $ALB_DNS"
    echo "You can manually retrieve the ALB URL with:"
    echo "  aws cloudformation describe-stacks --stack-name $STACK_NAME --region $AWS_REGION --query 'Stacks[0].Outputs'"
    exit 1
fi

if [ -z "$ALB_DNS" ]; then
    print_error "ALB DNS name not found in stack outputs"
    echo "Please check the CloudFormation stack outputs manually"
    exit 1
fi

print_success "ALB DNS Name: $ALB_DNS"
echo ""

# Display deployment success message with ALB URL
echo "╔════════════════════════════════════════════════════════════════════════════╗"
echo "║                                                                            ║"
echo "║                    🎉  DEPLOYMENT SUCCESSFUL!  🎉                          ║"
echo "║                                                                            ║"
echo "╚════════════════════════════════════════════════════════════════════════════╝"
echo ""
print_success "Environment: $ENVIRONMENT"
print_success "Git Commit: $GIT_COMMIT_SHA"
print_success "ECS Cluster: $CLUSTER_NAME"
print_success "ECS Service: $SERVICE_NAME"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
print_info "Dashboard URL:"
echo ""
echo -e "  ${GREEN}http://${ALB_DNS}${NC}"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
print_info "Next Steps:"
echo "  1. Access the dashboard at the URL above"
echo "  2. Configure HTTPS with ACM certificate (optional)"
echo "  3. Set up custom domain name (optional)"
echo "  4. Monitor service health in CloudWatch"
echo ""
print_info "Useful Commands:"
echo "  • View service status:"
echo "    aws ecs describe-services --cluster $CLUSTER_NAME --services $SERVICE_NAME --region $AWS_REGION"
echo ""
echo "  • View logs:"
echo "    aws logs tail /ecs/vibejudge-dashboard --follow --region $AWS_REGION"
echo ""
echo "  • View ALB target health:"
echo "    aws elbv2 describe-target-health --target-group-arn <target-group-arn> --region $AWS_REGION"
echo ""
print_success "Deployment completed successfully!"
echo ""

exit 0
