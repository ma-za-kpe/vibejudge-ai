# Streamlit Dashboard AWS Deployment - Requirements

## Overview

Deploy the Streamlit Organizer Dashboard to AWS ECS Fargate with production-ready infrastructure including load balancing, auto-scaling, custom domain, HTTPS, and monitoring.

## Goals

- Deploy Streamlit dashboard to AWS with high availability
- Integrate with existing backend API in same AWS account
- Achieve production-grade reliability and security
- Enable auto-scaling based on traffic
- Minimize operational overhead
- Keep costs under $60/month for baseline traffic

## Non-Goals

- VPC private networking (backend API stays public with API key auth)
- Multi-region deployment (single region: us-east-1)
- Custom CI/CD pipeline (manual deployment initially)
- Database migrations (Streamlit is stateless)

---

## Requirements

### Requirement 1: Docker Containerization

**User Story:** As a DevOps engineer, I want the Streamlit app packaged as a Docker container so it can run consistently across environments.

**Acceptance Criteria:**
1.1. Dockerfile creates a working container image from streamlit_ui/
1.2. Container exposes port 8501 for Streamlit
1.3. Container includes health check endpoint (/_stcore/health)
1.4. Image size is optimized (<500MB)
1.5. Environment variables configure API_BASE_URL
1.6. Container runs as non-root user for security
1.7. Build process completes in <5 minutes

### Requirement 2: Amazon ECR Repository

**User Story:** As a DevOps engineer, I want to store Docker images in ECR so they're available for ECS deployments.

**Acceptance Criteria:**
2.1. ECR repository named "vibejudge-dashboard" is created
2.2. Repository has lifecycle policy to keep only 10 most recent images
2.3. Images are tagged with Git commit SHA and "latest"
2.4. Image scanning is enabled for vulnerability detection
2.5. Repository has appropriate IAM permissions for ECS tasks

### Requirement 3: ECS Fargate Cluster

**User Story:** As a platform operator, I want an ECS cluster to run Streamlit containers without managing servers.

**Acceptance Criteria:**
3.1. ECS cluster named "vibejudge-cluster" uses Fargate capacity provider
3.2. Cluster has CloudWatch Container Insights enabled
3.3. Cluster supports both FARGATE and FARGATE_SPOT for cost optimization
3.4. Cluster is in us-east-1 region

### Requirement 4: ECS Task Definition

**User Story:** As a DevOps engineer, I want a task definition that specifies container configuration and resource limits.

**Acceptance Criteria:**
4.1. Task uses 0.5 vCPU and 1GB memory (smallest Fargate size)
4.2. Task runs Streamlit container on port 8501
4.3. Task includes environment variable for API_BASE_URL
4.4. Task has health check configured (/_stcore/health)
4.5. Task logs to CloudWatch Logs group "/ecs/vibejudge-dashboard"
4.6. Task execution role has permissions for ECR and CloudWatch
4.7. Task role has no additional permissions (Streamlit doesn't need AWS access)

### Requirement 5: Application Load Balancer

**User Story:** As a user, I want to access the dashboard via HTTPS with automatic health checks and failover.

**Acceptance Criteria:**
5.1. ALB is internet-facing and listens on ports 80 and 443
5.2. HTTP (port 80) redirects to HTTPS (port 443)
5.3. Target group routes traffic to ECS tasks on port 8501
5.4. Health checks use /_stcore/health endpoint
5.5. Health check interval is 30 seconds
5.6. Unhealthy threshold is 3 consecutive failures
5.7. Healthy threshold is 2 consecutive successes
5.8. Deregistration delay is 30 seconds

### Requirement 6: ECS Service

**User Story:** As a platform operator, I want an ECS service that maintains desired container count with auto-healing.

**Acceptance Criteria:**
6.1. Service runs 2 tasks by default (high availability)
6.2. Service uses Fargate launch type
6.3. Service is registered with ALB target group
6.4. Service has deployment configuration: rolling update, 100% min healthy, 200% max
6.5. Service health check grace period is 60 seconds
6.6. Service auto-restarts failed tasks
6.7. Service uses latest task definition revision on updates

### Requirement 7: Auto-Scaling

**User Story:** As a platform operator, I want the service to scale based on CPU usage to handle traffic spikes.

**Acceptance Criteria:**
7.1. Service scales between 2 and 10 tasks
7.2. Target tracking policy maintains 70% average CPU utilization
7.3. Scale-out cooldown is 60 seconds
7.4. Scale-in cooldown is 300 seconds (5 minutes)
7.5. Scaling metrics are visible in CloudWatch

### Requirement 8: Security Groups

**User Story:** As a security engineer, I want proper network isolation with minimal exposed ports.

**Acceptance Criteria:**
8.1. ALB security group allows inbound 80/443 from 0.0.0.0/0
8.2. ALB security group allows outbound to ECS tasks on 8501
8.3. ECS security group allows inbound 8501 from ALB security group only
8.4. ECS security group allows outbound 443 to internet (for API calls)
8.5. No SSH ports exposed
8.6. Security groups have descriptive names and descriptions

### Requirement 9: CloudWatch Monitoring

**User Story:** As a platform operator, I want comprehensive monitoring and alerting for the dashboard.

**Acceptance Criteria:**
9.1. CloudWatch Logs group captures all container stdout/stderr
9.2. Log retention is set to 7 days
9.3. Metrics track: CPU, Memory, Request Count, Response Time, Healthy Hosts
9.4. CloudWatch alarm triggers when healthy host count < 1
9.5. CloudWatch alarm triggers when average response time > 5 seconds
9.6. Alarms send notifications to SNS topic

### Requirement 10: Infrastructure as Code (SAM)

**User Story:** As a DevOps engineer, I want all infrastructure defined as code for repeatability and version control.

**Acceptance Criteria:**
10.1. SAM template defines all AWS resources
10.2. Template has parameters for: environment (dev/prod), image tag, domain name
10.3. Template outputs: ALB DNS name, ECS cluster ARN, service ARN
10.4. Template can be deployed with `sam deploy`
10.5. Template supports updates without downtime (rolling deployment)
10.6. Template includes all IAM roles and policies

### Requirement 11: Deployment Script

**User Story:** As a developer, I want a single command to build, push, and deploy updates.

**Acceptance Criteria:**
11.1. Script builds Docker image from streamlit_ui/
11.2. Script tags image with Git commit SHA
11.3. Script pushes image to ECR
11.4. Script updates ECS task definition with new image
11.5. Script triggers ECS service deployment
11.6. Script waits for deployment to stabilize
11.7. Script exits with error code on failure
11.8. Script outputs deployment status and ALB URL

### Requirement 12: Cost Optimization

**User Story:** As a business owner, I want to minimize AWS costs while maintaining reliability.

**Acceptance Criteria:**
12.1. Baseline cost is under $60/month (2 Fargate tasks + ALB)
12.2. FARGATE_SPOT is used when available (70% cost savings)
12.3. CloudWatch Logs retention is limited to 7 days
12.4. Auto-scaling prevents over-provisioning
12.5. Health check intervals are optimized to reduce costs
12.6. NAT Gateway is NOT used (tasks have public IPs)

---

## Technical Constraints

1. **Region:** us-east-1 (same as backend API)
2. **Runtime:** Python 3.12 (matches backend)
3. **Framework:** Streamlit 1.30+ (existing codebase)
4. **Container Platform:** Docker with multi-stage builds
5. **Orchestration:** AWS ECS Fargate (serverless)
6. **Load Balancing:** Application Load Balancer (ALB)
7. **Deployment Tool:** AWS SAM CLI

## Dependencies

- Existing backend API at https://2nu0j4n648.execute-api.us-east-1.amazonaws.com/dev
- Streamlit UI codebase in streamlit_ui/ (already complete)
- AWS account with appropriate permissions
- Docker installed locally for builds
- AWS SAM CLI installed

## Success Metrics

- **Deployment Success:** Can deploy from scratch in <15 minutes
- **High Availability:** 99.9% uptime (multi-AZ, auto-healing)
- **Performance:** Dashboard loads in <2 seconds
- **Scalability:** Handles 100 concurrent users without degradation
- **Cost Efficiency:** <$60/month baseline, scales linearly with traffic
- **Security:** No critical vulnerabilities in container scan
- **Monitoring:** All critical metrics visible in CloudWatch

## Out of Scope

- Custom domain configuration (Route 53, ACM certificates) - manual setup
- CloudFront CDN - future optimization
- WAF rules - future security enhancement
- Secrets Manager for API keys - not needed (user-provided in UI)
- RDS database - Streamlit is stateless
- ElastiCache - no caching needed at this stage
