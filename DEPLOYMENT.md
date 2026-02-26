# VibeJudge AI — Streamlit Dashboard Deployment Guide

This guide provides comprehensive instructions for deploying the VibeJudge AI Streamlit Organizer Dashboard to AWS ECS Fargate.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Deployment Steps](#deployment-steps)
- [Accessing the Dashboard](#accessing-the-dashboard)
- [Viewing Logs and Metrics](#viewing-logs-and-metrics)
- [Rollback Procedures](#rollback-procedures)
- [Troubleshooting](#troubleshooting)
- [Cost Management](#cost-management)

---

## Prerequisites

Before deploying, ensure you have the following tools installed and configured:

### Required Tools

1. **AWS CLI** (version 2.x)
   - Installation: https://aws.amazon.com/cli/
   - Verify: `aws --version`
   - Configure: `aws configure` (set access key, secret key, region: us-east-1)

2. **Docker** (version 20.10+)
   - Installation: https://docs.docker.com/get-docker/
   - Verify: `docker --version`
   - Ensure Docker daemon is running: `docker info`

3. **AWS SAM CLI** (version 1.100+)
   - Installation: https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html
   - Verify: `sam --version`

4. **Git** (version 2.x)
   - Installation: https://git-scm.com/downloads
   - Verify: `git --version`

### AWS Account Requirements

- AWS account with appropriate permissions:
  - ECR: Create repositories, push images
  - ECS: Create clusters, services, task definitions
  - EC2: Create VPCs, subnets, security groups
  - ELB: Create Application Load Balancers
  - CloudWatch: Create log groups, alarms
  - IAM: Create roles and policies
  - CloudFormation: Create and manage stacks

- AWS credentials configured via `aws configure` or environment variables

### Repository Setup

- Clone the VibeJudge AI repository
- Ensure you're on the correct branch with the latest changes
- Verify all files are committed (deployment uses Git commit SHA for image tagging)

---

## Quick Start

For experienced users, deploy in 3 commands:

```bash
# 1. Make deployment script executable
chmod +x deploy.sh

# 2. Deploy to dev environment
./deploy.sh dev

# 3. Access dashboard at the URL displayed in output
```

---

## Deployment Steps

### Step 1: Validate Prerequisites

The deployment script automatically validates all prerequisites. To manually verify:

```bash
# Check AWS CLI
aws --version
aws sts get-caller-identity  # Verify credentials

# Check Docker
docker --version
docker info  # Verify daemon is running

# Check SAM CLI
sam --version

# Check Git
git --version
git status  # Verify repository state
```

### Step 2: Configure Deployment Environment

The deployment supports two environments:

- **dev**: Development environment for testing
- **prod**: Production environment for live usage

Configuration is managed in `samconfig.toml`:

```toml
[dev.deploy.parameters]
stack_name = "vibejudge-dashboard-dev"
region = "us-east-1"
confirm_changeset = false
capabilities = "CAPABILITY_IAM"

[prod.deploy.parameters]
stack_name = "vibejudge-dashboard-prod"
region = "us-east-1"
confirm_changeset = true  # Requires manual approval
capabilities = "CAPABILITY_IAM"
```

### Step 3: Run Deployment Script

Execute the deployment script with your target environment:

```bash
# Deploy to dev environment
./deploy.sh dev

# Deploy to prod environment (requires changeset confirmation)
./deploy.sh prod
```

The script performs the following steps automatically:

1. **Prerequisite Validation**: Checks all required tools are installed
2. **Docker Build**: Builds container image with Git commit SHA tag
3. **Image Tagging**: Tags image with both commit SHA and "latest"
4. **ECR Authentication**: Authenticates Docker with AWS ECR
5. **Image Push**: Pushes both image tags to ECR
6. **Infrastructure Deployment**: Deploys SAM template via CloudFormation
7. **Service Stabilization**: Waits for ECS service to reach stable state
8. **Output Display**: Shows ALB URL and deployment details

### Step 4: Verify Deployment

After successful deployment, verify the service is running:

```bash
# Check ECS service status
aws ecs describe-services \
  --cluster vibejudge-cluster-dev \
  --services vibejudge-dashboard-service-dev \
  --region us-east-1 \
  --query 'services[0].{Status:status,Running:runningCount,Desired:desiredCount}'

# Expected output:
# {
#   "Status": "ACTIVE",
#   "Running": 2,
#   "Desired": 2
# }
```

---

## Accessing the Dashboard

### Using ALB DNS Name

After deployment, the script displays the Application Load Balancer DNS name:

```
Dashboard URL:
  http://vibejudge-alb-dev-1234567890.us-east-1.elb.amazonaws.com
```

Access the dashboard by opening this URL in your browser.

### Setting Up Custom Domain (Optional)

To use a custom domain (e.g., `dashboard.vibejudge.ai`):

1. **Request ACM Certificate**:
   ```bash
   aws acm request-certificate \
     --domain-name dashboard.vibejudge.ai \
     --validation-method DNS \
     --region us-east-1
   ```

2. **Validate Certificate**: Add DNS records as instructed by ACM

3. **Update ALB Listener**: Attach certificate to HTTPS listener (443)
   - Navigate to EC2 Console → Load Balancers
   - Select your ALB → Listeners tab
   - Edit HTTPS:443 listener → Add certificate

4. **Update DNS**: Create CNAME record pointing to ALB DNS name
   ```
   dashboard.vibejudge.ai → vibejudge-alb-dev-1234567890.us-east-1.elb.amazonaws.com
   ```

### Configuring Backend API URL

The Streamlit dashboard connects to the VibeJudge backend API. Configure the API URL:

1. **Via Environment Variable** (in task definition):
   - Edit `template.yaml`
   - Update `API_BASE_URL` environment variable in task definition
   - Redeploy with `./deploy.sh <env>`

2. **Via Streamlit UI**:
   - Users can enter their API key in the dashboard
   - API URL is configured in `streamlit_ui/components/api_client.py`

---

## Viewing Logs and Metrics

### CloudWatch Logs

All container logs are sent to CloudWatch Logs group `/ecs/vibejudge-dashboard`.

**View logs in real-time**:
```bash
# Tail logs (follow mode)
aws logs tail /ecs/vibejudge-dashboard --follow --region us-east-1

# View last 100 lines
aws logs tail /ecs/vibejudge-dashboard --since 10m --region us-east-1
```

**View logs in AWS Console**:
1. Navigate to CloudWatch → Log groups
2. Select `/ecs/vibejudge-dashboard`
3. Click on latest log stream

**CloudWatch Logs Insights Queries**:

Find errors:
```sql
fields @timestamp, @message
| filter @message like /ERROR|Exception|Failed/
| sort @timestamp desc
| limit 100
```

Track response times:
```sql
fields @timestamp, @message
| filter @message like /response_time/
| stats avg(response_time) as avg_response, max(response_time) as max_response by bin(5m)
```

Monitor health checks:
```sql
fields @timestamp, @message
| filter @message like /_stcore\/health/
| stats count() by bin(1m)
```

### CloudWatch Metrics

**ECS Service Metrics**:
- `CPUUtilization`: Target 70%, alert > 90%
- `MemoryUtilization`: Target 60%, alert > 90%
- `DesiredTaskCount`: Baseline 2, max 10
- `RunningTaskCount`: Should equal DesiredTaskCount

**ALB Metrics**:
- `TargetResponseTime`: Target < 2s, alert > 5s
- `RequestCount`: Track traffic patterns
- `HealthyHostCount`: Alert if < 1
- `UnHealthyHostCount`: Alert if > 0
- `HTTPCode_Target_5XX_Count`: Monitor server errors

**View metrics in AWS Console**:
1. Navigate to CloudWatch → Metrics
2. Select ECS or ApplicationELB namespace
3. Select metrics to visualize

**View metrics via CLI**:
```bash
# ECS CPU utilization
aws cloudwatch get-metric-statistics \
  --namespace AWS/ECS \
  --metric-name CPUUtilization \
  --dimensions Name=ServiceName,Value=vibejudge-dashboard-service-dev Name=ClusterName,Value=vibejudge-cluster-dev \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Average \
  --region us-east-1
```

### CloudWatch Alarms

The deployment creates two alarms:

1. **Healthy Host Count Alarm**: Triggers when no healthy tasks are available
2. **Response Time Alarm**: Triggers when response time exceeds 5 seconds

**View alarm status**:
```bash
aws cloudwatch describe-alarms \
  --alarm-name-prefix vibejudge-dashboard \
  --region us-east-1
```

**Subscribe to alarm notifications**:
```bash
# Get SNS topic ARN from CloudFormation outputs
TOPIC_ARN=$(aws cloudformation describe-stacks \
  --stack-name vibejudge-dashboard-dev \
  --region us-east-1 \
  --query 'Stacks[0].Outputs[?OutputKey==`AlarmTopicArn`].OutputValue' \
  --output text)

# Subscribe email to topic
aws sns subscribe \
  --topic-arn $TOPIC_ARN \
  --protocol email \
  --notification-endpoint your-email@example.com \
  --region us-east-1
```

### ECS Service Status

**Check service health**:
```bash
aws ecs describe-services \
  --cluster vibejudge-cluster-dev \
  --services vibejudge-dashboard-service-dev \
  --region us-east-1
```

**List running tasks**:
```bash
aws ecs list-tasks \
  --cluster vibejudge-cluster-dev \
  --service-name vibejudge-dashboard-service-dev \
  --region us-east-1
```

**Describe task details**:
```bash
# Get task ARN from list-tasks output
TASK_ARN="<task-arn>"

aws ecs describe-tasks \
  --cluster vibejudge-cluster-dev \
  --tasks $TASK_ARN \
  --region us-east-1
```

### ALB Target Health

**Check target health**:
```bash
# Get target group ARN from CloudFormation outputs
TARGET_GROUP_ARN=$(aws cloudformation describe-stacks \
  --stack-name vibejudge-dashboard-dev \
  --region us-east-1 \
  --query 'Stacks[0].Outputs[?OutputKey==`TargetGroupArn`].OutputValue' \
  --output text)

# Check health
aws elbv2 describe-target-health \
  --target-group-arn $TARGET_GROUP_ARN \
  --region us-east-1
```

---

## Rollback Procedures

### Automatic Rollback

The ECS service is configured with deployment circuit breaker, which automatically rolls back failed deployments:

- If new tasks fail to reach healthy status
- If health checks fail repeatedly
- If deployment exceeds timeout

**No manual intervention required** — ECS automatically reverts to the previous task definition.

### Manual Rollback

If you need to manually rollback to a previous version:

#### Option 1: Rollback via ECS Console

1. Navigate to ECS Console → Clusters → vibejudge-cluster-dev
2. Select service: vibejudge-dashboard-service-dev
3. Click "Update" → "Revision" tab
4. Select previous task definition revision
5. Click "Update Service"

#### Option 2: Rollback via CLI

```bash
# List task definition revisions
aws ecs list-task-definitions \
  --family-prefix vibejudge-dashboard \
  --region us-east-1

# Update service to use previous revision
aws ecs update-service \
  --cluster vibejudge-cluster-dev \
  --service vibejudge-dashboard-service-dev \
  --task-definition vibejudge-dashboard-dev:PREVIOUS_REVISION \
  --region us-east-1

# Wait for service to stabilize
aws ecs wait services-stable \
  --cluster vibejudge-cluster-dev \
  --services vibejudge-dashboard-service-dev \
  --region us-east-1
```

#### Option 3: Rollback via Deployment Script

Redeploy a previous Git commit:

```bash
# Checkout previous commit
git checkout <previous-commit-sha>

# Redeploy
./deploy.sh dev

# Return to latest
git checkout main
```

### Rollback CloudFormation Stack

If infrastructure changes need to be rolled back:

```bash
# View stack change sets
aws cloudformation list-change-sets \
  --stack-name vibejudge-dashboard-dev \
  --region us-east-1

# Rollback to previous stack state
aws cloudformation cancel-update-stack \
  --stack-name vibejudge-dashboard-dev \
  --region us-east-1
```

---

## Troubleshooting

### Issue: Deployment Script Fails at Prerequisite Validation

**Symptoms**: Script exits with "ERROR: <tool> is not installed"

**Solutions**:
- Install missing tool (see [Prerequisites](#prerequisites))
- Verify tool is in PATH: `which <tool>`
- For Docker: Ensure daemon is running: `docker info`
- For AWS CLI: Verify credentials: `aws sts get-caller-identity`

### Issue: Docker Build Fails

**Symptoms**: "Docker build failed" error

**Solutions**:
```bash
# Check Dockerfile syntax
docker build -t test -f Dockerfile .

# Check for missing files
ls -la streamlit_ui/

# Verify .dockerignore isn't excluding required files
cat .dockerignore

# Check Docker disk space
docker system df
docker system prune  # Clean up if needed
```

### Issue: ECR Authentication Fails

**Symptoms**: "Failed to authenticate with ECR"

**Solutions**:
```bash
# Verify AWS credentials
aws sts get-caller-identity

# Check ECR permissions
aws ecr describe-repositories --region us-east-1

# Manually authenticate
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin \
  <account-id>.dkr.ecr.us-east-1.amazonaws.com

# If repository doesn't exist, deploy SAM template first
sam deploy --config-env dev --guided
```

### Issue: ECR Image Push Fails

**Symptoms**: "Failed to push image"

**Solutions**:
- Verify ECR repository exists: `aws ecr describe-repositories --region us-east-1`
- Check image size: `docker images vibejudge-dashboard`
- Verify network connectivity to ECR
- Check ECR lifecycle policy isn't deleting images too aggressively

### Issue: SAM Deployment Fails

**Symptoms**: "SAM deployment failed"

**Solutions**:
```bash
# View CloudFormation events
aws cloudformation describe-stack-events \
  --stack-name vibejudge-dashboard-dev \
  --region us-east-1 \
  --max-items 20

# Check for resource limits (VPC, EIP, etc.)
aws service-quotas list-service-quotas \
  --service-code ec2 \
  --region us-east-1

# Validate template syntax
sam validate --region us-east-1

# Deploy with debug output
sam deploy --config-env dev --debug
```

### Issue: ECS Service Fails to Stabilize

**Symptoms**: "Service failed to stabilize within 15 minutes"

**Solutions**:

1. **Check task status**:
   ```bash
   aws ecs describe-tasks \
     --cluster vibejudge-cluster-dev \
     --tasks $(aws ecs list-tasks --cluster vibejudge-cluster-dev --service-name vibejudge-dashboard-service-dev --query 'taskArns[0]' --output text) \
     --region us-east-1
   ```

2. **Check container logs**:
   ```bash
   aws logs tail /ecs/vibejudge-dashboard --follow --region us-east-1
   ```

3. **Common causes**:
   - Container fails to start (check logs for errors)
   - Health check endpoint not responding (verify `/_stcore/health`)
   - Insufficient memory/CPU (check task definition)
   - Image pull errors (verify ECR permissions)
   - Port conflicts (verify port 8501 is exposed)

4. **Check ALB target health**:
   ```bash
   # Get target group ARN from stack outputs
   TARGET_GROUP_ARN=$(aws cloudformation describe-stacks \
     --stack-name vibejudge-dashboard-dev \
     --region us-east-1 \
     --query 'Stacks[0].Outputs[?OutputKey==`TargetGroupArn`].OutputValue' \
     --output text)
   
   # Check health
   aws elbv2 describe-target-health \
     --target-group-arn $TARGET_GROUP_ARN \
     --region us-east-1
   ```

### Issue: Dashboard Not Accessible

**Symptoms**: Cannot access dashboard via ALB URL

**Solutions**:

1. **Verify ALB is active**:
   ```bash
   aws elbv2 describe-load-balancers \
     --region us-east-1 \
     --query 'LoadBalancers[?contains(LoadBalancerName, `vibejudge`)].{Name:LoadBalancerName,DNS:DNSName,State:State.Code}'
   ```

2. **Check security groups**:
   - ALB security group: Allow inbound 80/443 from 0.0.0.0/0
   - ECS security group: Allow inbound 8501 from ALB security group

3. **Verify target health**:
   ```bash
   aws elbv2 describe-target-health \
     --target-group-arn <target-group-arn> \
     --region us-east-1
   ```

4. **Check DNS resolution**:
   ```bash
   nslookup <alb-dns-name>
   curl -I http://<alb-dns-name>
   ```

### Issue: High Response Times

**Symptoms**: Dashboard loads slowly (>5 seconds)

**Solutions**:

1. **Check CPU/Memory utilization**:
   ```bash
   aws cloudwatch get-metric-statistics \
     --namespace AWS/ECS \
     --metric-name CPUUtilization \
     --dimensions Name=ServiceName,Value=vibejudge-dashboard-service-dev Name=ClusterName,Value=vibejudge-cluster-dev \
     --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
     --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
     --period 300 \
     --statistics Average \
     --region us-east-1
   ```

2. **Scale up manually**:
   ```bash
   aws ecs update-service \
     --cluster vibejudge-cluster-dev \
     --service vibejudge-dashboard-service-dev \
     --desired-count 4 \
     --region us-east-1
   ```

3. **Increase task resources** (edit `template.yaml`):
   - CPU: 512 → 1024 (1 vCPU)
   - Memory: 1024 → 2048 (2GB)

4. **Check backend API latency**:
   - Verify backend API is responding quickly
   - Check network connectivity between ECS and API Gateway

### Issue: Container Out of Memory

**Symptoms**: Tasks repeatedly fail with "OutOfMemoryError"

**Solutions**:

1. **Check memory utilization**:
   ```bash
   aws cloudwatch get-metric-statistics \
     --namespace AWS/ECS \
     --metric-name MemoryUtilization \
     --dimensions Name=ServiceName,Value=vibejudge-dashboard-service-dev Name=ClusterName,Value=vibejudge-cluster-dev \
     --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
     --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
     --period 300 \
     --statistics Average,Maximum \
     --region us-east-1
   ```

2. **Increase task memory** (edit `template.yaml`):
   ```yaml
   Memory: 2048  # Increase from 1024 to 2048
   ```

3. **Optimize Streamlit caching**:
   - Review `@st.cache_data` usage
   - Reduce cache TTL
   - Clear cache periodically

### Issue: Auto-Scaling Not Working

**Symptoms**: Task count doesn't change despite high CPU

**Solutions**:

1. **Verify scaling policy**:
   ```bash
   aws application-autoscaling describe-scaling-policies \
     --service-namespace ecs \
     --region us-east-1
   ```

2. **Check CloudWatch alarms**:
   ```bash
   aws cloudwatch describe-alarms \
     --alarm-name-prefix TargetTracking \
     --region us-east-1
   ```

3. **Verify scaling target**:
   ```bash
   aws application-autoscaling describe-scalable-targets \
     --service-namespace ecs \
     --region us-east-1
   ```

4. **Check scaling activities**:
   ```bash
   aws application-autoscaling describe-scaling-activities \
     --service-namespace ecs \
     --resource-id service/vibejudge-cluster-dev/vibejudge-dashboard-service-dev \
     --region us-east-1
   ```

### Issue: Cost Exceeds Budget

**Symptoms**: AWS bill higher than expected

**Solutions**:

1. **Check current task count**:
   ```bash
   aws ecs describe-services \
     --cluster vibejudge-cluster-dev \
     --services vibejudge-dashboard-service-dev \
     --region us-east-1 \
     --query 'services[0].{Running:runningCount,Desired:desiredCount}'
   ```

2. **Reduce max capacity** (edit `template.yaml`):
   ```yaml
   MaxCapacity: 5  # Reduce from 10 to 5
   ```

3. **Verify FARGATE_SPOT usage**:
   - Check capacity provider strategy in template
   - Ensure FARGATE_SPOT is preferred

4. **Review CloudWatch costs**:
   - Reduce log retention: 7 days → 3 days
   - Disable Container Insights if not needed

5. **Set up billing alerts**:
   ```bash
   aws cloudwatch put-metric-alarm \
     --alarm-name vibejudge-billing-alert \
     --alarm-description "Alert when estimated charges exceed $100" \
     --metric-name EstimatedCharges \
     --namespace AWS/Billing \
     --statistic Maximum \
     --period 21600 \
     --evaluation-periods 1 \
     --threshold 100 \
     --comparison-operator GreaterThanThreshold \
     --region us-east-1
   ```

---

## Cost Management

### Expected Costs

**Baseline (2 tasks, 24/7)**:
- Fargate: ~$27/month (with FARGATE_SPOT)
- ALB: ~$16/month
- CloudWatch: ~$5/month
- ECR: ~$1/month
- **Total: ~$54/month**

**Peak Load (10 tasks, 24/7)**:
- Fargate: ~$135/month
- ALB: ~$16/month
- CloudWatch: ~$5/month
- **Total: ~$155/month**

### Cost Optimization Tips

1. **Use FARGATE_SPOT**: 70% savings vs standard Fargate (already configured)

2. **Reduce log retention**: 7 days → 3 days (edit `template.yaml`)

3. **Scale down during off-hours**: Use scheduled scaling
   ```bash
   # Scale down at night (example)
   aws application-autoscaling put-scheduled-action \
     --service-namespace ecs \
     --resource-id service/vibejudge-cluster-dev/vibejudge-dashboard-service-dev \
     --scheduled-action-name scale-down-night \
     --schedule "cron(0 22 * * ? *)" \
     --scalable-target-action MinCapacity=1,MaxCapacity=2 \
     --region us-east-1
   ```

4. **Disable Container Insights**: Saves ~$2/month (edit `template.yaml`)

5. **Use ALB access logs sparingly**: Only enable when debugging

6. **Clean up old ECR images**: Lifecycle policy keeps only 10 images (already configured)

### Monitoring Costs

**View current month costs**:
```bash
aws ce get-cost-and-usage \
  --time-period Start=$(date -u +%Y-%m-01),End=$(date -u +%Y-%m-%d) \
  --granularity MONTHLY \
  --metrics BlendedCost \
  --group-by Type=SERVICE \
  --region us-east-1
```

**Set up cost alerts**: See [Troubleshooting - Cost Exceeds Budget](#issue-cost-exceeds-budget)

---

## Additional Resources

- **AWS ECS Documentation**: https://docs.aws.amazon.com/ecs/
- **AWS SAM Documentation**: https://docs.aws.amazon.com/serverless-application-model/
- **Streamlit Documentation**: https://docs.streamlit.io/
- **Project README**: See `README.md` for project overview
- **Operational Runbook**: See `RUNBOOK.md` for common operations
- **CloudWatch Queries**: See `cloudwatch-queries.md` for log analysis

---

## Support

For issues or questions:

1. Check [Troubleshooting](#troubleshooting) section
2. Review CloudWatch logs for error messages
3. Check AWS CloudFormation events for infrastructure issues
4. Consult AWS documentation for service-specific issues

---

**Last Updated**: February 2026  
**Version**: 1.0  
**Deployment Target**: AWS ECS Fargate (us-east-1)
