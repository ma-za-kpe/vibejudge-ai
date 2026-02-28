# VibeJudge AI — Operational Runbook

This runbook provides step-by-step procedures for common operational tasks when managing the VibeJudge AI Streamlit Dashboard on AWS ECS Fargate.

## Table of Contents

- [Quick Reference](#quick-reference)
- [Service Status Operations](#service-status-operations)
- [Log Management](#log-management)
- [Scaling Operations](#scaling-operations)
- [Deployment Operations](#deployment-operations)
- [Health Check Operations](#health-check-operations)
- [Monitoring and Metrics](#monitoring-and-metrics)
- [Alarm Response Procedures](#alarm-response-procedures)
- [Emergency Procedures](#emergency-procedures)

---

## Quick Reference

### Environment Variables

Set these for your environment (dev or prod):

```bash
export ENV="dev"  # or "prod"
export CLUSTER_NAME="vibejudge-cluster-${ENV}"
export SERVICE_NAME="vibejudge-dashboard-service-${ENV}"
export STACK_NAME="vibejudge-dashboard-${ENV}"
export LOG_GROUP="/ecs/vibejudge-dashboard"
export REGION="us-east-1"
```

### Common Resource ARNs

Get resource ARNs from CloudFormation stack outputs:

```bash
# Get all stack outputs
aws cloudformation describe-stacks \
  --stack-name $STACK_NAME \
  --region $REGION \
  --query 'Stacks[0].Outputs'

# Get specific output (e.g., ALB DNS)
aws cloudformation describe-stacks \
  --stack-name $STACK_NAME \
  --region $REGION \
  --query 'Stacks[0].Outputs[?OutputKey==`LoadBalancerDNS`].OutputValue' \
  --output text
```

---

## Service Status Operations

### View Service Status

**Purpose**: Check the current state of the ECS service, including running task count and deployment status.

**When to use**:
- After deployments to verify success
- During incidents to assess service health
- Regular health checks

**Procedure**:

```bash
# Basic service status
aws ecs describe-services \
  --cluster $CLUSTER_NAME \
  --services $SERVICE_NAME \
  --region $REGION \
  --query 'services[0].{Status:status,Running:runningCount,Desired:desiredCount,Pending:pendingCount}'

# Detailed service information
aws ecs describe-services \
  --cluster $CLUSTER_NAME \
  --services $SERVICE_NAME \
  --region $REGION
```

**Expected output** (healthy service):
```json
{
  "Status": "ACTIVE",
  "Running": 2,
  "Desired": 2,
  "Pending": 0
}
```

**Troubleshooting**:
- If `Running < Desired`: Tasks are starting or failing - check task logs
- If `Status != ACTIVE`: Service may be draining or inactive
- If `Pending > 0`: Tasks are being launched - wait 60-120 seconds

### List Running Tasks

**Purpose**: Get ARNs of currently running tasks for detailed inspection.

**Procedure**:

```bash
# List all tasks in the service
aws ecs list-tasks \
  --cluster $CLUSTER_NAME \
  --service-name $SERVICE_NAME \
  --region $REGION

# Get task details
TASK_ARN=$(aws ecs list-tasks \
  --cluster $CLUSTER_NAME \
  --service-name $SERVICE_NAME \
  --region $REGION \
  --query 'taskArns[0]' \
  --output text)

aws ecs describe-tasks \
  --cluster $CLUSTER_NAME \
  --tasks $TASK_ARN \
  --region $REGION
```

### View Task Details

**Purpose**: Inspect detailed information about a specific task, including health status, network configuration, and container status.

**Procedure**:

```bash
# Get task ARN (replace with actual ARN or use list-tasks)
TASK_ARN="arn:aws:ecs:us-east-1:123456789012:task/vibejudge-cluster-dev/abc123"

# View task details
aws ecs describe-tasks \
  --cluster $CLUSTER_NAME \
  --tasks $TASK_ARN \
  --region $REGION \
  --query 'tasks[0].{LastStatus:lastStatus,HealthStatus:healthStatus,CPU:cpu,Memory:memory,StartedAt:startedAt}'
```

**Expected output** (healthy task):
```json
{
  "LastStatus": "RUNNING",
  "HealthStatus": "HEALTHY",
  "CPU": "512",
  "Memory": "1024",
  "StartedAt": "2026-02-15T10:30:00Z"
}
```

---

## Log Management

### View Task Logs (Real-time)

**Purpose**: Monitor container logs in real-time for debugging and monitoring.

**When to use**:
- Debugging application issues
- Monitoring deployments
- Investigating errors

**Procedure**:

```bash
# Tail logs (follow mode)
aws logs tail $LOG_GROUP --follow --region $REGION

# Tail logs with filter
aws logs tail $LOG_GROUP \
  --follow \
  --filter-pattern "ERROR" \
  --region $REGION

# View last 100 lines
aws logs tail $LOG_GROUP \
  --since 10m \
  --region $REGION
```

### View Historical Logs

**Purpose**: Search and analyze historical logs for troubleshooting.

**Procedure**:

```bash
# View logs from last hour
aws logs tail $LOG_GROUP \
  --since 1h \
  --region $REGION

# View logs from specific time range
aws logs tail $LOG_GROUP \
  --start-time "2026-02-15T10:00:00Z" \
  --end-time "2026-02-15T11:00:00Z" \
  --region $REGION
```

### Search Logs with CloudWatch Logs Insights

**Purpose**: Run complex queries to analyze log patterns.

**Procedure**:

```bash
# Find errors in last hour
aws logs start-query \
  --log-group-name $LOG_GROUP \
  --start-time $(date -u -d '1 hour ago' +%s) \
  --end-time $(date -u +%s) \
  --query-string 'fields @timestamp, @message | filter @message like /ERROR|Exception|Failed/ | sort @timestamp desc | limit 100' \
  --region $REGION

# Get query ID from output, then check results
QUERY_ID="<query-id-from-above>"
aws logs get-query-results \
  --query-id $QUERY_ID \
  --region $REGION
```

**Common queries**:

Find errors:
```sql
fields @timestamp, @message
| filter @message like /ERROR|Exception|Failed/
| sort @timestamp desc
| limit 100
```

Monitor health checks:
```sql
fields @timestamp, @message
| filter @message like /_stcore\/health/
| stats count() by bin(1m)
```

Track response times:
```sql
fields @timestamp, @message
| filter @message like /response_time/
| stats avg(response_time) as avg_response, max(response_time) as max_response by bin(5m)
```

---

## Scaling Operations

### View Current Scaling Configuration

**Purpose**: Check current auto-scaling settings and limits.

**Procedure**:

```bash
# View scalable target
aws application-autoscaling describe-scalable-targets \
  --service-namespace ecs \
  --resource-ids "service/${CLUSTER_NAME}/${SERVICE_NAME}" \
  --region $REGION

# View scaling policies
aws application-autoscaling describe-scaling-policies \
  --service-namespace ecs \
  --resource-id "service/${CLUSTER_NAME}/${SERVICE_NAME}" \
  --region $REGION
```

### Manually Scale Service

**Purpose**: Temporarily override auto-scaling to increase or decrease task count.

**When to use**:
- Preparing for expected traffic spike
- Scaling down during maintenance
- Testing capacity

**Procedure**:

```bash
# Scale to specific count (e.g., 4 tasks)
aws ecs update-service \
  --cluster $CLUSTER_NAME \
  --service $SERVICE_NAME \
  --desired-count 4 \
  --region $REGION

# Wait for service to stabilize
aws ecs wait services-stable \
  --cluster $CLUSTER_NAME \
  --services $SERVICE_NAME \
  --region $REGION

# Verify new task count
aws ecs describe-services \
  --cluster $CLUSTER_NAME \
  --services $SERVICE_NAME \
  --region $REGION \
  --query 'services[0].{Running:runningCount,Desired:desiredCount}'
```

**Important**: Manual scaling overrides auto-scaling temporarily. Auto-scaling will resume based on CPU utilization.

### View Scaling Activities

**Purpose**: Review recent scaling actions to understand scaling behavior.

**Procedure**:

```bash
# View recent scaling activities
aws application-autoscaling describe-scaling-activities \
  --service-namespace ecs \
  --resource-id "service/${CLUSTER_NAME}/${SERVICE_NAME}" \
  --max-results 20 \
  --region $REGION
```

### Modify Auto-Scaling Limits

**Purpose**: Change minimum or maximum task count limits.

**When to use**:
- Adjusting capacity for seasonal traffic
- Cost optimization
- Capacity planning

**Procedure**:

```bash
# Update min/max capacity
aws application-autoscaling register-scalable-target \
  --service-namespace ecs \
  --resource-id "service/${CLUSTER_NAME}/${SERVICE_NAME}" \
  --scalable-dimension ecs:service:DesiredCount \
  --min-capacity 2 \
  --max-capacity 10 \
  --region $REGION
```

**Note**: For permanent changes, update `template.yaml` and redeploy.

---

## Deployment Operations

### Force New Deployment (Restart Service)

**Purpose**: Force ECS to start new tasks with the latest task definition, effectively restarting the service.

**When to use**:
- Applying configuration changes
- Recovering from stuck deployments
- Pulling latest Docker image with "latest" tag
- Resolving transient issues

**Procedure**:

```bash
# Force new deployment
aws ecs update-service \
  --cluster $CLUSTER_NAME \
  --service $SERVICE_NAME \
  --force-new-deployment \
  --region $REGION

# Monitor deployment progress
aws ecs describe-services \
  --cluster $CLUSTER_NAME \
  --services $SERVICE_NAME \
  --region $REGION \
  --query 'services[0].deployments'

# Wait for service to stabilize (may take 5-10 minutes)
aws ecs wait services-stable \
  --cluster $CLUSTER_NAME \
  --services $SERVICE_NAME \
  --region $REGION
```

**Expected behavior**:
1. ECS starts new tasks with latest task definition
2. New tasks pass health checks (60s grace period + 2 checks = ~90s)
3. ALB registers new tasks as healthy
4. Old tasks are drained and stopped
5. Service reaches stable state

### View Deployment Status

**Purpose**: Monitor ongoing deployments and check for issues.

**Procedure**:

```bash
# View current deployments
aws ecs describe-services \
  --cluster $CLUSTER_NAME \
  --services $SERVICE_NAME \
  --region $REGION \
  --query 'services[0].deployments[*].{Status:status,Desired:desiredCount,Running:runningCount,Pending:pendingCount,Failed:failedTasks,RolloutState:rolloutState}'
```

**Deployment states**:
- `PRIMARY`: Current active deployment
- `ACTIVE`: Deployment in progress
- `COMPLETED`: Deployment finished successfully
- `FAILED`: Deployment failed (circuit breaker triggered)

### Rollback to Previous Task Definition

**Purpose**: Manually rollback to a previous version after a failed deployment.

**When to use**:
- Deployment introduced bugs
- New version has performance issues
- Circuit breaker didn't trigger automatically

**Procedure**:

```bash
# List task definition revisions
aws ecs list-task-definitions \
  --family-prefix vibejudge-dashboard-${ENV} \
  --sort DESC \
  --region $REGION

# Update service to use previous revision
PREVIOUS_REVISION="vibejudge-dashboard-dev:5"  # Replace with actual revision

aws ecs update-service \
  --cluster $CLUSTER_NAME \
  --service $SERVICE_NAME \
  --task-definition $PREVIOUS_REVISION \
  --region $REGION

# Wait for rollback to complete
aws ecs wait services-stable \
  --cluster $CLUSTER_NAME \
  --services $SERVICE_NAME \
  --region $REGION
```

### View Task Definition Details

**Purpose**: Inspect task definition configuration including CPU, memory, environment variables, and image.

**Procedure**:

```bash
# Get current task definition ARN
TASK_DEF_ARN=$(aws ecs describe-services \
  --cluster $CLUSTER_NAME \
  --services $SERVICE_NAME \
  --region $REGION \
  --query 'services[0].taskDefinition' \
  --output text)

# View task definition details
aws ecs describe-task-definition \
  --task-definition $TASK_DEF_ARN \
  --region $REGION
```

---

## Health Check Operations

### Check ALB Target Health

**Purpose**: Verify that ECS tasks are registered as healthy targets in the Application Load Balancer.

**When to use**:
- Troubleshooting connectivity issues
- Verifying deployment health
- Investigating 503 errors

**Procedure**:

```bash
# Get target group ARN from CloudFormation
TARGET_GROUP_ARN=$(aws cloudformation describe-stacks \
  --stack-name $STACK_NAME \
  --region $REGION \
  --query 'Stacks[0].Outputs[?OutputKey==`TargetGroupArn`].OutputValue' \
  --output text)

# Check target health
aws elbv2 describe-target-health \
  --target-group-arn $TARGET_GROUP_ARN \
  --region $REGION
```

**Expected output** (healthy targets):
```json
{
  "TargetHealthDescriptions": [
    {
      "Target": {
        "Id": "10.0.1.123",
        "Port": 8501
      },
      "HealthCheckPort": "8501",
      "TargetHealth": {
        "State": "healthy"
      }
    },
    {
      "Target": {
        "Id": "10.0.2.456",
        "Port": 8501
      },
      "HealthCheckPort": "8501",
      "TargetHealth": {
        "State": "healthy"
      }
    }
  ]
}
```

**Health states**:
- `healthy`: Target is passing health checks
- `unhealthy`: Target is failing health checks
- `initial`: Target is in initial health check grace period
- `draining`: Target is being deregistered
- `unavailable`: Target is not registered

### Test Health Check Endpoint

**Purpose**: Manually verify the Streamlit health check endpoint is responding.

**Procedure**:

```bash
# Get ALB DNS name
ALB_DNS=$(aws cloudformation describe-stacks \
  --stack-name $STACK_NAME \
  --region $REGION \
  --query 'Stacks[0].Outputs[?OutputKey==`LoadBalancerDNS`].OutputValue' \
  --output text)

# Test health check endpoint
curl -I http://${ALB_DNS}/_stcore/health

# Expected response: HTTP/1.1 200 OK
```

### View ALB Configuration

**Purpose**: Check ALB listener rules and health check configuration.

**Procedure**:

```bash
# Get ALB ARN
ALB_ARN=$(aws elbv2 describe-load-balancers \
  --region $REGION \
  --query 'LoadBalancers[?contains(LoadBalancerName, `vibejudge`)].LoadBalancerArn' \
  --output text)

# View listeners
aws elbv2 describe-listeners \
  --load-balancer-arn $ALB_ARN \
  --region $REGION

# View target group health check configuration
aws elbv2 describe-target-groups \
  --target-group-arns $TARGET_GROUP_ARN \
  --region $REGION \
  --query 'TargetGroups[0].{HealthCheckPath:HealthCheckPath,HealthCheckInterval:HealthCheckIntervalSeconds,HealthyThreshold:HealthyThresholdCount,UnhealthyThreshold:UnhealthyThresholdCount}'
```

---

## Monitoring and Metrics

### View CloudWatch Metrics

**Purpose**: Monitor key performance indicators for the service.

**Key metrics to monitor**:
- **ECS Service**: CPUUtilization, MemoryUtilization, DesiredTaskCount, RunningTaskCount
- **ALB**: TargetResponseTime, RequestCount, HealthyHostCount, UnHealthyHostCount, HTTPCode_Target_5XX_Count

**Procedure**:

```bash
# View CPU utilization (last hour)
aws cloudwatch get-metric-statistics \
  --namespace AWS/ECS \
  --metric-name CPUUtilization \
  --dimensions Name=ServiceName,Value=$SERVICE_NAME Name=ClusterName,Value=$CLUSTER_NAME \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Average,Maximum \
  --region $REGION

# View memory utilization
aws cloudwatch get-metric-statistics \
  --namespace AWS/ECS \
  --metric-name MemoryUtilization \
  --dimensions Name=ServiceName,Value=$SERVICE_NAME Name=ClusterName,Value=$CLUSTER_NAME \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Average,Maximum \
  --region $REGION

# View ALB response time
aws cloudwatch get-metric-statistics \
  --namespace AWS/ApplicationELB \
  --metric-name TargetResponseTime \
  --dimensions Name=LoadBalancer,Value=<load-balancer-id> \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Average,Maximum \
  --region $REGION

# View healthy host count
aws cloudwatch get-metric-statistics \
  --namespace AWS/ApplicationELB \
  --metric-name HealthyHostCount \
  --dimensions Name=TargetGroup,Value=<target-group-id> Name=LoadBalancer,Value=<load-balancer-id> \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 60 \
  --statistics Average,Minimum \
  --region $REGION
```

### View CloudWatch Alarms

**Purpose**: Check alarm status and history.

**Procedure**:

```bash
# List all alarms for the service
aws cloudwatch describe-alarms \
  --alarm-name-prefix vibejudge-dashboard-${ENV} \
  --region $REGION

# View alarm history
aws cloudwatch describe-alarm-history \
  --alarm-name vibejudge-dashboard-${ENV}-HealthyHostCount \
  --max-records 10 \
  --region $REGION
```

### Create Custom CloudWatch Dashboard

**Purpose**: Visualize key metrics in a single dashboard.

**Procedure**:

```bash
# Create dashboard (example)
aws cloudwatch put-dashboard \
  --dashboard-name vibejudge-dashboard-${ENV} \
  --dashboard-body file://dashboard-config.json \
  --region $REGION
```

Example `dashboard-config.json`:
```json
{
  "widgets": [
    {
      "type": "metric",
      "properties": {
        "metrics": [
          ["AWS/ECS", "CPUUtilization", {"stat": "Average"}],
          [".", "MemoryUtilization", {"stat": "Average"}]
        ],
        "period": 300,
        "stat": "Average",
        "region": "us-east-1",
        "title": "ECS Resource Utilization"
      }
    }
  ]
}
```

---

## Alarm Response Procedures

### Alarm: HealthyHostCount < 1

**Severity**: CRITICAL

**Impact**: Service is completely down - no healthy tasks available to serve traffic.

**Immediate Actions**:

1. **Check service status**:
   ```bash
   aws ecs describe-services \
     --cluster $CLUSTER_NAME \
     --services $SERVICE_NAME \
     --region $REGION \
     --query 'services[0].{Running:runningCount,Desired:desiredCount}'
   ```

2. **Check task status**:
   ```bash
   aws ecs list-tasks \
     --cluster $CLUSTER_NAME \
     --service-name $SERVICE_NAME \
     --region $REGION

   # If tasks exist, check why they're unhealthy
   TASK_ARN=$(aws ecs list-tasks --cluster $CLUSTER_NAME --service-name $SERVICE_NAME --region $REGION --query 'taskArns[0]' --output text)

   aws ecs describe-tasks \
     --cluster $CLUSTER_NAME \
     --tasks $TASK_ARN \
     --region $REGION
   ```

3. **Check container logs**:
   ```bash
   aws logs tail $LOG_GROUP --since 10m --region $REGION
   ```

4. **Check ALB target health**:
   ```bash
   TARGET_GROUP_ARN=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --region $REGION --query 'Stacks[0].Outputs[?OutputKey==`TargetGroupArn`].OutputValue' --output text)

   aws elbv2 describe-target-health \
     --target-group-arn $TARGET_GROUP_ARN \
     --region $REGION
   ```

**Common causes and solutions**:

- **Tasks failing to start**: Check logs for application errors, increase task memory/CPU
- **Health check failing**: Verify `/_stcore/health` endpoint is responding, check security groups
- **Deployment failure**: Rollback to previous task definition
- **Resource exhaustion**: Scale up manually or increase task resources

**Recovery steps**:

```bash
# Option 1: Force new deployment
aws ecs update-service \
  --cluster $CLUSTER_NAME \
  --service $SERVICE_NAME \
  --force-new-deployment \
  --region $REGION

# Option 2: Rollback to previous task definition
aws ecs update-service \
  --cluster $CLUSTER_NAME \
  --service $SERVICE_NAME \
  --task-definition <previous-revision> \
  --region $REGION

# Option 3: Scale up manually
aws ecs update-service \
  --cluster $CLUSTER_NAME \
  --service $SERVICE_NAME \
  --desired-count 4 \
  --region $REGION
```

### Alarm: TargetResponseTime > 5 seconds

**Severity**: WARNING

**Impact**: Users experiencing slow page loads, potential timeout errors.

**Immediate Actions**:

1. **Check CPU/Memory utilization**:
   ```bash
   aws cloudwatch get-metric-statistics \
     --namespace AWS/ECS \
     --metric-name CPUUtilization \
     --dimensions Name=ServiceName,Value=$SERVICE_NAME Name=ClusterName,Value=$CLUSTER_NAME \
     --start-time $(date -u -d '30 minutes ago' +%Y-%m-%dT%H:%M:%S) \
     --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
     --period 60 \
     --statistics Average,Maximum \
     --region $REGION
   ```

2. **Check current task count**:
   ```bash
   aws ecs describe-services \
     --cluster $CLUSTER_NAME \
     --services $SERVICE_NAME \
     --region $REGION \
     --query 'services[0].{Running:runningCount,Desired:desiredCount}'
   ```

3. **Check backend API latency**: Verify backend API is responding quickly

4. **Review recent logs for errors**:
   ```bash
   aws logs tail $LOG_GROUP --since 10m --filter-pattern "ERROR" --region $REGION
   ```

**Common causes and solutions**:

- **High CPU utilization**: Auto-scaling should trigger, or manually scale up
- **Backend API slow**: Check API Gateway and Lambda metrics
- **Memory pressure**: Increase task memory in task definition
- **Database queries**: Optimize Streamlit caching

**Recovery steps**:

```bash
# Scale up manually if auto-scaling hasn't triggered
aws ecs update-service \
  --cluster $CLUSTER_NAME \
  --service $SERVICE_NAME \
  --desired-count 4 \
  --region $REGION

# If persistent, increase task resources (edit template.yaml and redeploy)
# CPU: 512 → 1024
# Memory: 1024 → 2048
```

### Alarm: High 5XX Error Rate

**Severity**: HIGH

**Impact**: Application errors affecting user experience.

**Immediate Actions**:

1. **Check error logs**:
   ```bash
   aws logs tail $LOG_GROUP \
     --since 10m \
     --filter-pattern "ERROR" \
     --region $REGION
   ```

2. **Check ALB 5XX metrics**:
   ```bash
   aws cloudwatch get-metric-statistics \
     --namespace AWS/ApplicationELB \
     --metric-name HTTPCode_Target_5XX_Count \
     --dimensions Name=LoadBalancer,Value=<load-balancer-id> \
     --start-time $(date -u -d '30 minutes ago' +%Y-%m-%dT%H:%M:%S) \
     --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
     --period 60 \
     --statistics Sum \
     --region $REGION
   ```

3. **Check recent deployments**: May be caused by bad deployment

**Common causes and solutions**:

- **Application bug**: Rollback to previous version
- **Backend API errors**: Check API Gateway and Lambda logs
- **Resource exhaustion**: Scale up or increase task resources
- **Configuration error**: Review environment variables and task definition

**Recovery steps**:

```bash
# Rollback to previous task definition
aws ecs update-service \
  --cluster $CLUSTER_NAME \
  --service $SERVICE_NAME \
  --task-definition <previous-revision> \
  --region $REGION
```

---

## Emergency Procedures

### Complete Service Outage

**Scenario**: Service is completely unavailable, all tasks are failing.

**Emergency Response**:

1. **Assess impact**:
   ```bash
   aws ecs describe-services --cluster $CLUSTER_NAME --services $SERVICE_NAME --region $REGION
   aws elbv2 describe-target-health --target-group-arn $TARGET_GROUP_ARN --region $REGION
   ```

2. **Check recent changes**: Review recent deployments, configuration changes

3. **Immediate rollback**:
   ```bash
   # Rollback to last known good task definition
   aws ecs update-service \
     --cluster $CLUSTER_NAME \
     --service $SERVICE_NAME \
     --task-definition <last-known-good-revision> \
     --region $REGION
   ```

4. **If rollback fails, redeploy from Git**:
   ```bash
   git checkout <last-known-good-commit>
   ./deploy.sh $ENV
   ```

5. **Monitor recovery**:
   ```bash
   aws ecs wait services-stable --cluster $CLUSTER_NAME --services $SERVICE_NAME --region $REGION
   aws logs tail $LOG_GROUP --follow --region $REGION
   ```

### High Cost Alert

**Scenario**: AWS costs are exceeding budget.

**Emergency Response**:

1. **Check current task count**:
   ```bash
   aws ecs describe-services \
     --cluster $CLUSTER_NAME \
     --services $SERVICE_NAME \
     --region $REGION \
     --query 'services[0].{Running:runningCount,Desired:desiredCount}'
   ```

2. **Review scaling activities**:
   ```bash
   aws application-autoscaling describe-scaling-activities \
     --service-namespace ecs \
     --resource-id "service/${CLUSTER_NAME}/${SERVICE_NAME}" \
     --max-results 20 \
     --region $REGION
   ```

3. **Reduce max capacity**:
   ```bash
   aws application-autoscaling register-scalable-target \
     --service-namespace ecs \
     --resource-id "service/${CLUSTER_NAME}/${SERVICE_NAME}" \
     --scalable-dimension ecs:service:DesiredCount \
     --min-capacity 2 \
     --max-capacity 5 \
     --region $REGION
   ```

4. **Scale down immediately if needed**:
   ```bash
   aws ecs update-service \
     --cluster $CLUSTER_NAME \
     --service $SERVICE_NAME \
     --desired-count 2 \
     --region $REGION
   ```

### Security Incident

**Scenario**: Suspected security breach or vulnerability.

**Emergency Response**:

1. **Isolate affected tasks**:
   ```bash
   # Scale down to minimum
   aws ecs update-service \
     --cluster $CLUSTER_NAME \
     --service $SERVICE_NAME \
     --desired-count 0 \
     --region $REGION
   ```

2. **Review security groups**:
   ```bash
   # Check ECS security group rules
   aws ec2 describe-security-groups \
     --filters "Name=tag:Name,Values=vibejudge-ecs-sg-${ENV}" \
     --region $REGION
   ```

3. **Review CloudTrail logs**: Check for unauthorized API calls

4. **Scan ECR images**:
   ```bash
   aws ecr describe-image-scan-findings \
     --repository-name vibejudge-dashboard \
     --image-id imageTag=latest \
     --region $REGION
   ```

5. **Deploy patched version**: Build and deploy new image with security fixes

### Data Loss or Corruption

**Scenario**: Application data is lost or corrupted.

**Note**: The Streamlit dashboard is stateless - it doesn't store data. All data is in the backend API (DynamoDB).

**Response**:

1. **Verify backend API**: Check DynamoDB tables and Lambda functions
2. **Restart dashboard**: Force new deployment to clear any cached state
   ```bash
   aws ecs update-service \
     --cluster $CLUSTER_NAME \
     --service $SERVICE_NAME \
     --force-new-deployment \
     --region $REGION
   ```

---

## Additional Resources

- **Deployment Guide**: See `DEPLOYMENT.md` for deployment procedures
- **CloudWatch Queries**: See `cloudwatch-queries.md` for log analysis queries
- **AWS ECS Documentation**: https://docs.aws.amazon.com/ecs/
- **AWS CloudWatch Documentation**: https://docs.aws.amazon.com/cloudwatch/
- **Streamlit Documentation**: https://docs.streamlit.io/

---

**Last Updated**: February 2026  
**Version**: 1.0  
**Maintained by**: VibeJudge AI Team
