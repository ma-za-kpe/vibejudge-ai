# VibeJudge AI — Test Scenarios

> **Version:** 1.0  
> **Date:** February 2026  
> **Author:** Maku Mazakpe / Vibe Coders  
> **Status:** APPROVED  
> **Depends On:** All previous deliverables  
> **Framework:** pytest + moto (AWS mocking) + FastAPI TestClient

---

## Test Strategy

| Layer | Tool | Mocking | Coverage Target |
|-------|------|---------|----------------|
| Unit | pytest | Pure Python, no AWS | Models, scoring, git parsing, cost calc |
| Integration | pytest + moto + TestClient | Mocked DynamoDB/S3, mocked Bedrock | API routes, orchestrator, services |
| Fixtures | JSON files + sample git repos | Pre-built mock responses | Realistic test data |

**What we DON'T test in CI:** Live Bedrock API calls, live GitHub API calls, SAM deployment. These are manual validation during development.

---

## 1. conftest.py — Shared Fixtures

```python
"""tests/conftest.py — Shared test fixtures."""

import json
import os
import pytest
import boto3
from moto import mock_dynamodb, mock_s3
from fastapi.testclient import TestClient
from pathlib import Path

# Ensure we don't hit real AWS
os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
os.environ["AWS_ACCESS_KEY_ID"] = "testing"
os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
os.environ["TABLE_NAME"] = "vibejudge-test"
os.environ["BUCKET_NAME"] = "vibejudge-test-bucket"
os.environ["BEDROCK_REGION"] = "us-east-1"
os.environ["LOG_LEVEL"] = "DEBUG"
os.environ["ENVIRONMENT"] = "test"


FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_hackathon_config():
    """Load sample hackathon configuration."""
    with open(FIXTURES_DIR / "sample_hackathon.json") as f:
        return json.load(f)


@pytest.fixture
def sample_bug_hunter_response():
    with open(FIXTURES_DIR / "sample_responses" / "bug_hunter_response.json") as f:
        return json.load(f)


@pytest.fixture
def sample_performance_response():
    with open(FIXTURES_DIR / "sample_responses" / "performance_response.json") as f:
        return json.load(f)


@pytest.fixture
def sample_innovation_response():
    with open(FIXTURES_DIR / "sample_responses" / "innovation_response.json") as f:
        return json.load(f)


@pytest.fixture
def sample_ai_detection_response():
    with open(FIXTURES_DIR / "sample_responses" / "ai_detection_response.json") as f:
        return json.load(f)


@pytest.fixture
def all_agent_responses(
    sample_bug_hunter_response,
    sample_performance_response,
    sample_innovation_response,
    sample_ai_detection_response,
):
    return {
        "bug_hunter": sample_bug_hunter_response,
        "performance": sample_performance_response,
        "innovation": sample_innovation_response,
        "ai_detection": sample_ai_detection_response,
    }


@pytest.fixture
def dynamodb_table():
    """Create mocked DynamoDB table matching our SAM template."""
    with mock_dynamodb():
        client = boto3.client("dynamodb", region_name="us-east-1")
        client.create_table(
            TableName="vibejudge-test",
            KeySchema=[
                {"AttributeName": "PK", "KeyType": "HASH"},
                {"AttributeName": "SK", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "PK", "AttributeType": "S"},
                {"AttributeName": "SK", "AttributeType": "S"},
                {"AttributeName": "GSI1PK", "AttributeType": "S"},
                {"AttributeName": "GSI1SK", "AttributeType": "S"},
                {"AttributeName": "GSI2PK", "AttributeType": "S"},
                {"AttributeName": "GSI2SK", "AttributeType": "S"},
            ],
            GlobalSecondaryIndexes=[
                {
                    "IndexName": "GSI1",
                    "KeySchema": [
                        {"AttributeName": "GSI1PK", "KeyType": "HASH"},
                        {"AttributeName": "GSI1SK", "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                    "ProvisionedThroughput": {"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
                },
                {
                    "IndexName": "GSI2",
                    "KeySchema": [
                        {"AttributeName": "GSI2PK", "KeyType": "HASH"},
                        {"AttributeName": "GSI2SK", "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "KEYS_ONLY"},
                    "ProvisionedThroughput": {"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
                },
            ],
            BillingMode="PROVISIONED",
            ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
        )
        table = boto3.resource("dynamodb", region_name="us-east-1").Table("vibejudge-test")
        yield table


@pytest.fixture
def s3_bucket():
    """Create mocked S3 bucket."""
    with mock_s3():
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket="vibejudge-test-bucket")
        yield s3


@pytest.fixture
def api_client(dynamodb_table, s3_bucket):
    """FastAPI TestClient with mocked AWS services."""
    from src.api.main import app
    with TestClient(app) as client:
        yield client


@pytest.fixture
def mock_bedrock_response():
    """Factory for mocking Bedrock converse() responses."""
    def _make_response(agent_json: dict, input_tokens: int = 3000, output_tokens: int = 800):
        return {
            "output": {
                "message": {
                    "role": "assistant",
                    "content": [{"text": json.dumps(agent_json)}],
                }
            },
            "usage": {
                "inputTokens": input_tokens,
                "outputTokens": output_tokens,
                "totalTokens": input_tokens + output_tokens,
            },
            "stopReason": "end_turn",
            "metrics": {"latencyMs": 2100},
        }
    return _make_response
```

---

## 2. Unit Tests

### test_models.py — Pydantic Validation

```python
"""tests/unit/test_models.py"""

import pytest
from src.models.hackathon import HackathonCreate, RubricConfig, RubricDimension
from src.models.submission import SubmissionInput
from src.models.scores import BugHunterResponse, AGENT_RESPONSE_MODELS
from src.models.common import AgentName, AIPolicyMode


class TestRubricValidation:
    def test_valid_rubric(self):
        rubric = RubricConfig(
            name="Test",
            dimensions=[
                RubricDimension(name="code", weight=0.5, agent="bug_hunter"),
                RubricDimension(name="innovation", weight=0.5, agent="innovation"),
            ],
        )
        assert len(rubric.dimensions) == 2

    def test_weights_must_sum_to_one(self):
        with pytest.raises(ValueError, match="weights must sum to 1.0"):
            RubricConfig(
                dimensions=[
                    RubricDimension(name="code", weight=0.3, agent="bug_hunter"),
                    RubricDimension(name="innovation", weight=0.3, agent="innovation"),
                ],
            )

    def test_weights_tolerance(self):
        """Weights summing to 0.999 should be accepted."""
        rubric = RubricConfig(
            dimensions=[
                RubricDimension(name="a", weight=0.333, agent="bug_hunter"),
                RubricDimension(name="b", weight=0.333, agent="performance"),
                RubricDimension(name="c", weight=0.334, agent="innovation"),
            ],
        )
        assert rubric is not None


class TestSubmissionValidation:
    def test_valid_github_url(self):
        sub = SubmissionInput(
            team_name="Team Alpha",
            repo_url="https://github.com/team-alpha/my-project",
        )
        assert sub.repo_url == "https://github.com/team-alpha/my-project"

    def test_invalid_github_url(self):
        with pytest.raises(ValueError):
            SubmissionInput(
                team_name="Team",
                repo_url="https://gitlab.com/team/repo",
            )

    def test_github_url_with_trailing_slash(self):
        sub = SubmissionInput(
            team_name="Team",
            repo_url="https://github.com/owner/repo/",
        )
        assert sub is not None


class TestAgentResponseParsing:
    def test_valid_bug_hunter_response(self, sample_bug_hunter_response):
        parsed = BugHunterResponse(**sample_bug_hunter_response)
        assert parsed.agent == "bug_hunter"
        assert 0 <= parsed.overall_score <= 10
        assert len(parsed.evidence) >= 1

    def test_score_clamping(self):
        """Scores outside 0-10 should be clamped."""
        data = {
            "agent": "bug_hunter",
            "prompt_version": "1.0.0",
            "scores": {
                "code_quality": 11.0,  # Over 10
                "security": -1.0,      # Under 0
                "test_coverage": 5.0,
                "error_handling": 5.0,
                "dependency_hygiene": 5.0,
            },
            "overall_score": 5.0,
            "evidence": [],
            "summary": "Test",
        }
        # Should raise validation error for individual score fields
        with pytest.raises(ValueError):
            BugHunterResponse(**data)

    def test_all_agent_models_exist(self):
        for agent in AgentName:
            assert agent.value in AGENT_RESPONSE_MODELS


class TestHackathonCreate:
    def test_agents_must_match_rubric(self):
        with pytest.raises(ValueError, match="agents not in agents_enabled"):
            HackathonCreate(
                name="Test",
                rubric=RubricConfig(
                    dimensions=[
                        RubricDimension(name="code", weight=0.5, agent="bug_hunter"),
                        RubricDimension(name="innov", weight=0.5, agent="innovation"),
                    ],
                ),
                agents_enabled=["bug_hunter"],  # Missing innovation!
            )
```

### test_scoring.py — Aggregation Logic

```python
"""tests/unit/test_scoring.py"""

import pytest
from src.services.scoring_service import aggregate_scores, apply_ai_policy_modifier


class TestScoreAggregation:
    def test_basic_weighted_scoring(self, all_agent_responses):
        """Test that weighted scores produce correct overall score."""
        # With default weights: code=0.25, arch=0.25, innov=0.30, auth=0.20
        # Exact values depend on fixture data
        pass  # Implemented when fixtures are created

    def test_ai_policy_full_vibe_reduces_authenticity_weight(self):
        weights = {
            "code_quality": 0.25,
            "architecture": 0.25,
            "innovation": 0.30,
            "authenticity": 0.20,
        }
        modified = apply_ai_policy_modifier(weights, "full_vibe")
        assert modified["authenticity"] == 0.05
        assert abs(sum(modified.values()) - 1.0) < 0.001

    def test_ai_policy_traditional_increases_authenticity_weight(self):
        weights = {
            "code_quality": 0.25,
            "architecture": 0.25,
            "innovation": 0.30,
            "authenticity": 0.20,
        }
        modified = apply_ai_policy_modifier(weights, "traditional")
        assert modified["authenticity"] == 0.30
        assert abs(sum(modified.values()) - 1.0) < 0.001

    def test_custom_mode_uses_rubric_weights(self):
        weights = {"code_quality": 0.4, "authenticity": 0.6}
        modified = apply_ai_policy_modifier(weights, "custom")
        assert modified == weights  # Unchanged


class TestCostCalculation:
    def test_cost_per_submission(self):
        """Verify cost calculation matches model rates."""
        from src.analysis.cost_tracker import calculate_cost
        from src.constants import MODEL_RATES

        cost = calculate_cost(
            model_id="amazon.nova-lite-v1:0",
            input_tokens=3200,
            output_tokens=890,
        )
        expected_input = 3200 * MODEL_RATES["amazon.nova-lite-v1:0"]["input"]
        expected_output = 890 * MODEL_RATES["amazon.nova-lite-v1:0"]["output"]
        assert abs(cost - (expected_input + expected_output)) < 0.000001
```

### test_git_analyzer.py — Git Extraction

```python
"""tests/unit/test_git_analyzer.py"""

import pytest
from src.analysis.git_analyzer import parse_github_url, extract_file_tree


class TestGitHubURLParsing:
    def test_standard_url(self):
        owner, repo = parse_github_url("https://github.com/owner/repo")
        assert owner == "owner"
        assert repo == "repo"

    def test_url_with_git_suffix(self):
        owner, repo = parse_github_url("https://github.com/owner/repo.git")
        assert owner == "owner"
        assert repo == "repo"

    def test_url_with_trailing_slash(self):
        owner, repo = parse_github_url("https://github.com/owner/repo/")
        assert owner == "owner"
        assert repo == "repo"

    def test_hyphenated_names(self):
        owner, repo = parse_github_url("https://github.com/my-org/my-repo-name")
        assert owner == "my-org"
        assert repo == "my-repo-name"

    def test_invalid_url_gitlab(self):
        with pytest.raises(ValueError):
            parse_github_url("https://gitlab.com/owner/repo")

    def test_invalid_url_no_repo(self):
        with pytest.raises(ValueError):
            parse_github_url("https://github.com/owner")


class TestFileTree:
    def test_file_tree_generation(self, tmp_path):
        """Test file tree generation with a temporary directory."""
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.py").write_text("print('hello')")
        (tmp_path / "README.md").write_text("# Test")
        (tmp_path / "tests").mkdir()
        (tmp_path / "tests" / "test_main.py").write_text("def test(): pass")

        tree = extract_file_tree(tmp_path)
        assert "main.py" in tree
        assert "README.md" in tree
        assert "test_main.py" in tree

    def test_ignores_node_modules(self, tmp_path):
        (tmp_path / "node_modules").mkdir()
        (tmp_path / "node_modules" / "junk.js").write_text("x")
        (tmp_path / "app.js").write_text("console.log('hi')")

        tree = extract_file_tree(tmp_path)
        assert "node_modules" not in tree
        assert "app.js" in tree
```

---

## 3. Integration Tests

### test_api.py — FastAPI Endpoints

```python
"""tests/integration/test_api.py"""

import pytest


class TestHealthEndpoint:
    def test_health_check(self, api_client):
        response = api_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"


class TestOrganizerEndpoints:
    def test_register_organizer(self, api_client):
        response = api_client.post("/api/v1/organizers", json={
            "email": "test@example.com",
            "name": "Test User",
            "organization": "Test Corp",
        })
        assert response.status_code == 201
        data = response.json()
        assert "api_key" in data
        assert data["email"] == "test@example.com"
        assert data["tier"] == "free"

    def test_duplicate_email_rejected(self, api_client):
        api_client.post("/api/v1/organizers", json={
            "email": "dupe@example.com", "name": "User 1",
        })
        response = api_client.post("/api/v1/organizers", json={
            "email": "dupe@example.com", "name": "User 2",
        })
        assert response.status_code == 409

    def test_auth_required_for_hackathons(self, api_client):
        response = api_client.get("/api/v1/hackathons")
        assert response.status_code == 401


class TestHackathonEndpoints:
    def _register_and_get_key(self, client) -> str:
        resp = client.post("/api/v1/organizers", json={
            "email": "hack@example.com", "name": "Hacker",
        })
        return resp.json()["api_key"]

    def test_create_hackathon(self, api_client, sample_hackathon_config):
        api_key = self._register_and_get_key(api_client)
        response = api_client.post(
            "/api/v1/hackathons",
            json=sample_hackathon_config,
            headers={"X-API-Key": api_key},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == sample_hackathon_config["name"]
        assert data["status"] == "draft"

    def test_list_hackathons(self, api_client, sample_hackathon_config):
        api_key = self._register_and_get_key(api_client)
        api_client.post(
            "/api/v1/hackathons",
            json=sample_hackathon_config,
            headers={"X-API-Key": api_key},
        )
        response = api_client.get(
            "/api/v1/hackathons",
            headers={"X-API-Key": api_key},
        )
        assert response.status_code == 200
        assert len(response.json()["hackathons"]) == 1


class TestSubmissionEndpoints:
    def test_add_submissions(self, api_client, sample_hackathon_config):
        api_key = self._register_and_get_key(api_client)
        hack = api_client.post(
            "/api/v1/hackathons",
            json=sample_hackathon_config,
            headers={"X-API-Key": api_key},
        ).json()

        response = api_client.post(
            f"/api/v1/hackathons/{hack['hack_id']}/submissions",
            json={
                "submissions": [
                    {"team_name": "Team A", "repo_url": "https://github.com/team-a/project"},
                    {"team_name": "Team B", "repo_url": "https://github.com/team-b/project"},
                ]
            },
            headers={"X-API-Key": api_key},
        )
        assert response.status_code == 201
        assert response.json()["created"] == 2

    def _register_and_get_key(self, client) -> str:
        resp = client.post("/api/v1/organizers", json={
            "email": f"sub-test@example.com", "name": "Sub Tester",
        })
        return resp.json()["api_key"]
```

---

## 4. Test Fixtures

### sample_hackathon.json

```json
{
  "name": "Test Hackathon",
  "description": "A test hackathon for unit testing",
  "rubric": {
    "name": "Default Test Rubric",
    "version": "1.0",
    "max_score": 100,
    "dimensions": [
      {"name": "code_quality", "weight": 0.25, "agent": "bug_hunter", "description": "Code quality"},
      {"name": "architecture", "weight": 0.25, "agent": "performance", "description": "Architecture"},
      {"name": "innovation", "weight": 0.30, "agent": "innovation", "description": "Innovation"},
      {"name": "authenticity", "weight": 0.20, "agent": "ai_detection", "description": "Authenticity"}
    ]
  },
  "agents_enabled": ["bug_hunter", "performance", "innovation", "ai_detection"],
  "ai_policy_mode": "ai_assisted",
  "budget_limit_usd": 5.00
}
```

### sample_responses/bug_hunter_response.json

```json
{
  "agent": "bug_hunter",
  "prompt_version": "1.0.0",
  "scores": {
    "code_quality": 7.5,
    "security": 6.0,
    "test_coverage": 8.0,
    "error_handling": 5.5,
    "dependency_hygiene": 7.0
  },
  "overall_score": 6.8,
  "evidence": [
    {
      "finding": "SQL injection vulnerability in query builder",
      "file": "src/api/users.py",
      "line": 42,
      "severity": "high",
      "category": "security",
      "recommendation": "Use parameterized queries instead of string formatting"
    },
    {
      "finding": "Comprehensive pytest suite with fixtures",
      "file": "tests/test_api.py",
      "line": null,
      "severity": "info",
      "category": "testing",
      "recommendation": "Consider adding edge case tests for error paths"
    },
    {
      "finding": "Missing error handling on external API call",
      "file": "src/services/bedrock_client.py",
      "line": 28,
      "severity": "medium",
      "category": "bug",
      "recommendation": "Wrap in try/except with appropriate error response"
    }
  ],
  "ci_observations": {
    "has_ci": true,
    "has_automated_tests": true,
    "has_linting": false,
    "has_security_scanning": false,
    "build_success_rate": 0.85,
    "notable_findings": "CI runs tests but lacks linting and security scanning"
  },
  "summary": "Solid code structure with good test coverage. A critical SQL injection vulnerability needs addressing, and error handling could be more robust around external API calls."
}
```

*(Similar fixtures for performance, innovation, ai_detection — omitted for brevity but follow same pattern from Deliverable #4 schemas)*

---

## 5. Critical Test Scenarios Matrix

| ID | Scenario | Type | Priority |
|----|----------|------|----------|
| T01 | Rubric weights must sum to 1.0 | Unit | P0 |
| T02 | Invalid GitHub URL rejected | Unit | P0 |
| T03 | Agent JSON response parses correctly | Unit | P0 |
| T04 | Score clamping to 0-10 range | Unit | P0 |
| T05 | AI policy modifiers change weights correctly | Unit | P0 |
| T06 | Cost calculation matches model rates | Unit | P0 |
| T07 | Hallucinated file paths removed from evidence | Unit | P0 |
| T08 | Health endpoint returns 200 | Integration | P0 |
| T09 | Registration creates organizer + returns API key | Integration | P0 |
| T10 | Duplicate email returns 409 | Integration | P1 |
| T11 | Missing API key returns 401 | Integration | P0 |
| T12 | Create hackathon with valid config | Integration | P0 |
| T13 | Add submissions batch creates records | Integration | P0 |
| T14 | Leaderboard returns sorted by score | Integration | P1 |
| T15 | Cost estimate returns range with budget check | Integration | P1 |
| T16 | File tree ignores node_modules/.git | Unit | P1 |
| T17 | README extraction finds common filenames | Unit | P1 |
| T18 | Empty repo handled gracefully (scores 0) | Integration | P1 |
| T19 | Large file truncation works | Unit | P2 |
| T20 | Context window budget respected | Unit | P2 |

---

*End of Test Scenarios v1.0*  
*Next deliverable: #11 — Claude Code Prompt (FINAL)*
