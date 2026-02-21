# VibeJudge AI — Project Structure

## Directory Layout
```
vibejudge/
├── .kiro/
│   ├── steering/          # This folder - project context
│   ├── specs/             # Generated specs
│   └── hooks/             # Agent hooks for automation
│
├── src/
│   ├── api/               # FastAPI application (Lambda 1: API Handler)
│   │   ├── main.py        # FastAPI app + Mangum handler
│   │   ├── dependencies.py # DI: Bedrock client, DynamoDB table, auth
│   │   └── routes/
│   │       ├── health.py           # GET /health
│   │       ├── organizers.py       # Organizer CRUD + auth
│   │       ├── hackathons.py       # Hackathon CRUD
│   │       ├── submissions.py      # Submission management
│   │       ├── analysis.py         # Trigger analysis, job status
│   │       └── costs.py            # Cost analytics
│   │
│   ├── agents/            # AI Agents (Bedrock Converse API)
│   │   ├── base.py        # BaseAgent class with shared logic
│   │   ├── bug_hunter.py  # Code quality + security agent
│   │   ├── performance.py # Architecture + scalability agent
│   │   ├── innovation.py  # Creativity + novelty agent
│   │   └── ai_detection.py # Authenticity + AI usage agent
│   │
│   ├── analysis/          # Analysis Engine (Lambda 2: Batch Processor)
│   │   ├── lambda_handler.py   # Analyzer Lambda entry point
│   │   ├── orchestrator.py     # Multi-agent coordination
│   │   ├── git_analyzer.py     # Clone + extract repo data
│   │   ├── actions_analyzer.py # GitHub Actions REST API
│   │   ├── context_builder.py  # Build agent input context
│   │   └── cost_tracker.py     # Token + cost tracking
│   │
│   ├── models/            # Pydantic v2 Schemas (Shared)
│   │   ├── common.py      # Enums, base models, mixins
│   │   ├── organizer.py   # Organizer request/response
│   │   ├── hackathon.py   # Hackathon config, rubric
│   │   ├── submission.py  # Submission, repo metadata
│   │   ├── scores.py      # Agent response schemas
│   │   ├── costs.py       # Cost tracking models
│   │   ├── analysis.py    # Internal models (RepoData, etc.)
│   │   ├── leaderboard.py # Leaderboard response
│   │   └── errors.py      # Error responses
│   │
│   ├── prompts/           # Agent System Prompts (Versioned)
│   │   ├── bug_hunter_v1.py     # BugHunter system prompt
│   │   ├── performance_v1.py    # Performance system prompt
│   │   ├── innovation_v1.py     # Innovation system prompt
│   │   ├── ai_detection_v1.py   # AI Detection system prompt
│   │   ├── retry_prompts.py     # JSON retry prompts
│   │   └── context_template.py  # Repo context template
│   │
│   ├── services/          # Business Logic Layer
│   │   ├── organizer_service.py  # Organizer CRUD + API key
│   │   ├── hackathon_service.py  # Hackathon CRUD + validation
│   │   ├── submission_service.py # Submission management
│   │   ├── analysis_service.py   # Analysis job orchestration
│   │   ├── scoring_service.py    # Score aggregation + leaderboard
│   │   └── cost_service.py       # Cost estimation + tracking
│   │
│   ├── utils/             # Shared Utilities (Leaf Module)
│   │   ├── bedrock.py     # Bedrock client wrapper
│   │   ├── dynamo.py      # DynamoDB helper class
│   │   ├── github_client.py # httpx GitHub API client
│   │   ├── id_gen.py      # ULID generation
│   │   ├── config.py      # Settings from env vars
│   │   └── logging.py     # Structured logging setup
│   │
│   └── constants.py       # Model rates, limits, config
│
├── tests/
│   ├── conftest.py        # Shared fixtures (mocks, sample data)
│   ├── unit/              # Unit tests (no AWS)
│   │   ├── test_models.py
│   │   ├── test_git_analyzer.py
│   │   ├── test_scoring.py
│   │   └── test_agents.py
│   ├── integration/       # Integration tests (mocked AWS)
│   │   ├── test_api.py    # FastAPI TestClient
│   │   └── test_orchestrator.py
│   └── fixtures/
│       ├── sample_repos/  # Small git repos for testing
│       └── sample_responses/ # Mock Bedrock responses
│
├── template.yaml          # SAM Infrastructure (IaC)
├── samconfig.toml         # SAM deployment config
├── requirements.txt       # Python dependencies
├── requirements-dev.txt   # Dev/test dependencies
├── pyproject.toml         # Project metadata
├── Makefile               # Common commands
├── .gitignore
├── .env.example
└── README.md
```

## Module Dependency Rules (NO CIRCULAR IMPORTS!)

```
api/routes → services → agents → prompts
                     → utils
                     → models
         → models

analysis → agents → services → utils
                             → models
         → utils
         → models

agents → prompts
       → utils/bedrock
       → models/scores

services → utils/dynamo
         → utils/bedrock
         → models
         → agents (for analysis_service only)

utils → (NO dependencies - leaf module)
models → (NO dependencies - pure data)
prompts → (NO dependencies - pure strings)
```

**CRITICAL:** Never import in reverse! Services NEVER import from API routes.

## File Naming Conventions

### Python Modules
- **Models:** Singular nouns (organizer.py, hackathon.py)
- **Services:** `<entity>_service.py` (organizer_service.py)
- **Agents:** `<agent_name>.py` (bug_hunter.py)
- **Utils:** `<purpose>.py` (bedrock.py, dynamo.py)
- **Tests:** `test_<module>.py` (test_organizer_service.py)

### Classes
- PascalCase: `HackathonCreate`, `BedrockClient`, `BugHunterAgent`

### Functions
- snake_case: `get_hackathon()`, `analyze_repo()`, `validate_evidence()`

## Import Style (REQUIRED)

```python
# ✅ ALWAYS use absolute imports
from src.models.hackathon import HackathonCreate
from src.utils.bedrock import BedrockClient
from src.agents.bug_hunter import BugHunterAgent

# ❌ NEVER use relative imports
from ..models import HackathonCreate  # WRONG
from .bug_hunter import BugHunterAgent  # WRONG
```

## Entity Responsibilities

| Module | Responsibility | What It Does | What It Doesn't Do |
|--------|---------------|--------------|-------------------|
| api/routes/ | HTTP layer only | Parse requests, call services, return responses | Business logic, data access |
| services/ | Business logic | Validate, orchestrate, transform data | HTTP handling, direct DB access |
| agents/ | AI agent wrappers | System prompt + Converse call + parse JSON | Business rules, data storage |
| analysis/ | Data extraction | Clone repos, extract git data, build context | Scoring, storage |
| models/ | Data schemas | Pydantic validation, serialization | Logic, transformations |
| prompts/ | Prompt text | Static strings, templates | Execution, state |
| utils/ | Infrastructure | AWS clients, logging, IDs | Business logic |

## Key Constraints

1. Single Lambda for API (all routes → one FastAPI app)
2. Single Lambda for Analysis (batch processor)
3. All models shared (src/models/ used by both Lambdas)
4. No frontend (API-first MVP)
5. No circular imports (enforce with mypy)
6. No relative imports (absolute only)
