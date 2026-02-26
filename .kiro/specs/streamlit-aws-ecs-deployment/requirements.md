# Requirements Document: Streamlit Dashboard AWS ECS Deployment

## Introduction

This document specifies the functional and non-functional requirements for deploying the VibeJudge AI Streamlit Organizer Dashboard on AWS ECS Fargate. The deployment must provide a highly available, auto-scaling, containerized solution with Application Load Balancer, CloudWatch monitoring, and Infrastructure as Code using AWS SAM. The system targets <$60/month operational cost while supporting 100 concurrent users with 99.9% uptime and <2s page load times.

## Glossary

- **ECS**: Elastic Container Service - AWS container orchestration service
- **Fargate**: Serverless compute engine for containers
- **ALB**: Application Load Balancer - Layer 7 load balancer
- **ECR**: Elastic Container Registry - Docker image repository
- **Task**: Single running instance of a container in ECS
- **Service**: ECS component that maintains desired number of tasks
- **Target_Group**: ALB component that routes traffic to healthy tasks
- **Health_Check**: Periodic HTTP request to verify task health
- **SAM**: Serverless Application Model - Infrastructure as Code framework
- **vCPU**: Virtual CPU unit (1 vCPU = 1024 CPU units)
- **LCU**: Load Balancer Capacity Unit - ALB pricing metric
- **Container_Insights**: CloudWatch feature for container metrics
- **Circuit_Breaker**: ECS feature that automatically rolls back failed deployments
- **FARGATE_SPOT**: Discounted Fargate capacity using spare AWS capacity

## Requirements

### Requirement 1: Docker Containerization

**User Story:** As a DevOps engineer, I want to containerize the Streamlit application, so that it can run consistently across development and production environments.

#### Acceptance Criteria

1. WHEN building the Docker image THEN the System SHALL use a multi-stage build to minimize final image size
2. WHEN the Docker image is built THEN the System SHALL produce an image smaller than 500MB
3. WHEN the container starts THEN the System SHALL run the Streamlit process as a non-root user with UID 1000
4. WHEN the container is running THEN the System SHALL expose port 8501 for HTTP traffic
5. WHEN the container receives a health check request at `/_stcore/health` THEN the System SHALL respond with HTTP 200 status within 2 seconds
6. WHEN the container starts THEN the System SHALL accept API_BASE_URL as an environment variable for backend API configuration
7. WHEN the Dockerfile is built THEN the System SHALL include metadata labels for maintainer, version, and description

### Requirement 2: ECR Repository Management

**User Story:** As a DevOps engineer, I want to store Docker images in ECR with lifecycle management, so that I can version images and control storage costs.

#### Acceptance Criteria

1. WHEN a Docker image is pushed to ECR THEN the System SHALL automatically scan the image for CVE vulnerabilities
2. WHEN more than 10 images exist in the repository THEN the System SHALL automatically delete the oldest images to maintain only 10 most recent
3. WHEN an image is pushed THEN the System SHALL tag it with both the Git commit SHA and "latest" tag
4. WHEN an image is stored THEN the System SHALL calculate and store a SHA256 digest for integrity verification
5. WHEN the ECS task execution role requests image access THEN the System SHALL grant pull permissions via IAM policy
6. WHEN the repository is created THEN the System SHALL enable tag mutability to allow "latest" tag updates

### Requirement 3: ECS Fargate Cluster Configuration

**User Story:** As a platform administrator, I want a serverless ECS cluster with cost optimization, so that I can run containers without managing servers.

#### Acceptance Criteria

1. WHEN the ECS cluster is created THEN the System SHALL configure both FARGATE and FARGATE_SPOT capacity providers
2. WHEN launching new tasks THEN the System SHALL prefer FARGATE_SPOT capacity to achieve 70% cost savings
3. WHEN launching tasks THEN the System SHALL maintain a base of 2 tasks on standard FARGATE for reliability
4. WHEN the cluster is running THEN the System SHALL enable Container Insights for detailed metrics collection
5. WHEN tasks are launched THEN the System SHALL distribute them across multiple availability zones for high availability

### Requirement 4: ECS Task Definition

**User Story:** As a DevOps engineer, I want to define task resource requirements and configuration, so that containers run with appropriate CPU, memory, and permissions.

#### Acceptance Criteria

1. WHEN a task is launched THEN the System SHALL allocate 0.5 vCPU (512 CPU units) to the container
2. WHEN a task is launched THEN the System SHALL allocate 1GB of memory to the container
3. WHEN a task starts THEN the System SHALL configure the container to listen on port 8501
4. WHEN a task runs THEN the System SHALL send container logs to CloudWatch Logs group `/ecs/vibejudge-dashboard`
5. WHEN a task needs to pull images THEN the System SHALL use the task execution role with ECR pull permissions
6. WHEN a task is running THEN the System SHALL use an empty task role since the Streamlit application does not require AWS API access
7. WHEN a task is defined THEN the System SHALL configure health check command to verify Streamlit process is running

### Requirement 5: Application Load Balancer

**User Story:** As a user, I want to access the dashboard via a stable URL with HTTPS, so that I can securely interact with the application.

#### Acceptance Criteria

1. WHEN the ALB is created THEN the System SHALL configure listeners on ports 80 (HTTP) and 443 (HTTPS)
2. WHEN the ALB receives HTTP traffic on port 80 THEN the System SHALL redirect to HTTPS on port 443
3. WHEN the ALB routes traffic THEN the System SHALL distribute requests across healthy tasks in the target group
4. WHEN the ALB performs health checks THEN the System SHALL send HTTP GET requests to `/_stcore/health` every 30 seconds
5. WHEN a task fails 3 consecutive health checks THEN the System SHALL mark the task as unhealthy and stop routing traffic to it
6. WHEN a new task passes 2 consecutive health checks THEN the System SHALL mark the task as healthy and begin routing traffic to it
7. WHEN the ALB is deployed THEN the System SHALL provide a DNS name as output for accessing the dashboard

### Requirement 6: ECS Service Management

**User Story:** As a platform administrator, I want the ECS service to maintain desired task count with auto-healing, so that the application remains available during failures.

#### Acceptance Criteria

1. WHEN the ECS service is created THEN the System SHALL maintain a desired count of 2 running tasks at all times
2. WHEN a task fails health checks THEN the System SHALL automatically start a replacement task within 60 seconds
3. WHEN deploying a new task definition THEN the System SHALL perform a rolling deployment maintaining 100% minimum healthy tasks
4. WHEN deploying a new task definition THEN the System SHALL allow up to 200% maximum tasks (4 tasks during deployment)
5. WHEN a deployment fails THEN the System SHALL automatically rollback to the previous task definition via circuit breaker
6. WHEN tasks start THEN the System SHALL wait 60 seconds (health check grace period) before evaluating health checks
7. WHEN tasks are running THEN the System SHALL register them with the ALB target group on port 8501

### Requirement 7: Auto-Scaling Configuration

**User Story:** As a platform administrator, I want automatic scaling based on CPU utilization, so that the system handles variable load efficiently.

#### Acceptance Criteria

1. WHEN the ECS service is created THEN the System SHALL configure auto-scaling with minimum capacity of 2 tasks and maximum capacity of 10 tasks
2. WHEN average CPU utilization exceeds 70% for 60 seconds THEN the System SHALL scale out by adding tasks
3. WHEN average CPU utilization falls below 70% for 300 seconds THEN the System SHALL scale in by removing tasks
4. WHEN scaling out THEN the System SHALL wait 60 seconds (scale-out cooldown) before evaluating another scale-out action
5. WHEN scaling in THEN the System SHALL wait 300 seconds (scale-in cooldown) before evaluating another scale-in action
6. WHEN scaling actions occur THEN the System SHALL publish scaling activities to CloudWatch for monitoring
7. WHEN task count reaches maximum capacity (10 tasks) THEN the System SHALL stop scaling out regardless of CPU utilization

### Requirement 8: Security Groups and Network Isolation

**User Story:** As a security engineer, I want network-level isolation between components, so that only necessary traffic is allowed.

#### Acceptance Criteria

1. WHEN the ALB security group is created THEN the System SHALL allow inbound traffic only on ports 80 and 443 from the internet (0.0.0.0/0)
2. WHEN the ECS security group is created THEN the System SHALL allow inbound traffic only on port 8501 from the ALB security group
3. WHEN ECS tasks need outbound access THEN the System SHALL allow outbound HTTPS traffic on port 443 to reach the backend API
4. WHEN the network is configured THEN the System SHALL place ECS tasks in public subnets with public IP addresses to avoid NAT Gateway costs
5. WHEN the network is configured THEN the System SHALL place the ALB in public subnets across multiple availability zones

### Requirement 9: CloudWatch Monitoring and Alerting

**User Story:** As a platform administrator, I want comprehensive monitoring and alerting, so that I can detect and respond to issues quickly.

#### Acceptance Criteria

1. WHEN tasks are running THEN the System SHALL send all container stdout and stderr logs to CloudWatch Logs group `/ecs/vibejudge-dashboard`
2. WHEN logs are stored THEN the System SHALL retain them for 7 days to minimize storage costs
3. WHEN the ECS service is running THEN the System SHALL publish metrics for CPUUtilization, MemoryUtilization, DesiredTaskCount, and RunningTaskCount
4. WHEN the ALB is running THEN the System SHALL publish metrics for TargetResponseTime, HealthyHostCount, UnHealthyHostCount, and HTTPCode_Target_5XX_Count
5. WHEN HealthyHostCount falls below 1 THEN the System SHALL trigger a CloudWatch alarm and send notification to SNS topic
6. WHEN TargetResponseTime exceeds 5 seconds for 2 consecutive periods THEN the System SHALL trigger a CloudWatch alarm
7. WHEN Container Insights is enabled THEN the System SHALL collect detailed container-level metrics including network and disk I/O

### Requirement 10: Infrastructure as Code with SAM

**User Story:** As a DevOps engineer, I want all infrastructure defined in SAM templates, so that deployments are repeatable and version-controlled.

#### Acceptance Criteria

1. WHEN the SAM template is deployed THEN the System SHALL create all required resources including VPC, subnets, security groups, ECR, ECS cluster, task definition, service, ALB, target group, and CloudWatch resources
2. WHEN the SAM template is deployed THEN the System SHALL accept parameters for Environment (dev/prod), ImageTag, and optional DomainName
3. WHEN the SAM template is deployed THEN the System SHALL output the ALB DNS name, ECS cluster ARN, service ARN, and ECR repository URI
4. WHEN the SAM template is deployed THEN the System SHALL create IAM roles for task execution (ECR and CloudWatch access) and task role (empty)
5. WHEN the SAM template is deployed THEN the System SHALL configure all resources with appropriate tags for cost tracking
6. WHEN the SAM template is updated THEN the System SHALL perform a CloudFormation change set to preview changes before applying

### Requirement 11: Deployment Automation

**User Story:** As a DevOps engineer, I want an automated deployment script, so that I can deploy new versions with a single command.

#### Acceptance Criteria

1. WHEN the deployment script runs THEN the System SHALL validate that AWS CLI, Docker, SAM CLI, and Git are installed
2. WHEN the deployment script runs THEN the System SHALL build the Docker image with the current Git commit SHA as the tag
3. WHEN the Docker image is built THEN the System SHALL tag it with both the commit SHA and "latest" tags
4. WHEN the deployment script runs THEN the System SHALL authenticate with ECR and push both image tags
5. WHEN images are pushed THEN the System SHALL deploy the SAM template with the commit SHA as the ImageTag parameter
6. WHEN the SAM deployment completes THEN the System SHALL wait for the ECS service to stabilize before returning success
7. WHEN the deployment script completes THEN the System SHALL output the ALB URL for accessing the deployed dashboard

### Requirement 12: Cost Optimization

**User Story:** As a platform administrator, I want to minimize operational costs, so that the deployment remains within budget constraints.

#### Acceptance Criteria

1. WHEN running 2 tasks continuously THEN the System SHALL incur monthly costs less than $60
2. WHEN launching tasks THEN the System SHALL prefer FARGATE_SPOT capacity to achieve approximately 70% cost savings compared to standard FARGATE
3. WHEN storing images in ECR THEN the System SHALL automatically delete images beyond the 10 most recent to minimize storage costs
4. WHEN storing logs THEN the System SHALL retain CloudWatch logs for only 7 days to minimize log storage costs
5. WHEN the task count reaches 10 (maximum capacity) THEN the System SHALL cap monthly costs at approximately $155
6. WHEN deploying the ALB THEN the System SHALL use Application Load Balancer (not Network Load Balancer) to minimize LCU costs for HTTP traffic
7. WHEN configuring networking THEN the System SHALL use public subnets with Internet Gateway instead of NAT Gateway to avoid $32/month NAT costs

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Task Count Invariant

*For any* point in time during normal operation, the number of running tasks should be greater than or equal to the minimum capacity (2) and less than or equal to the maximum capacity (10).

**Validates: Requirements 6.1, 7.1**

### Property 2: Health Check Determines Routing

*For any* ECS task, if it fails 3 consecutive health checks, then the ALB should not route any new requests to that task.

**Validates: Requirements 5.5, 6.2**

### Property 3: Auto-Healing Replacement

*For any* failed task, the ECS service should start a replacement task within 60 seconds to maintain the desired count.

**Validates: Requirements 6.2**

### Property 4: Rolling Deployment Safety

*For any* deployment, the number of healthy tasks should never fall below the minimum healthy percent (100% of desired count = 2 tasks) during the deployment process.

**Validates: Requirements 6.3, 6.4**

### Property 5: Deployment Rollback on Failure

*For any* deployment where tasks fail to reach healthy status, the circuit breaker should automatically rollback to the previous task definition.

**Validates: Requirements 6.5**

### Property 6: Scaling Respects Bounds

*For any* scaling action, the resulting task count should never be less than 2 or greater than 10, regardless of CPU utilization.

**Validates: Requirements 7.1, 7.7**

### Property 7: Scaling Cooldown Prevention

*For any* scale-out action, no additional scale-out should occur within 60 seconds, and for any scale-in action, no additional scale-in should occur within 300 seconds.

**Validates: Requirements 7.4, 7.5**

### Property 8: Network Isolation

*For any* inbound traffic to ECS tasks, it should only be accepted on port 8501 and only from the ALB security group, not from the public internet.

**Validates: Requirements 8.2**

### Property 9: Image Lifecycle Enforcement

*For any* ECR repository state, the number of stored images should never exceed 10.

**Validates: Requirements 2.2**

### Property 10: Log Retention Enforcement

*For any* CloudWatch log group, logs older than 7 days should be automatically deleted.

**Validates: Requirements 9.2**

### Property 11: Cost Ceiling

*For any* month of operation, when the task count is at maximum capacity (10 tasks), the total infrastructure cost should not exceed $155.

**Validates: Requirements 12.5**

### Property 12: High Availability Guarantee

*For any* single task failure, at least one healthy task should remain running and serving traffic at all times.

**Validates: Requirements 6.1, 6.2**

### Property 13: Health Check Response Time

*For any* health check request to a healthy task, the response should be received within 2 seconds.

**Validates: Requirements 1.5**

### Property 14: Container Non-Root Execution

*For any* running container, the Streamlit process should execute with UID 1000 (non-root user).

**Validates: Requirements 1.3**

### Property 15: Image Size Constraint

*For any* Docker image built from the Dockerfile, the final image size should be less than 500MB.

**Validates: Requirements 1.2**

### Property 16: Vulnerability Scanning

*For any* image pushed to ECR, a vulnerability scan should be initiated automatically.

**Validates: Requirements 2.1**

### Property 17: Multi-AZ Distribution

*For any* set of running tasks, they should be distributed across at least 2 availability zones when the task count is 2 or more.

**Validates: Requirements 3.5**

### Property 18: Resource Allocation Consistency

*For any* task launched, it should be allocated exactly 0.5 vCPU and exactly 1GB of memory.

**Validates: Requirements 4.1, 4.2**

### Property 19: HTTPS Redirect

*For any* HTTP request received on port 80, the ALB should respond with a redirect to HTTPS on port 443.

**Validates: Requirements 5.2**

### Property 20: Alarm Triggers on Unhealthy State

*For any* state where HealthyHostCount is less than 1, a CloudWatch alarm should be in ALARM state and send a notification.

**Validates: Requirements 9.5**
