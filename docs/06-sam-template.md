# VibeJudge AI — SAM Template (Infrastructure as Code)

> **Version:** 1.0  
> **Date:** February 2026  
> **Author:** Maku Mazakpe / Vibe Coders  
> **Status:** APPROVED  
> **Depends On:** ADR-002 (SAM), ADR-004 (DynamoDB), Deliverable #3 (Data Model), Deliverable #5 (API Spec)  
> **Deploy Command:** `sam build && sam deploy --guided`

---

## Template Overview

This SAM template defines the complete VibeJudge infrastructure:

| Resource | Type | Free Tier? |
|----------|------|-----------|
| API Lambda | Lambda Function (FastAPI) | ✅ 1M requests/mo |
| Analyzer Lambda | Lambda Function (batch analysis) | ✅ 400K GB-sec/mo |
| HTTP API | API Gateway v2 | ✅ 1M requests/mo (12 months) |
| DynamoDB Table | Single-table + 2 GSIs | ✅ 25 RCU/WCU always free |
| S3 Bucket | Static assets + raw responses | ✅ 5GB (12 months) |
| CloudWatch Alarms | Budget + error alerts | ✅ 10 alarms |

---

## template.yaml

```yaml
AWSTemplateFormatVersion: '2010-09-09'
Transform: AWS::Serverless-2016-10-31

Description: >
  VibeJudge AI — AI-powered hackathon judging platform.
  Multi-agent system on Amazon Bedrock for automated code evaluation.
  AWS 10,000 AIdeas Competition — Vibe Coders.

# ============================================================
# PARAMETERS
# ============================================================
Parameters:
  Environment:
    Type: String
    Default: dev
    AllowedValues: [dev, staging, prod]
    Description: Deployment environment

  BedrockRegion:
    Type: String
    Default: us-east-1
    Description: AWS Region for Bedrock API calls (model availability varies by region)

  LogLevel:
    Type: String
    Default: INFO
    AllowedValues: [DEBUG, INFO, WARNING, ERROR]
    Description: Application log level

# ============================================================
# GLOBALS
# ============================================================
Globals:
  Function:
    Runtime: python3.12
    Architectures:
      - x86_64
    Timeout: 30
    MemorySize: 512
    Environment:
      Variables:
        ENVIRONMENT: !Ref Environment
        TABLE_NAME: !Ref VibeJudgeTable
        BUCKET_NAME: !Ref VibeJudgeBucket
        BEDROCK_REGION: !Ref BedrockRegion
        LOG_LEVEL: !Ref LogLevel
        POWERTOOLS_SERVICE_NAME: vibejudge
    Tags:
      Project: VibeJudge
      Environment: !Ref Environment
      Competition: AWS-10000-AIdeas

# ============================================================
# RESOURCES
# ============================================================
Resources:

  # ----------------------------------------------------------
  # API GATEWAY (HTTP API v2 — 71% cheaper than REST API)
  # ----------------------------------------------------------
  VibeJudgeApi:
    Type: AWS::Serverless::HttpApi
    Properties:
      StageName: !Ref Environment
      Description: VibeJudge AI API
      CorsConfiguration:
        AllowOrigins:
          - "*"
        AllowHeaders:
          - Content-Type
          - X-API-Key
          - Authorization
        AllowMethods:
          - GET
          - POST
          - PUT
          - DELETE
          - OPTIONS
      DefaultRouteSettings:
        ThrottlingBurstLimit: 100
        ThrottlingRateLimit: 50

  # ----------------------------------------------------------
  # LAMBDA: API FUNCTION (FastAPI + Mangum)
  # ----------------------------------------------------------
  ApiFunctionLogGroup:
    Type: AWS::Logs::LogGroup
    Properties:
      LogGroupName: !Sub "/aws/lambda/${ApiFunction}"
      RetentionInDays: 14

  ApiFunction:
    Type: AWS::Serverless::Function
    Properties:
      FunctionName: !Sub "vibejudge-api-${Environment}"
      Description: FastAPI application handling all API routes
      CodeUri: src/
      Handler: api.main.handler
      MemorySize: 1024
      Timeout: 30
      Events:
        # Catch-all proxy route — FastAPI handles internal routing
        ApiProxy:
          Type: HttpApi
          Properties:
            ApiId: !Ref VibeJudgeApi
            Path: /{proxy+}
            Method: ANY
        # Root path
        ApiRoot:
          Type: HttpApi
          Properties:
            ApiId: !Ref VibeJudgeApi
            Path: /
            Method: ANY
      Policies:
        - DynamoDBCrudPolicy:
            TableName: !Ref VibeJudgeTable
        - S3ReadPolicy:
            BucketName: !Ref VibeJudgeBucket
        - Statement:
            - Effect: Allow
              Action:
                - bedrock:InvokeModel
                - bedrock:InvokeModelWithResponseStream
              Resource: "*"
        - Statement:
            - Effect: Allow
              Action:
                - lambda:InvokeFunction
              Resource: !GetAtt AnalyzerFunction.Arn

  # ----------------------------------------------------------
  # LAMBDA: ANALYZER FUNCTION (Batch analysis — long-running)
  # ----------------------------------------------------------
  AnalyzerFunctionLogGroup:
    Type: AWS::Logs::LogGroup
    Properties:
      LogGroupName: !Sub "/aws/lambda/${AnalyzerFunction}"
      RetentionInDays: 14

  AnalyzerFunction:
    Type: AWS::Serverless::Function
    Properties:
      FunctionName: !Sub "vibejudge-analyzer-${Environment}"
      Description: Batch analysis engine — clones repos, runs AI agents, writes scores
      CodeUri: src/
      Handler: analysis.lambda_handler.handler
      MemorySize: 2048
      Timeout: 900               # 15 minutes — max Lambda timeout
      EphemeralStorage:
        Size: 2048               # 2GB /tmp for git clones
      Environment:
        Variables:
          ENVIRONMENT: !Ref Environment
          TABLE_NAME: !Ref VibeJudgeTable
          BUCKET_NAME: !Ref VibeJudgeBucket
          BEDROCK_REGION: !Ref BedrockRegion
          LOG_LEVEL: !Ref LogLevel
          POWERTOOLS_SERVICE_NAME: vibejudge-analyzer
      Policies:
        - DynamoDBCrudPolicy:
            TableName: !Ref VibeJudgeTable
        - S3CrudPolicy:
            BucketName: !Ref VibeJudgeBucket
        - Statement:
            - Effect: Allow
              Action:
                - bedrock:InvokeModel
                - bedrock:InvokeModelWithResponseStream
              Resource: "*"
        # CloudWatch metrics for cost tracking
        - Statement:
            - Effect: Allow
              Action:
                - cloudwatch:PutMetricData
              Resource: "*"

  # ----------------------------------------------------------
  # DYNAMODB TABLE (Single-table design)
  # ----------------------------------------------------------
  VibeJudgeTable:
    Type: AWS::DynamoDB::Table
    DeletionPolicy: Retain
    Properties:
      TableName: !Sub "vibejudge-${Environment}"
      BillingMode: PROVISIONED
      TableClass: STANDARD         # CRITICAL: Standard-IA NOT free tier eligible
      ProvisionedThroughput:
        ReadCapacityUnits: 5
        WriteCapacityUnits: 5
      AttributeDefinitions:
        - AttributeName: PK
          AttributeType: S
        - AttributeName: SK
          AttributeType: S
        - AttributeName: GSI1PK
          AttributeType: S
        - AttributeName: GSI1SK
          AttributeType: S
        - AttributeName: GSI2PK
          AttributeType: S
        - AttributeName: GSI2SK
          AttributeType: S
      KeySchema:
        - AttributeName: PK
          KeyType: HASH
        - AttributeName: SK
          KeyType: RANGE
      GlobalSecondaryIndexes:
        - IndexName: GSI1
          KeySchema:
            - AttributeName: GSI1PK
              KeyType: HASH
            - AttributeName: GSI1SK
              KeyType: RANGE
          Projection:
            ProjectionType: ALL
          ProvisionedThroughput:
            ReadCapacityUnits: 5
            WriteCapacityUnits: 5
        - IndexName: GSI2
          KeySchema:
            - AttributeName: GSI2PK
              KeyType: HASH
            - AttributeName: GSI2SK
              KeyType: RANGE
          Projection:
            ProjectionType: KEYS_ONLY
          ProvisionedThroughput:
            ReadCapacityUnits: 5
            WriteCapacityUnits: 5
      TimeToLiveSpecification:
        AttributeName: expires_at
        Enabled: true
      Tags:
        - Key: Project
          Value: VibeJudge
        - Key: Environment
          Value: !Ref Environment

  # ----------------------------------------------------------
  # S3 BUCKET (Raw responses, static assets)
  # ----------------------------------------------------------
  VibeJudgeBucket:
    Type: AWS::S3::Bucket
    Properties:
      BucketName: !Sub "vibejudge-${Environment}-${AWS::AccountId}"
      VersioningConfiguration:
        Status: Enabled
      LifecycleConfiguration:
        Rules:
          # Auto-delete raw LLM responses after 30 days
          - Id: CleanupRawResponses
            Prefix: raw-responses/
            Status: Enabled
            ExpirationInDays: 30
          # Move old scorecards to infrequent access after 90 days
          - Id: ArchiveOldScorecards
            Prefix: scorecards/
            Status: Enabled
            Transitions:
              - StorageClass: STANDARD_IA
                TransitionInDays: 90
      PublicAccessBlockConfiguration:
        BlockPublicAcls: true
        BlockPublicPolicy: true
        IgnorePublicAcls: true
        RestrictPublicBuckets: true
      Tags:
        - Key: Project
          Value: VibeJudge
        - Key: Environment
          Value: !Ref Environment

  # ----------------------------------------------------------
  # CLOUDWATCH ALARMS
  # ----------------------------------------------------------

  # Alarm: API Lambda errors
  ApiErrorAlarm:
    Type: AWS::CloudWatch::Alarm
    Properties:
      AlarmName: !Sub "vibejudge-api-errors-${Environment}"
      AlarmDescription: API Lambda function error rate exceeded threshold
      Namespace: AWS/Lambda
      MetricName: Errors
      Dimensions:
        - Name: FunctionName
          Value: !Ref ApiFunction
      Statistic: Sum
      Period: 300                 # 5 minutes
      EvaluationPeriods: 2
      Threshold: 5
      ComparisonOperator: GreaterThanThreshold
      TreatMissingData: notBreaching

  # Alarm: Analyzer Lambda errors
  AnalyzerErrorAlarm:
    Type: AWS::CloudWatch::Alarm
    Properties:
      AlarmName: !Sub "vibejudge-analyzer-errors-${Environment}"
      AlarmDescription: Analyzer Lambda function errors
      Namespace: AWS/Lambda
      MetricName: Errors
      Dimensions:
        - Name: FunctionName
          Value: !Ref AnalyzerFunction
      Statistic: Sum
      Period: 300
      EvaluationPeriods: 1
      Threshold: 3
      ComparisonOperator: GreaterThanThreshold
      TreatMissingData: notBreaching

  # Alarm: Analyzer Lambda duration approaching timeout
  AnalyzerDurationAlarm:
    Type: AWS::CloudWatch::Alarm
    Properties:
      AlarmName: !Sub "vibejudge-analyzer-duration-${Environment}"
      AlarmDescription: Analyzer approaching 15min timeout
      Namespace: AWS/Lambda
      MetricName: Duration
      Dimensions:
        - Name: FunctionName
          Value: !Ref AnalyzerFunction
      Statistic: Maximum
      Period: 300
      EvaluationPeriods: 1
      Threshold: 840000          # 14 minutes in milliseconds (approaching 15min limit)
      ComparisonOperator: GreaterThanThreshold
      TreatMissingData: notBreaching

  # Alarm: DynamoDB read throttling
  DynamoDBReadThrottleAlarm:
    Type: AWS::CloudWatch::Alarm
    Properties:
      AlarmName: !Sub "vibejudge-dynamo-read-throttle-${Environment}"
      AlarmDescription: DynamoDB read requests being throttled
      Namespace: AWS/DynamoDB
      MetricName: ReadThrottleEvents
      Dimensions:
        - Name: TableName
          Value: !Ref VibeJudgeTable
      Statistic: Sum
      Period: 300
      EvaluationPeriods: 2
      Threshold: 5
      ComparisonOperator: GreaterThanThreshold
      TreatMissingData: notBreaching

  # Alarm: DynamoDB write throttling
  DynamoDBWriteThrottleAlarm:
    Type: AWS::CloudWatch::Alarm
    Properties:
      AlarmName: !Sub "vibejudge-dynamo-write-throttle-${Environment}"
      AlarmDescription: DynamoDB write requests being throttled
      Namespace: AWS/DynamoDB
      MetricName: WriteThrottleEvents
      Dimensions:
        - Name: TableName
          Value: !Ref VibeJudgeTable
      Statistic: Sum
      Period: 300
      EvaluationPeriods: 2
      Threshold: 5
      ComparisonOperator: GreaterThanThreshold
      TreatMissingData: notBreaching

# ============================================================
# OUTPUTS
# ============================================================
Outputs:
  ApiUrl:
    Description: VibeJudge API endpoint URL
    Value: !Sub "https://${VibeJudgeApi}.execute-api.${AWS::Region}.amazonaws.com/${Environment}/"

  ApiDocsUrl:
    Description: Swagger UI documentation
    Value: !Sub "https://${VibeJudgeApi}.execute-api.${AWS::Region}.amazonaws.com/${Environment}/docs"

  ApiFunctionArn:
    Description: API Lambda function ARN
    Value: !GetAtt ApiFunction.Arn

  AnalyzerFunctionArn:
    Description: Analyzer Lambda function ARN
    Value: !GetAtt AnalyzerFunction.Arn

  TableName:
    Description: DynamoDB table name
    Value: !Ref VibeJudgeTable

  TableArn:
    Description: DynamoDB table ARN
    Value: !GetAtt VibeJudgeTable.Arn

  BucketName:
    Description: S3 bucket name
    Value: !Ref VibeJudgeBucket

  BucketArn:
    Description: S3 bucket ARN
    Value: !GetAtt VibeJudgeBucket.Arn
```

---

## samconfig.toml

```toml
# SAM deployment configuration
# Run: sam deploy --config-env dev

version = 0.1

[default.deploy.parameters]
stack_name = "vibejudge-dev"
resolve_s3 = true
s3_prefix = "vibejudge"
region = "us-east-1"
confirm_changeset = true
capabilities = "CAPABILITY_IAM"
parameter_overrides = "Environment=\"dev\" BedrockRegion=\"us-east-1\" LogLevel=\"DEBUG\""
disable_rollback = false
image_repositories = []

[staging.deploy.parameters]
stack_name = "vibejudge-staging"
resolve_s3 = true
s3_prefix = "vibejudge"
region = "us-east-1"
confirm_changeset = true
capabilities = "CAPABILITY_IAM"
parameter_overrides = "Environment=\"staging\" BedrockRegion=\"us-east-1\" LogLevel=\"INFO\""

[prod.deploy.parameters]
stack_name = "vibejudge-prod"
resolve_s3 = true
s3_prefix = "vibejudge"
region = "us-east-1"
confirm_changeset = true
capabilities = "CAPABILITY_IAM"
parameter_overrides = "Environment=\"prod\" BedrockRegion=\"us-east-1\" LogLevel=\"WARNING\""
```

---

## Deployment Commands

```bash
# First time setup
sam build
sam deploy --guided

# Subsequent deploys
sam build && sam deploy

# Local testing
sam local start-api --port 8000
sam local invoke ApiFunction --event events/test-event.json
sam local invoke AnalyzerFunction --event events/analyze-event.json

# View logs
sam logs -n ApiFunction --stack-name vibejudge-dev --tail
sam logs -n AnalyzerFunction --stack-name vibejudge-dev --tail

# Teardown (careful!)
sam delete --stack-name vibejudge-dev
```

---

## Architecture Diagram (Text)

```
                        ┌──────────────┐
                        │   Internet   │
                        └──────┬───────┘
                               │
                    ┌──────────▼──────────┐
                    │  API Gateway (HTTP)  │
                    │  /{proxy+} → Lambda  │
                    └──────────┬──────────┘
                               │
              ┌────────────────▼────────────────┐
              │     API Lambda (FastAPI)         │
              │     1024MB | 30s timeout         │
              │     Handles all API routes       │
              └──┬─────────────┬──────────────┬─┘
                 │             │              │
    ┌────────────▼──┐  ┌──────▼──────┐  ┌───▼────────────┐
    │   DynamoDB    │  │  S3 Bucket  │  │ Analyzer Lambda│
    │  (single-tbl) │  │ (assets)    │  │ 2048MB | 15min │
    │  5 RCU/5 WCU  │  │ versioned   │  │ 2GB /tmp       │
    └───────────────┘  └─────────────┘  └───┬────────────┘
                                            │
                               ┌────────────▼────────────┐
                               │   Amazon Bedrock        │
                               │   ├─ Nova Micro         │
                               │   ├─ Nova Lite          │
                               │   └─ Claude Sonnet      │
                               └─────────────────────────┘
```

---

## Free Tier Cost Analysis

| Service | Free Tier | Our Usage | Monthly Cost |
|---------|-----------|-----------|-------------|
| Lambda (API) | 1M req + 400K GB-sec | ~5K req, ~5K GB-sec | $0.00 |
| Lambda (Analyzer) | (shared with above) | ~500 req, ~250K GB-sec | $0.00 |
| API Gateway HTTP | 1M requests (12mo) | ~5K requests | $0.00 |
| DynamoDB | 25 RCU + 25 WCU + 25GB | 15 RCU + 15 WCU + <1GB | $0.00 |
| S3 | 5GB + 20K GET + 2K PUT | <100MB, <1K ops | $0.00 |
| CloudWatch | 5GB logs + 10 alarms | <1GB logs, 5 alarms | $0.00 |
| **Bedrock** | **$0 free tier** | **~$1-15/hackathon** | **$1-15** |
| **Total** | | | **$1-15/mo** |

Bedrock is the only real cost. Everything else is free tier.

---

*End of SAM Template v1.0*  
*Next deliverable: #7 — Pydantic Models*
