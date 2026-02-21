# VibeJudge AI — Project Structure

> **Version:** 1.0  
> **Date:** February 2026  
> **Author:** Maku Mazakpe / Vibe Coders  
> **Status:** APPROVED  
> **Depends On:** ADR-007 (Monorepo), All previous deliverables

---

## Complete File Tree

```
vibejudge/
│
├── template.yaml                    # SAM infrastructure (Deliverable #6)
├── samconfig.toml                   # SAM deployment config
├── requirements.txt                 # Shared Python dependencies
├── requirements-dev.txt             # Dev/test dependencies
├── pyproject.toml                   # Project metadata & tool config
├── README.md                        # Project documentation
├── Makefile                         # Common commands (build, test, deploy)
├── .gitignore
├── .env.example                     # Environment variable template
│
├── src/                             # All application code
│   │
│   ├── api/                         # FastAPI application (Lambda 1: API)
│   │   ├── __init__.py
│   │   ├── main.py                  # FastAPI app + Mangum handler
│   │   ├── dependencies.py          # DI providers (Bedrock, DynamoDB, auth)
│   │   └── routes/
│   │       ├── __init__.py
│   │       ├── health.py            # GET /health
│   │       ├── organizers.py        # /api/v1/organizers/*
│   │       ├── hackathons.py        # /api/v1/hackathons/*
│   │       ├── submissions.py       # /api/v1/submissions/*
│   │       ├── analysis.py          # /api/v1/hackathons/{id}/analyze/*
│   │       └── costs.py             # Cost endpoints
│   │
│   ├── agents/                      # AI judging agents
│   │   ├── __init__.py
│   │   ├── base.py                  # BaseAgent class (Converse API wrapper)
│   │   ├── bug_hunter.py            # BugHunter agent
│   │   ├── performance.py           # PerformanceAnalyzer agent
│   │   ├── innovation.py            # InnovationScorer agent
│   │   └── ai_detection.py          # AIDetectionAnalyst agent
│   │
│   ├── analysis/                    # Core analysis engine
│   │   ├── __init__.py
│   │   ├── lambda_handler.py        # Analyzer Lambda entry point
│   │   ├── orchestrator.py          # Multi-agent orchestration
│   │   ├── git_analyzer.py          # Clone + extract git data
│   │   ├── actions_analyzer.py      # GitHub Actions REST API
│   │   ├── context_builder.py       # Assemble repo context for agents
│   │   └── cost_tracker.py          # Token/cost tracking per agent
│   │
│   ├── models/                      # Pydantic models (Deliverable #7)
│   │   ├── __init__.py
│   │   ├── common.py                # Enums, base models
│   │   ├── organizer.py
│   │   ├── hackathon.py
│   │   ├── submission.py
│   │   ├── scores.py                # Agent output schemas
│   │   ├── costs.py
│   │   ├── analysis.py              # RepoData, internal models
│   │   ├── leaderboard.py
│   │   └── errors.py
│   │
│   ├── prompts/                     # Agent system prompts (versioned)
│   │   ├── __init__.py
│   │   ├── bug_hunter_v1.py         # BugHunter system prompt
│   │   ├── performance_v1.py        # PerformanceAnalyzer system prompt
│   │   ├── innovation_v1.py         # InnovationScorer system prompt
│   │   ├── ai_detection_v1.py       # AIDetectionAnalyst system prompt
│   │   ├── ai_policy_modifiers.py   # AI policy mode prompt modifiers
│   │   ├── retry_prompts.py         # JSON retry, error recovery prompts
│   │   └── context_template.py      # REPO_CONTEXT_TEMPLATE
│   │
│   ├── services/                    # Business logic layer
│   │   ├── __init__.py
│   │   ├── organizer_service.py     # Organizer CRUD + auth
│   │   ├── hackathon_service.py     # Hackathon CRUD + validation
│   │   ├── submission_service.py    # Submission management
│   │   ├── analysis_service.py      # Analysis job management
│   │   ├── scoring_service.py       # Score aggregation + leaderboard
│   │   └── cost_service.py          # Cost estimation + tracking
│   │
│   ├── utils/                       # Shared utilities
│   │   ├── __init__.py
│   │   ├── bedrock.py               # Bedrock client wrapper with token tracking
│   │   ├── dynamo.py                # DynamoDB helper (from Deliverable #3)
│   │   ├── github_client.py         # httpx-based GitHub API client
│   │   ├── id_gen.py                # ULID generation
│   │   ├── config.py                # Settings from env vars (pydantic-settings)
│   │   └── logging.py               # Structured logging setup (structlog)
│   │
│   └── constants.py                 # Model rates, limits, defaults
│
├── tests/                           # All tests
│   ├── __init__.py
│   ├── conftest.py                  # Shared fixtures (mock Bedrock, DynamoDB, repos)
│   │
│   ├── unit/                        # Unit tests (no AWS calls)
│   │   ├── __init__.py
│   │   ├── test_models.py           # Pydantic model validation
│   │   ├── test_git_analyzer.py     # Git extraction logic
│   │   ├── test_context_builder.py  # Context assembly
│   │   ├── test_scoring.py          # Score aggregation
│   │   ├── test_cost_tracker.py     # Cost calculations
│   │   └── test_agents.py           # Agent response parsing
│   │
│   ├── integration/                 # Integration tests (mocked AWS)
│   │   ├── __init__.py
│   │   ├── test_api.py              # FastAPI endpoint tests (TestClient)
│   │   ├── test_orchestrator.py     # Full analysis pipeline
│   │   └── test_dynamo.py           # DynamoDB operations (moto)
│   │
│   └── fixtures/                    # Test data
│       ├── sample_repos/            # Small git repos for testing
│       │   └── basic_python/        # Minimal Python project
│       ├── sample_responses/        # Mock Bedrock responses per agent
│       │   ├── bug_hunter_response.json
│       │   ├── performance_response.json
│       │   ├── innovation_response.json
│       │   └── ai_detection_response.json
│       └── sample_hackathon.json    # Demo hackathon config
│
├── events/                          # SAM local invoke test events
│   ├── api-health.json              # GET /health event
│   ├── api-create-hackathon.json    # POST hackathon event
│   └── analyzer-trigger.json        # Analyzer invocation event
│
└── docs/                            # Documentation & deliverables
    ├── 01-strategy-document.docx
    ├── 02-architecture-decision-records.md
    ├── 03-dynamodb-data-model.md
    ├── 04-agent-prompt-library.md
    ├── 05-api-specification.md
    ├── 06-sam-template.md
    ├── 07-pydantic-models.md
    ├── 08-git-analysis-spec.md
    ├── 09-project-structure.md
    └── 10-test-scenarios.md
```

---

## Module Responsibility Map

| Module | Responsibility | Dependencies |
|--------|---------------|-------------|
| `src/api/` | HTTP layer only. Route → service call → response. No business logic. | services, models |
| `src/services/` | Business logic. Validation, orchestration, data transformation. | models, utils, agents |
| `src/agents/` | AI agent wrappers. System prompt + Converse API call + response parsing. | models, prompts, utils/bedrock |
| `src/analysis/` | Data extraction. Git clone, file parsing, context assembly. | models, utils/github_client |
| `src/models/` | Data definitions. Pydantic schemas. Zero logic. | (none) |
| `src/prompts/` | Prompt text. Pure strings/constants. Zero logic. | (none) |
| `src/utils/` | AWS clients, ID generation, config, logging. Infrastructure glue. | (none — leaf module) |

---

## Dependency Flow (no circular imports)

```
api/routes → services → agents → prompts
                     → utils
                     → models
         → models
analysis → agents
         → services
         → utils
         → models
```

---

## Key Files Detail

### `src/api/main.py`
```python
# FastAPI app entry point + Mangum Lambda handler
# Registers all routers, exception handlers, middleware
# handler = Mangum(app, lifespan="off")
```

### `src/analysis/lambda_handler.py`
```python
# Analyzer Lambda entry point
# Invoked asynchronously by API Lambda
# def handler(event, context): processes batch analysis
```

### `src/agents/base.py`
```python
# BaseAgent class with:
#   - converse() wrapper that captures token usage
#   - JSON response parsing with retry
#   - Evidence validation (anti-hallucination)
#   - Configurable model, temperature, max_tokens
```

### `src/utils/config.py`
```python
# pydantic-settings based configuration
# Reads from env vars (set in SAM template)
# class Settings(BaseSettings):
#     table_name: str
#     bucket_name: str
#     bedrock_region: str
#     log_level: str
```

---

## requirements.txt

```
# Core
fastapi>=0.109.0,<1.0.0
mangum>=0.17.0,<1.0.0
pydantic>=2.5.0,<3.0.0
pydantic-settings>=2.1.0,<3.0.0

# AWS (boto3 included in Lambda runtime, but pin for local dev)
boto3>=1.34.0,<2.0.0

# Git
gitpython>=3.1.40,<4.0.0

# HTTP
httpx>=0.25.0,<1.0.0

# Utilities
python-ulid>=2.2.0,<3.0.0
structlog>=23.2.0,<25.0.0
tenacity>=8.2.0,<10.0.0
```

## requirements-dev.txt

```
-r requirements.txt

# Testing
pytest>=7.4.0,<9.0.0
pytest-asyncio>=0.23.0,<1.0.0
pytest-cov>=4.1.0,<6.0.0
moto[dynamodb,s3]>=5.0.0,<6.0.0
httpx  # TestClient uses httpx

# Local dev
uvicorn>=0.25.0,<1.0.0
python-dotenv>=1.0.0,<2.0.0

# Code quality
ruff>=0.1.0
mypy>=1.7.0
```

---

## Makefile

```makefile
.PHONY: install test lint build deploy local

install:
	pip install -r requirements-dev.txt

test:
	pytest tests/ -v --cov=src --cov-report=term-missing

test-unit:
	pytest tests/unit/ -v

test-integration:
	pytest tests/integration/ -v

lint:
	ruff check src/ tests/
	mypy src/ --ignore-missing-imports

format:
	ruff format src/ tests/

build:
	sam build

deploy-dev:
	sam build && sam deploy --config-env default

deploy-prod:
	sam build && sam deploy --config-env prod

local:
	uvicorn src.api.main:app --reload --port 8000

local-sam:
	sam local start-api --port 8000

logs-api:
	sam logs -n ApiFunction --stack-name vibejudge-dev --tail

logs-analyzer:
	sam logs -n AnalyzerFunction --stack-name vibejudge-dev --tail

clean:
	rm -rf .aws-sam/ __pycache__ .pytest_cache .mypy_cache
```

---

*End of Project Structure v1.0*  
*Next deliverable: #10 — Test Scenarios*
