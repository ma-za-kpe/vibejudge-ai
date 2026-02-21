# VibeJudge AI — Technology Stack & Constraints

## Core Technologies

### Programming Language
- **Python 3.12** (Lambda runtime: python3.12)
- Type hints REQUIRED for all functions
- Use latest Python features (pattern matching, walrus operator OK)

### API Framework
- **FastAPI 0.109+** (ASGI framework)
- **Mangum 0.17+** (Lambda adapter for FastAPI)
- Auto-generated OpenAPI docs at /docs
- Pydantic v2 for request/response validation

### AI Platform
- **Amazon Bedrock Converse API** (NOT Bedrock Agents!)
- **Why Converse API:** Token transparency (usage.inputTokens, usage.outputTokens)
- **Models & Costs:**
```python
MODEL_RATES = {
    "amazon.nova-micro-v1:0":  {"input": 0.000000035, "output": 0.000000140},
    "amazon.nova-lite-v1:0":   {"input": 0.000000060, "output": 0.000000240},
    "anthropic.claude-sonnet-4-20250514": {"input": 0.000003000, "output": 0.000015000},
}

# Agent Model Assignments (Cost-Optimized)
BugHunter: Nova Lite ($0.002/repo)
Performance: Nova Lite ($0.002/repo)
Innovation: Claude Sonnet ($0.018/repo)  # Worth the premium for deep reasoning
AI Detection: Nova Micro ($0.001/repo)   # Pattern detection only
```

## AWS Services (Free Tier Constraints) ⚠️ CRITICAL

| Service | Free Tier | Configuration REQUIRED | Why |
|---------|-----------|------------------------|-----|
| Lambda | 1M requests/mo, 400K GB-seconds | Memory: 1024MB (API), 2048MB (Analyzer)<br>Timeout: 30s (API), 900s (Analyzer) | Balance cost/speed |
| DynamoDB | 25 RCU/WCU | BillingMode: PROVISIONED<br>TableClass: STANDARD<br>RCU: 5, WCU: 5 | ⚠️ On-demand NOT free<br>⚠️ Standard-IA NOT free |
| API Gateway | 1M calls/mo (12mo) | Type: HttpApi (NOT RestApi) | 71% cheaper |
| S3 | 5GB (12mo) | Lifecycle: 30d deletion | Cleanup old data |
| CloudWatch | 5GB logs, 10 alarms | Retention: 14 days | Avoid log costs |

## Database

- **Single-table DynamoDB design**
- **Key Schema:**
  - PK (Partition Key): String  # ORG#<id>, HACK#<id>, SUB#<id>
  - SK (Sort Key): String       # PROFILE, META, SCORE#<agent>, etc.
  - GSI1PK, GSI1SK: Cross-entity lookups
  - GSI2PK, GSI2SK: Status + time queries
- **Access Patterns:** 16 patterns defined in docs/03-dynamodb-data-model.md
- **Provisioned Capacity:** 5 RCU / 5 WCU (within 25 free tier)

## Git Analysis

- **GitPython** (Python wrapper for git CLI)
- **httpx** (NOT PyGithub - need GitHub Actions API coverage)
- **Storage:** Lambda /tmp (ephemeral, 2GB configured)
- **Cleanup:** Always shutil.rmtree() after analysis

## Infrastructure

- **AWS SAM** (NOT CDK - faster for serverless)
- **Why SAM:** Purpose-built for Lambda + API Gateway, local testing with `sam local`

## Architecture Principles (NON-NEGOTIABLE!)

### 1. Cost Transparency 💰

```python
# EVERY Bedrock call must track tokens and cost
response = bedrock_client.converse(...)
cost_record = CostRecord(
    agent_name=agent_name,
    model_id=model_id,
    input_tokens=response["usage"]["inputTokens"],
    output_tokens=response["usage"]["outputTokens"],
    total_cost_usd=calculate_cost(...)
)
# Store in DynamoDB for dashboard
```

**Why:** This is a core value prop - organizers see exactly what they're paying per agent.

### 2. Evidence-Based Scoring (No Hallucinations!) 🎯

```python
# Agents MUST cite specific files and lines
evidence = {
    "finding": "SQL injection vulnerability",
    "file": "src/api/users.py",  # ✅ Must exist in repo
    "line": 42,                   # ✅ Must be valid line number
    "severity": "high"
}

# ALWAYS validate before storing
def validate_evidence(evidence, repo_data):
    if evidence["file"] not in repo_data.file_paths:
        evidence["verified"] = False
        evidence["error"] = "File not found in repository"
    if evidence["line"] and evidence["line"] > repo_data.file_line_counts[evidence["file"]]:
        evidence["verified"] = False
        evidence["error"] = "Line number exceeds file length"
```

**Why:** Hallucinated evidence destroys trust. Verification is mandatory.

### 3. Free Tier Compliance ✅

```yaml
# DynamoDB: ALWAYS use provisioned mode for free tier
VibeJudgeTable:
  BillingMode: PROVISIONED  # ✅ NOT on-demand
  TableClass: STANDARD      # ✅ NOT Standard-IA (not free!)
  ProvisionedThroughput:
    ReadCapacityUnits: 5    # ✅ Within 25 RCU free tier
    WriteCapacityUnits: 5   # ✅ Within 25 WCU free tier

# Lambda: Optimize memory for cost/speed balance
ApiFunction:
  MemorySize: 1024          # ✅ Not 128 (too slow), not 3008 (too expensive)

AnalyzerFunction:
  MemorySize: 2048          # ✅ Needs more for git clones
  EphemeralStorage: 2048    # ✅ 2GB /tmp for repos
```

**Why:** We MUST stay in free tier to prove cost-efficiency.

### 4. No Over-Engineering 🚫

- ❌ Don't use Bedrock Agents (Converse API simpler + token tracking)
- ❌ Don't use PyGithub (httpx lighter + Actions API support)
- ❌ Don't use LangChain/CrewAI (custom orchestrator 200 lines vs 50+ dependencies)
- ❌ Don't build frontend (API-first MVP, Swagger UI is enough)
- ❌ Don't implement real-time webhooks (post-submission batch is 10-30x cheaper)

## Coding Standards (ENFORCE!)

### Type Hints (Required)

```python
# ✅ GOOD - All parameters and return types annotated
def analyze_repo(
    repo_url: str,
    config: HackathonConfig
) -> tuple[RepoData, float]:
    ...

# ❌ BAD - No type hints
def analyze_repo(repo_url, config):
    ...
```

### Pydantic Models (Required)

```python
# ✅ ALL data structures use Pydantic v2
from pydantic import BaseModel, Field, ConfigDict

class HackathonCreate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    name: str = Field(..., min_length=1, max_length=200)
    rubric: RubricConfig

# ❌ DON'T use plain dicts or dataclasses for API/DB models
```

### Structured Logging (Required)

```python
# ✅ Use structlog for JSON logs (CloudWatch Log Insights)
import structlog
logger = structlog.get_logger()

logger.info(
    "analysis_started",
    sub_id=sub_id,
    repo_url=repo_url,
    estimated_cost=0.023
)

# ❌ DON'T use print() or basic logging
print(f"Starting analysis for {sub_id}")  # WRONG
```

### Error Handling (Required)

```python
# ✅ Bedrock calls MUST have error handling
try:
    response = bedrock.converse(...)
except bedrock.exceptions.ThrottlingException:
    logger.warning("bedrock_throttled", agent=agent_name)
    time.sleep(2)  # Exponential backoff
    retry()
except Exception as e:
    logger.error("bedrock_failed", agent=agent_name, error=str(e))
    # Mark submission as failed, continue with others
    submission.status = SubmissionStatus.FAILED
    submission.error_message = str(e)

# ❌ NEVER let Bedrock errors crash the entire batch
response = bedrock.converse(...)  # Unhandled exception kills pipeline
```

### No Circular Imports (Enforce with mypy)

```python
# ✅ Services can import agents
from src.agents.bug_hunter import BugHunterAgent  # OK

# ❌ Agents CANNOT import services
from src.services.hackathon_service import HackathonService  # WRONG
```

## Dependencies (requirements.txt)

### Production
```
# Core
fastapi>=0.109.0,<1.0.0
mangum>=0.17.0,<1.0.0
pydantic>=2.5.0,<3.0.0
pydantic-settings>=2.1.0,<3.0.0

# AWS (boto3 in Lambda runtime, pin for local dev)
boto3>=1.34.0,<2.0.0

# Git
gitpython>=3.1.40,<4.0.0

# HTTP
httpx>=0.25.0,<1.0.0

# Utilities
python-ulid>=2.2.0,<3.0.0
structlog>=23.2.0,<25.0.0
tenacity>=8.2.0,<10.0.0  # Retry logic
```

### Development Only
```
# Testing
pytest>=7.4.0,<9.0.0
pytest-asyncio>=0.23.0,<1.0.0
pytest-cov>=4.1.0,<6.0.0
moto[dynamodb,s3]>=5.0.0,<6.0.0

# Code Quality
ruff>=0.1.0
mypy>=1.7.0
```

## What Kiro Should NEVER Generate

When generating code, Kiro should AVOID:

### ❌ Don't Generate
1. Bedrock Agents code (we use Converse API directly)
2. Frontend components (API-first MVP)
3. Real-time webhook handlers (post-submission batch only)
4. LangChain/CrewAI integrations (custom orchestrator)
5. PyGithub usage (use httpx)
6. On-demand DynamoDB (provisioned only)
7. Relative imports (absolute only)
8. print() statements (use structlog)

### ✅ Always Generate
1. Type hints on all functions
2. Pydantic models for all data structures
3. Error handling around Bedrock calls
4. Structured logging with context
5. Evidence validation for agent responses
6. Cost tracking for every Bedrock call
7. Free tier configurations for AWS resources

## Kiro Credit Optimization Rules

### Use Kiro Credits For (High Value)
- ✅ Infrastructure generation (SAM templates, complex config)
- ✅ Pydantic model creation (lots of boilerplate)
- ✅ Agent prompt engineering (needs AI understanding)
- ✅ Complex business logic (orchestrator, analyzers)
- ✅ Property-based test generation (hard to write manually)

### DON'T Use Kiro Credits For (Low Value)
- ❌ Simple file creation (steering files, .gitignore)
- ❌ Basic edits (variable renames, comment changes)
- ❌ Copy-paste from docs (do manually)
- ❌ Trivial getters/setters
- ❌ Configuration files (.env.example)

### Use Agent Hooks Instead of Manual Chat
- ✅ Test generation on file save (one-time hook setup)
- ✅ Documentation updates (automatic)
- ✅ Linting/formatting (use pre-commit, not Kiro)
