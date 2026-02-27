# VibeJudge AI - Deployment Guide

## CRITICAL: Two Separate Deployments

VibeJudge AI has TWO independent deployments that must NEVER be confused:

1. **Backend API (Lambda)** - Python FastAPI application
2. **Frontend Dashboard (ECS)** - Streamlit web application

---

## 1. Backend API Deployment (Lambda + API Gateway)

### Files Used
- **Template:** `template.yaml` (Lambda SAM template)
- **Code:** `src/` directory (all Python code)
- **Dependencies:** `requirements.txt` (root directory)
- **Config:** `samconfig.toml`

### Stack Information
- **Stack Name:** `vibejudge-dev`
- **Resources:** 2 Lambda functions, API Gateway, DynamoDB, S3
- **API URL:** https://2nu0j4n648.execute-api.us-east-1.amazonaws.com/dev/

### Lambda Functions
1. **vibejudge-api-dev**
   - Handler: `src.api.main.handler`
   - CodeUri: `./` (project root)
   - Memory: 1024 MB
   - Timeout: 30s

2. **vibejudge-analyzer-dev**
   - Handler: `src.analysis.lambda_handler.handler`
   - CodeUri: `./` (project root)
   - Memory: 2048 MB
   - Timeout: 900s (15 min)

### Deployment Commands

```bash
# Build with dependencies (CRITICAL: uses Docker container)
sam build --use-container

# Deploy to dev
sam deploy --stack-name vibejudge-dev \
  --capabilities CAPABILITY_NAMED_IAM \
  --no-confirm-changeset \
  --no-fail-on-empty-changeset

# Or use Makefile
make deploy-dev
```

### Verification

```bash
# Test health endpoint
curl https://2nu0j4n648.execute-api.us-east-1.amazonaws.com/dev/health

# Check Lambda logs
aws logs tail /aws/lambda/vibejudge-api-dev --since 5m --follow

# Check function size (should be several MB with dependencies)
aws lambda get-function --function-name vibejudge-api-dev \
  --query 'Configuration.CodeSize'
```

### Common Issues

**Issue:** Lambda shows "No module named 'structlog'" error
- **Cause:** Dependencies not bundled
- **Fix:** Ensure `sam build --use-container` is used (NOT just `sam build`)

**Issue:** Lambda shows "No module named 'src'" error
- **Cause:** Wrong handler path or CodeUri
- **Fix:** Verify template.yaml has:
  - `CodeUri: ./`
  - `Handler: src.api.main.handler`

---

## 2. Frontend Dashboard Deployment (ECS Fargate)

### Files Used
- **Template:** `template-ecs.yaml` (ECS CloudFormation template)
- **Code:** `streamlit_ui/` directory
- **Dockerfile:** `streamlit_ui/Dockerfile`
- **Dependencies:** `streamlit_ui/requirements.txt`

### Stack Information
- **Stack Name:** `vibejudge-dashboard-prod`
- **Resources:** ECS Cluster, Fargate Service, ALB, VPC
- **Dashboard URL:** http://vibejudge-alb-prod-[id].us-east-1.elb.amazonaws.com

### Docker Image
- **Registry:** ECR (607415053998.dkr.ecr.us-east-1.amazonaws.com)
- **Repository:** vibejudge-dashboard
- **Platform:** linux/amd64 (REQUIRED for ECS Fargate)

### Deployment Commands

```bash
# 1. Build Docker image (MUST specify platform)
cd streamlit_ui
docker build --platform linux/amd64 -t vibejudge-dashboard:latest .

# 2. Login to ECR
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin \
  607415053998.dkr.ecr.us-east-1.amazonaws.com

# 3. Tag image
docker tag vibejudge-dashboard:latest \
  607415053998.dkr.ecr.us-east-1.amazonaws.com/vibejudge-dashboard:latest

# 4. Push to ECR
docker push 607415053998.dkr.ecr.us-east-1.amazonaws.com/vibejudge-dashboard:latest

# 5. Update ECS service (force new deployment)
aws ecs update-service \
  --cluster vibejudge-cluster-prod \
  --service vibejudge-dashboard-prod \
  --force-new-deployment
```

### Verification

```bash
# Check ECS service status
aws ecs describe-services \
  --cluster vibejudge-cluster-prod \
  --services vibejudge-dashboard-prod \
  --query 'services[0].[runningCount,desiredCount,deployments[0].status]'

# Check task health
aws ecs list-tasks \
  --cluster vibejudge-cluster-prod \
  --service-name vibejudge-dashboard-prod

# View logs
aws logs tail /ecs/vibejudge-dashboard-prod --since 10m --follow
```

### Common Issues

**Issue:** ECS tasks fail to start with "exec format error"
- **Cause:** Docker image built for wrong platform (arm64 vs amd64)
- **Fix:** Always use `--platform linux/amd64` in docker build

**Issue:** Dashboard shows "Connection refused" to API
- **Cause:** Wrong API_BASE_URL environment variable
- **Fix:** Verify ECS task definition has correct API_BASE_URL

---

## File Organization Reference

```
vibejudge/
├── template.yaml              # ← BACKEND Lambda deployment
├── template-ecs.yaml          # ← FRONTEND ECS deployment
├── requirements.txt           # ← Backend dependencies
├── samconfig.toml            # ← Backend SAM config
│
├── src/                      # ← Backend Python code
│   ├── api/                  # ← Lambda API handler
│   ├── analysis/             # ← Lambda analyzer handler
│   ├── models/               # ← Shared Pydantic models
│   ├── services/             # ← Business logic
│   ├── agents/               # ← AI agents
│   └── utils/                # ← Utilities
│
└── streamlit_ui/             # ← Frontend Streamlit app
    ├── Dockerfile            # ← Frontend container
    ├── requirements.txt      # ← Frontend dependencies
    ├── app.py               # ← Main Streamlit app
    ├── pages/               # ← Dashboard pages
    └── components/          # ← Reusable components
```

---

## Deployment Checklist

### Before Deploying Backend (Lambda)

- [ ] Verify `template.yaml` is the Lambda template (not ECS)
- [ ] Check `CodeUri: ./` and `Handler: src.api.main.handler`
- [ ] Ensure `requirements.txt` exists in root directory
- [ ] Run `sam build --use-container` (NOT just `sam build`)
- [ ] Verify build output shows "ResolveDependencies" step
- [ ] Check built artifacts size (should be several MB)

### Before Deploying Frontend (ECS)

- [ ] Verify `template-ecs.yaml` is being used (not template.yaml)
- [ ] Build Docker image with `--platform linux/amd64`
- [ ] Push image to ECR before updating service
- [ ] Verify API_BASE_URL environment variable is correct
- [ ] Check ECS task definition has correct image tag

### After Deployment

- [ ] Test backend health endpoint
- [ ] Check Lambda CloudWatch logs for errors
- [ ] Test frontend dashboard loads
- [ ] Verify dashboard can connect to API
- [ ] Check ECS task is running and healthy

---

## Emergency Rollback

### Backend (Lambda)

```bash
# List recent deployments
aws cloudformation describe-stack-events \
  --stack-name vibejudge-dev \
  --max-items 20

# Rollback to previous version
aws cloudformation cancel-update-stack --stack-name vibejudge-dev
```

### Frontend (ECS)

```bash
# Rollback to previous task definition
aws ecs update-service \
  --cluster vibejudge-cluster-prod \
  --service vibejudge-dashboard-prod \
  --task-definition vibejudge-dashboard-prod:7  # Previous version

# Or use previous Docker image tag
docker pull 607415053998.dkr.ecr.us-east-1.amazonaws.com/vibejudge-dashboard:previous-tag
# ... then push and update service
```

---

## Quick Reference

### Backend API
- **Deploy:** `sam build --use-container && sam deploy --stack-name vibejudge-dev --capabilities CAPABILITY_NAMED_IAM --no-confirm-changeset`
- **Test:** `curl https://2nu0j4n648.execute-api.us-east-1.amazonaws.com/dev/health`
- **Logs:** `aws logs tail /aws/lambda/vibejudge-api-dev --since 5m`

### Frontend Dashboard
- **Build:** `cd streamlit_ui && docker build --platform linux/amd64 -t vibejudge-dashboard:latest .`
- **Push:** `docker push 607415053998.dkr.ecr.us-east-1.amazonaws.com/vibejudge-dashboard:latest`
- **Deploy:** `aws ecs update-service --cluster vibejudge-cluster-prod --service vibejudge-dashboard-prod --force-new-deployment`
- **Logs:** `aws logs tail /ecs/vibejudge-dashboard-prod --since 10m`

---

## CRITICAL RULES

1. **NEVER** use `template-ecs.yaml` for Lambda deployment
2. **NEVER** use `template.yaml` for ECS deployment
3. **ALWAYS** use `--use-container` with `sam build`
4. **ALWAYS** use `--platform linux/amd64` with `docker build`
5. **ALWAYS** verify handler paths match code structure
6. **ALWAYS** test after deployment before considering it complete

---

## Contact & Support

- **CloudWatch Logs:** Check first for all errors
- **Stack Events:** `aws cloudformation describe-stack-events --stack-name <stack-name>`
- **Service Status:** `aws ecs describe-services` or `aws lambda get-function`
