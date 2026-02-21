# Auto-Generate Tests Hook

## Trigger
**Event:** On file save
**Pattern:** `src/**/*.py` (excluding `__init__.py` and files in `tests/`)

## Action
For each saved Python file in the `src/` directory, automatically create or update the corresponding pytest test file in `tests/unit/` with comprehensive test coverage.

## Instructions
When a file is saved (e.g., `src/agents/bug_hunter.py`), perform the following:

1. **Determine test file location:**
   - Map `src/agents/bug_hunter.py` → `tests/unit/test_agents.py`
   - Map `src/services/organizer_service.py` → `tests/unit/test_organizer_service.py`
   - Map `src/utils/bedrock.py` → `tests/unit/test_bedrock.py`

2. **Generate comprehensive pytest tests including:**
   - All public functions and methods
   - Happy path test cases
   - Edge cases (empty inputs, None values, boundary conditions)
   - Error handling tests (expected exceptions)
   - Mocked dependencies:
     - Mock AWS services (DynamoDB, Bedrock) using `moto` or manual mocks
     - Mock external HTTP calls using `httpx` mock
     - Mock git operations for `GitPython`
   - Fixtures for common test data (sample repos, sample responses)

3. **Follow pytest best practices:**
   - Use descriptive test names: `test_analyze_repo_returns_valid_repo_data()`
   - Use `@pytest.fixture` for reusable test setup
   - Use `@pytest.mark.parametrize` for data-driven tests
   - Include docstrings explaining what each test verifies
   - Group related tests in classes if appropriate

4. **Maintain existing tests:**
   - If test file exists, update it intelligently:
     - Add tests for new functions
     - Don't delete manually-written tests
     - Preserve custom test logic
   - If test file doesn't exist, create it from scratch

## Example

**File saved:** `src/agents/bug_hunter.py`

**Generated:** `tests/unit/test_agents.py`

```python
"""Tests for AI agents."""
import pytest
from unittest.mock import Mock, patch
from src.agents.bug_hunter import BugHunterAgent
from src.models.scores import BugHunterResponse
from src.models.analysis import RepoData

@pytest.fixture
def mock_bedrock_client():
    """Mock Bedrock client for testing."""
    client = Mock()
    client.converse.return_value = {
        "output": {"message": {"content": [{"text": '{"overall_score": 7.5}'}]}},
        "usage": {"inputTokens": 1000, "outputTokens": 500, "totalTokens": 1500}
    }
    return client

@pytest.fixture
def sample_repo_data():
    """Sample repository data for testing."""
    return RepoData(
        repo_url="https://github.com/test/repo",
        file_tree="src/main.py\ntests/test_main.py",
        commit_count=10,
        # ... more fields
    )

def test_bug_hunter_analyze_returns_valid_response(mock_bedrock_client, sample_repo_data):
    """Test that BugHunter.analyze returns valid BugHunterResponse."""
    agent = BugHunterAgent(bedrock_client=mock_bedrock_client)
    result = agent.analyze(sample_repo_data)

    assert isinstance(result, BugHunterResponse)
    assert 0 <= result.overall_score <= 10
    assert result.model_used == "amazon.nova-lite-v1:0"

def test_bug_hunter_handles_bedrock_errors(mock_bedrock_client, sample_repo_data):
    """Test that BugHunter handles Bedrock API errors gracefully."""
    mock_bedrock_client.converse.side_effect = Exception("Bedrock error")
    agent = BugHunterAgent(bedrock_client=mock_bedrock_client)

    with pytest.raises(Exception, match="Bedrock error"):
        agent.analyze(sample_repo_data)

@pytest.mark.parametrize("score,expected_valid", [
    (0.0, True),
    (5.5, True),
    (10.0, True),
    (10.1, False),
    (-0.1, False),
])
def test_bug_hunter_validates_score_range(score, expected_valid):
    """Test that scores are validated to be in 0-10 range."""
    # Test implementation
    pass
```

## Benefits
- **Saves 8-10 hours** of manual test writing per week
- **Ensures consistent test coverage** across all modules
- **Catches bugs early** through comprehensive testing
- **Maintains test quality** with best practices enforced

## Configuration
- **Runs automatically** on every save in `src/`
- **Does not run** for test files themselves (no infinite loops)
- **Logs activity** to `.kiro/hooks/logs/auto-test-generator.log`
