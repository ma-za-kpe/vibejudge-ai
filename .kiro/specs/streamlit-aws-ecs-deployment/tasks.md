# Implementation Plan: Streamlit Dashboard AWS ECS Deployment

## Overview

This implementation plan breaks down the deployment of the VibeJudge AI Streamlit dashboard on AWS ECS Fargate into discrete, actionable tasks. The implementation follows a bottom-up approach: containerization → infrastructure → deployment automation → monitoring. Each task builds on previous work and includes validation steps to ensure correctness before proceeding.

## Tasks

- [ ] 1. Create Docker containerization
  - [x] 1.1 Create multi-stage Dockerfile for Streamlit application
    - Create `Dockerfile` in project root
    - Use `python:3.12-slim` as base image
    - Implement builder stage for dependency installation
    - Implement runtime stage with non-root user (UID 1000)
    - Configure Streamlit environment variables (port 8501, headless mode)
    - Expose port 8501
    - Set WORKDIR to `/app`
    - Copy Streamlit application from `streamlit_ui/` directory
    - Add metadata labels (maintainer, version, description)
    - _Requirements: 1.1, 1.3, 1.4, 1.6, 1.7_

  - [x] 1.2 Verify Docker image size is under 500MB
    - Build image locally with `docker build`
    - Check image size with `docker images`
    - Optimize if size exceeds 500MB (remove unnecessary packages, use .dockerignore)
    - _Requirements: 1.2_

  - [x] 1.3 Test container health check endpoint
    - Run container locally with `docker run`
    - Send HTTP GET request to `http://localhost:8501/_stcore/health`
    - Verify response is HTTP 200 within 2 seconds
    - Verify Streamlit UI loads at `http://localhost:8501`
    - _Requirements: 1.5_

- [ ] 2. Create SAM infrastructure template
  - [x] 2.1 Create base SAM template with parameters and metadata
    - Create `template.yaml` in project root
    - Define CloudFormation template version and SAM transform
    - Add parameters: Environment (dev/prod), ImageTag, DomainName
    - Add template metadata and description
    - _Requirements: 10.2_

  - [x] 2.2 Define networking resources in SAM template
    - Add VPC resource with CIDR 10.0.0.0/16
    - Add 2 public subnets in different AZs (10.0.1.0/24, 10.0.2.0/24)
    - Add Internet Gateway and attach to VPC
    - Add route table with default route to Internet Gateway
    - Associate route table with public subnets
    - _Requirements: 8.4, 8.5, 12.7_

  - [x] 2.3 Define security groups in SAM template
    - Add ALB security group allowing inbound 80/443 from 0.0.0.0/0
    - Add ECS security group allowing inbound 8501 from ALB security group only
    - Add outbound rule for ECS security group allowing HTTPS (443) to 0.0.0.0/0
    - _Requirements: 8.1, 8.2, 8.3_

  - [x] 2.4 Define ECR repository in SAM template
    - Add ECR repository resource named "vibejudge-dashboard"
    - Enable image scanning on push
    - Set image tag mutability to MUTABLE
    - Add lifecycle policy to keep only 10 most recent images
    - _Requirements: 2.1, 2.2, 2.6_

  - [x] 2.5 Define IAM roles in SAM template
    - Add task execution role with AmazonECSTaskExecutionRolePolicy
    - Add ECR pull permissions to task execution role
    - Add CloudWatch Logs write permissions to task execution role
    - Add empty task role (no permissions needed for Streamlit)
    - _Requirements: 2.5, 4.5, 4.6, 10.4_

  - [x] 2.6 Define ECS cluster in SAM template
    - Add ECS cluster resource named "vibejudge-cluster"
    - Configure FARGATE and FARGATE_SPOT capacity providers
    - Set default capacity provider strategy (FARGATE_SPOT weight 1, FARGATE base 2)
    - Enable Container Insights
    - _Requirements: 3.1, 3.2, 3.3, 3.4_

  - [x] 2.7 Define ECS task definition in SAM template
    - Add task definition with Fargate compatibility
    - Set CPU to 512 (0.5 vCPU) and memory to 1024 (1GB)
    - Define container with image from ECR (parameterized by ImageTag)
    - Configure container port 8501
    - Set CloudWatch log configuration to `/ecs/vibejudge-dashboard`
    - Add environment variable for API_BASE_URL
    - Configure health check command
    - Reference task execution role and task role
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7_

  - [x] 2.8 Define Application Load Balancer in SAM template
    - Add ALB resource in public subnets
    - Add target group with health check to `/_stcore/health` (30s interval, 2 healthy threshold, 3 unhealthy threshold)
    - Add HTTP listener on port 80 with redirect to HTTPS
    - Add HTTPS listener on port 443 forwarding to target group
    - Configure deregistration delay to 30 seconds
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6_

  - [x] 2.9 Define ECS service in SAM template
    - Add ECS service resource referencing cluster and task definition
    - Set desired count to 2
    - Configure network configuration with public subnets and ECS security group
    - Enable public IP assignment
    - Configure load balancer with target group and container port 8501
    - Set deployment configuration (max 200%, min 100% healthy)
    - Enable deployment circuit breaker with rollback
    - Set health check grace period to 60 seconds
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7_

  - [x] 2.10 Define auto-scaling resources in SAM template
    - Add scalable target for ECS service (min 2, max 10)
    - Add target tracking scaling policy for CPU utilization (target 70%)
    - Configure scale-out cooldown to 60 seconds
    - Configure scale-in cooldown to 300 seconds
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.7_

  - [x] 2.11 Define CloudWatch monitoring resources in SAM template
    - Add CloudWatch log group `/ecs/vibejudge-dashboard` with 7-day retention
    - Add SNS topic for alarm notifications
    - Add CloudWatch alarm for HealthyHostCount < 1
    - Add CloudWatch alarm for TargetResponseTime > 5s
    - _Requirements: 9.1, 9.2, 9.5, 9.6_

  - [x] 2.12 Add outputs to SAM template
    - Add output for ALB DNS name
    - Add output for ECS cluster ARN
    - Add output for ECS service ARN
    - Add output for ECR repository URI
    - _Requirements: 5.7, 10.3_

- [ ] 3. Create deployment automation script
  - [x] 3.1 Create deployment script with prerequisite validation
    - Create `deploy.sh` bash script in project root
    - Add shebang and set -e for error handling
    - Validate AWS CLI is installed
    - Validate Docker is installed and daemon is running
    - Validate SAM CLI is installed (version 1.100+)
    - Validate Git is installed
    - Accept environment (dev/prod) as command-line argument
    - _Requirements: 11.1_

  - [x] 3.2 Add Docker build and tag logic to deployment script
    - Get current Git commit SHA with `git rev-parse --short HEAD`
    - Build Docker image with commit SHA tag
    - Tag image with both commit SHA and "latest"
    - _Requirements: 2.3, 11.2, 11.3_

  - [x] 3.3 Add ECR authentication and push logic to deployment script
    - Get AWS account ID with `aws sts get-caller-identity`
    - Construct ECR repository URI
    - Authenticate Docker with ECR using `aws ecr get-login-password`
    - Push image with commit SHA tag
    - Push image with "latest" tag
    - _Requirements: 11.4_

  - [x] 3.4 Add SAM deployment logic to deployment script
    - Run `sam deploy` with config-env parameter
    - Pass ImageTag parameter with commit SHA
    - Wait for CloudFormation stack to complete
    - _Requirements: 11.5_

  - [x] 3.5 Add ECS service stabilization wait to deployment script
    - Use `aws ecs wait services-stable` to wait for service to stabilize
    - Set timeout to 15 minutes
    - Exit with error if service fails to stabilize
    - _Requirements: 11.6_

  - [x] 3.6 Add output display to deployment script
    - Query CloudFormation stack outputs for ALB DNS name
    - Display ALB URL to user
    - Display deployment success message
    - _Requirements: 11.7_

- [ ] 4. Create SAM configuration file
  - [x] 4.1 Create samconfig.toml with dev and prod environments
    - Create `samconfig.toml` in project root
    - Define `[dev.deploy.parameters]` section with stack name, region, capabilities
    - Define `[prod.deploy.parameters]` section with stack name, region, capabilities
    - Set confirm_changeset = true for prod, false for dev
    - Set region to us-east-1
    - _Requirements: 10.1, 10.2_

- [ ] 5. Create supporting documentation
  - [x] 5.1 Create deployment README
    - Create `DEPLOYMENT.md` in project root
    - Document prerequisites (AWS CLI, Docker, SAM CLI, Git)
    - Document deployment steps (build, push, deploy)
    - Document how to access deployed dashboard
    - Document how to view logs and metrics
    - Document how to rollback deployments
    - Include troubleshooting section
    - _Requirements: 11.1, 11.7_

  - [x] 5.2 Create .dockerignore file
    - Create `.dockerignore` in project root
    - Exclude `.git`, `__pycache__`, `*.pyc`, `.env`, `tests/`, `.kiro/`
    - Exclude `node_modules`, `.vscode`, `.idea`
    - _Requirements: 1.2_

- [ ] 6. Checkpoint - Validate infrastructure deployment
  - Run deployment script for dev environment
  - Verify CloudFormation stack creates successfully
  - Verify ECS service reaches stable state with 2 running tasks
  - Verify ALB health checks pass
  - Access dashboard via ALB DNS name
  - Verify Streamlit UI loads within 2 seconds
  - Check CloudWatch logs for container output
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 7. Create operational runbooks
  - [x] 7.1 Create runbook for common operations
    - Create `RUNBOOK.md` in project root
    - Document how to view service status
    - Document how to view task logs
    - Document how to manually scale service
    - Document how to force new deployment (restart)
    - Document how to check ALB target health
    - Document how to view CloudWatch metrics
    - Document how to respond to alarms
    - _Requirements: 9.3, 9.4, 9.5, 9.6_

  - [x] 7.2 Create CloudWatch Logs Insights queries
    - Create `cloudwatch-queries.md` in project root
    - Add query to find errors and exceptions
    - Add query to track response times
    - Add query to monitor health checks
    - Add query to analyze scaling events
    - _Requirements: 9.1, 9.7_

- [x] 8. Final checkpoint - End-to-end validation
  - Deploy to prod environment using deployment script
  - Verify 2 tasks running in different availability zones
  - Verify auto-scaling triggers by simulating load (optional)
  - Verify deployment rollback by deploying broken image (optional)
  - Verify CloudWatch alarms trigger correctly (optional)
  - Verify cost projections match expected baseline ($54-60/month)
  - Document final ALB URL for production dashboard
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- The deployment script should be idempotent (safe to run multiple times)
- SAM template uses CloudFormation intrinsic functions for resource references
- All AWS resources should be tagged with Environment and Project tags for cost tracking
- The design uses YAML for SAM templates, Dockerfile syntax for containerization, and bash for deployment automation
