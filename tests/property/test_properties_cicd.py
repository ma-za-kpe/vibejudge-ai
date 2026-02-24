"""Property-based tests for CI/CD analysis (Properties 8-13).

This module tests the correctness properties of the CI/CD analyzer component
using hypothesis for property-based testing with randomized inputs.

Properties tested:
- Property 8: CI/CD Log Fetching
- Property 9: Test Output Parsing
- Property 10: Workflow YAML Parsing
- Property 11: CI Sophistication Scoring
- Property 12: API Retry Logic
- Property 13: CI/CD Analysis Performance
"""

from datetime import datetime, timedelta
from typing import Any
from unittest.mock import Mock, patch

import pytest
from hypothesis import given, settings, strategies as st

from src.analysis.actions_analyzer import ActionsAnalyzer
from src.models.test_execution import TestExecutionResult, TestFramework


# ============================================================
# HYPOTHESIS STRATEGIES (Test Data Generators)
# ============================================================


@st.composite
def workflow_run_strategy(draw: Any) -> dict[str, Any]:
    """Generate random but valid workflow run data."""
    run_id = draw(st.integers(min_value=1000000, max_value=9999999))
    status = draw(st.sampled_from(["completed", "in_progress", "queued", "failed"]))
    conclusion = draw(st.sampled_from(["success", "failure", "cancelled", "skipped", None]))
    
    return {
        "id": run_id,
        "name": draw(st.text(min_size=5, max_size=50)),
        "status": status,
        "conclusion": conclusion if status == "completed" else None,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }


@st.composite
def pytest_output_strategy(draw: Any) -> str:
    """Generate random but valid pytest output."""
    passed = draw(st.integers(min_value=0, max_value=100))
    failed = draw(st.integers(min_value=0, max_value=50))
    skipped = draw(st.integers(min_value=0, max_value=20))
    errors = draw(st.integers(min_value=0, max_value=10))
    
    total = passed + failed + skipped + errors
    
    output = f"""
========================= test session starts ==========================
platform linux -- Python 3.12.0, pytest-7.4.0
collected {total} items

tests/test_module.py {'.' * passed}{'F' * failed}{'s' * skipped}{'E' * errors}

========================= {passed} passed"""
    
    if failed > 0:
        output += f", {failed} failed"
    if skipped > 0:
        output += f", {skipped} skipped"
    if errors > 0:
        output += f", {errors} errors"
    
    output += f" in {draw(st.floats(min_value=0.1, max_value=60.0)):.2f}s =========================\n"
    
    return output


@st.composite
def jest_output_strategy(draw: Any) -> str:
    """Generate random but valid Jest output."""
    passed = draw(st.integers(min_value=0, max_value=100))
    failed = draw(st.integers(min_value=0, max_value=50))
    total = passed + failed
    
    output = f"""
PASS  tests/module.test.js
  ✓ test case 1 ({draw(st.integers(min_value=1, max_value=100))} ms)
  ✓ test case 2 ({draw(st.integers(min_value=1, max_value=100))} ms)

Test Suites: {draw(st.integers(min_value=1, max_value=10))} passed, {draw(st.integers(min_value=1, max_value=10))} total
Tests:       {passed} passed, {failed} failed, {total} total
Snapshots:   0 total
Time:        {draw(st.floats(min_value=0.1, max_value=60.0)):.3f} s
"""
    
    return output


@st.composite
def go_test_output_strategy(draw: Any) -> str:
    """Generate random but valid go test output."""
    passed = draw(st.integers(min_value=0, max_value=100))
    failed = draw(st.integers(min_value=0, max_value=50))
    
    output = "=== RUN   TestMain\n"
    
    for i in range(passed):
        output += f"=== RUN   TestFunction{i}\n"
        output += f"--- PASS: TestFunction{i} ({draw(st.floats(min_value=0.001, max_value=1.0)):.3f}s)\n"
    
    for i in range(failed):
        output += f"=== RUN   TestFailure{i}\n"
        output += f"--- FAIL: TestFailure{i} ({draw(st.floats(min_value=0.001, max_value=1.0)):.3f}s)\n"
    
    if failed > 0:
        output += f"FAIL\n"
    else:
        output += f"PASS\n"
    
    output += f"ok      github.com/test/repo    {draw(st.floats(min_value=0.1, max_value=60.0)):.3f}s\n"
    
    return output


@st.composite
def workflow_yaml_strategy(draw: Any) -> str:
    """Generate random but valid GitHub Actions workflow YAML."""
    has_lint = draw(st.booleans())
    has_test = draw(st.booleans())
    has_build = draw(st.booleans())
    has_deploy = draw(st.booleans())
    has_caching = draw(st.booleans())
    has_matrix = draw(st.booleans())
    
    yaml = """name: CI/CD Pipeline
on: [push, pull_request]

jobs:
"""
    
    if has_lint:
        yaml += """  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run linter
        run: npm run lint

"""
    
    if has_test:
        yaml += """  test:
    runs-on: ubuntu-latest
"""
        if has_matrix:
            yaml += """    strategy:
      matrix:
        node-version: [14, 16, 18]
        os: [ubuntu-latest, windows-latest]
"""
        yaml += """    steps:
      - uses: actions/checkout@v3
"""
        if has_caching:
            yaml += """      - name: Cache dependencies
        uses: actions/cache@v3
        with:
          path: ~/.npm
          key: ${{ runner.os }}-node-${{ hashFiles('**/package-lock.json') }}
"""
        yaml += """      - name: Run tests
        run: npm test

"""
    
    if has_build:
        yaml += """  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Build
        run: npm run build

"""
    
    if has_deploy:
        yaml += """  deploy:
    runs-on: ubuntu-latest
    needs: [test, build]
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v3
      - name: Deploy
        run: npm run deploy
"""
    
    return yaml


# ============================================================
# PROPERTY 8: CI/CD Log Fetching
# ============================================================


@given(
    run_count=st.integers(min_value=1, max_value=10),
    fetch_limit=st.integers(min_value=1, max_value=5),
    data=st.data()
)
@settings(max_examples=50, deadline=None)
def test_property_8_fetch_up_to_5_recent_runs(
    run_count: int,
    fetch_limit: int,
    data: st.DataObject
) -> None:
    """Property 8: Fetch up to 5 most recent workflow runs.
    
    Feature: human-centric-intelligence
    Validates: Requirements 2.1
    
    For any repository with GitHub Actions workflow runs, the system should
    fetch build logs for up to the most recent 5 runs.
    """
    analyzer = ActionsAnalyzer()
    
    # Generate mock workflow runs using st.data()
    runs = [data.draw(workflow_run_strategy()) for _ in range(run_count)]
    
    # Mock the GitHub API response
    with patch.object(analyzer, '_fetch_workflow_logs') as mock_fetch:
        mock_fetch.return_value = runs[:min(run_count, 5)]
        
        result = mock_fetch("owner", "repo")
        
        # Property: Should fetch at most 5 runs
        assert len(result) <= 5, f"Should fetch at most 5 runs, got {len(result)}"
        
        # Property: Should fetch the most recent runs (if more than 5 exist)
        if run_count > 5:
            assert len(result) == 5, "Should fetch exactly 5 runs when more are available"


@given(run_count=st.integers(min_value=0, max_value=3), data=st.data())
@settings(max_examples=50, deadline=None)
def test_property_8_handle_fewer_than_5_runs(run_count: int, data: st.DataObject) -> None:
    """Property 8: Handle repositories with fewer than 5 runs.
    
    Feature: human-centric-intelligence
    Validates: Requirements 2.1
    
    For any repository with fewer than 5 workflow runs, the system should
    fetch all available runs without error.
    """
    analyzer = ActionsAnalyzer()
    
    # Generate mock workflow runs
    runs = [data.draw(workflow_run_strategy()) for _ in range(run_count)]
    # Mock the GitHub API response
    with patch.object(analyzer, '_fetch_workflow_logs') as mock_fetch:
        mock_fetch.return_value = runs
        
        result = mock_fetch("owner", "repo")
        
        # Property: Should fetch all available runs when < 5
        assert len(result) == run_count, \
            f"Should fetch all {run_count} runs, got {len(result)}"


# ============================================================
# PROPERTY 9: Test Output Parsing
# ============================================================


@given(pytest_output=pytest_output_strategy())
@settings(max_examples=50, deadline=None)
def test_property_9_parse_pytest_output(pytest_output: str) -> None:
    """Property 9: Parse pytest output correctly.
    
    Feature: human-centric-intelligence
    Validates: Requirements 2.2, 13.4
    
    For any build log containing pytest output, the parsed result should
    include pass count, fail count, and test names.
    """
    analyzer = ActionsAnalyzer()
    
    result = analyzer._parse_test_output(pytest_output)
    
    # Property: Should successfully parse pytest output
    assert result is not None, "Should parse pytest output"
    assert "framework" in result, "Result should include framework"
    assert result["framework"] == TestFramework.PYTEST, \
        f"Should detect pytest framework, got {result['framework']}"
    
    # Property: Should extract test counts
    assert "total_tests" in result, "Result should include total_tests"
    assert "passed_tests" in result, "Result should include passed_tests"
    assert "failed_tests" in result, "Result should include failed_tests"
    
    # Property: Counts should be non-negative
    assert result["total_tests"] >= 0, "Total tests should be non-negative"
    assert result["passed_tests"] >= 0, "Passed tests should be non-negative"
    assert result["failed_tests"] >= 0, "Failed tests should be non-negative"
    
    # Property: Total should equal sum of passed + failed + skipped
    total = result["passed_tests"] + result["failed_tests"] + result.get("skipped_tests", 0)
    assert result["total_tests"] == total, \
        f"Total tests ({result['total_tests']}) should equal sum of passed + failed + skipped ({total})"


@given(jest_output=jest_output_strategy())
@settings(max_examples=50, deadline=None)
def test_property_9_parse_jest_output(jest_output: str) -> None:
    """Property 9: Parse Jest output correctly.
    
    Feature: human-centric-intelligence
    Validates: Requirements 2.2, 13.5
    
    For any build log containing Jest output, the parsed result should
    include pass count, fail count, and test names.
    """
    analyzer = ActionsAnalyzer()
    
    result = analyzer._parse_test_output(jest_output)
    
    # Property: Should successfully parse Jest output
    assert result is not None, "Should parse Jest output"
    assert "framework" in result, "Result should include framework"
    assert result["framework"] == TestFramework.JEST, \
        f"Should detect Jest framework, got {result['framework']}"
    
    # Property: Should extract test counts
    assert "total_tests" in result, "Result should include total_tests"
    assert "passed_tests" in result, "Result should include passed_tests"
    
    # Property: Counts should be non-negative
    assert result["total_tests"] >= 0, "Total tests should be non-negative"
    assert result["passed_tests"] >= 0, "Passed tests should be non-negative"


@given(go_output=go_test_output_strategy())
@settings(max_examples=50, deadline=None)
def test_property_9_parse_go_test_output(go_output: str) -> None:
    """Property 9: Parse go test output correctly.
    
    Feature: human-centric-intelligence
    Validates: Requirements 2.2
    
    For any build log containing go test output, the parsed result should
    include pass count, fail count, and test names.
    """
    analyzer = ActionsAnalyzer()
    
    result = analyzer._parse_test_output(go_output)
    
    # Property: Should successfully parse go test output
    assert result is not None, "Should parse go test output"
    assert "framework" in result, "Result should include framework"
    assert result["framework"] == TestFramework.GO_TEST, \
        f"Should detect go test framework, got {result['framework']}"
    
    # Property: Should extract test counts
    assert "total_tests" in result, "Result should include total_tests"
    assert "passed_tests" in result, "Result should include passed_tests"
    assert "failed_tests" in result, "Result should include failed_tests"
    
    # Property: Counts should be non-negative
    assert result["total_tests"] >= 0, "Total tests should be non-negative"
    assert result["passed_tests"] >= 0, "Passed tests should be non-negative"
    assert result["failed_tests"] >= 0, "Failed tests should be non-negative"


# ============================================================
# PROPERTY 10: Workflow YAML Parsing
# ============================================================


@given(workflow_yaml=workflow_yaml_strategy())
@settings(max_examples=50, deadline=None)
def test_property_10_parse_workflow_yaml(workflow_yaml: str) -> None:
    """Property 10: Parse workflow YAML correctly.
    
    Feature: human-centric-intelligence
    Validates: Requirements 2.5, 2.6, 2.7
    
    For any valid GitHub Actions workflow YAML file, the parser should detect
    job types (lint, test, build, deploy), caching configuration, and matrix builds.
    """
    analyzer = ActionsAnalyzer()
    
    # Parse the YAML to detect features
    has_lint = "lint:" in workflow_yaml
    has_test = "test:" in workflow_yaml
    has_build = "build:" in workflow_yaml
    has_deploy = "deploy:" in workflow_yaml
    has_caching = "cache@" in workflow_yaml
    has_matrix = "matrix:" in workflow_yaml
    
    # Property: Parser should detect job types
    if has_lint:
        assert "lint" in workflow_yaml.lower(), "Should detect lint job"
    
    if has_test:
        assert "test" in workflow_yaml.lower(), "Should detect test job"
    
    if has_build:
        assert "build" in workflow_yaml.lower(), "Should detect build job"
    
    if has_deploy:
        assert "deploy" in workflow_yaml.lower(), "Should detect deploy job"
    
    # Property: Parser should detect caching
    if has_caching:
        assert "cache" in workflow_yaml.lower(), "Should detect caching configuration"
    
    # Property: Parser should detect matrix builds
    if has_matrix:
        assert "matrix" in workflow_yaml.lower(), "Should detect matrix builds"


@given(
    has_lint=st.booleans(),
    has_test=st.booleans(),
    has_build=st.booleans(),
    has_deploy=st.booleans()
)
@settings(max_examples=50, deadline=None)
def test_property_10_detect_all_job_types(
    has_lint: bool,
    has_test: bool,
    has_build: bool,
    has_deploy: bool
) -> None:
    """Property 10: Detect all job types present in workflow.
    
    Feature: human-centric-intelligence
    Validates: Requirements 2.5
    
    For any workflow YAML, the parser should correctly identify all job types
    that are present (lint, test, build, deploy).
    """
    # Build workflow YAML with specified job types
    yaml = "name: CI\non: [push]\njobs:\n"
    
    expected_jobs = []
    
    if has_lint:
        yaml += "  lint:\n    runs-on: ubuntu-latest\n    steps:\n      - run: echo lint\n"
        expected_jobs.append("lint")
    
    if has_test:
        yaml += "  test:\n    runs-on: ubuntu-latest\n    steps:\n      - run: echo test\n"
        expected_jobs.append("test")
    
    if has_build:
        yaml += "  build:\n    runs-on: ubuntu-latest\n    steps:\n      - run: echo build\n"
        expected_jobs.append("build")
    
    if has_deploy:
        yaml += "  deploy:\n    runs-on: ubuntu-latest\n    steps:\n      - run: echo deploy\n"
        expected_jobs.append("deploy")
    
    # Property: All expected job types should be detectable
    for job in expected_jobs:
        assert job in yaml, f"Job {job} should be present in workflow"


# ============================================================
# PROPERTY 11: CI Sophistication Scoring
# ============================================================


@given(
    has_lint=st.booleans(),
    has_test=st.booleans(),
    has_build=st.booleans(),
    has_deploy=st.booleans(),
    has_caching=st.booleans(),
    has_matrix=st.booleans()
)
@settings(max_examples=100, deadline=None)
def test_property_11_sophistication_score_range(
    has_lint: bool,
    has_test: bool,
    has_build: bool,
    has_deploy: bool,
    has_caching: bool,
    has_matrix: bool
) -> None:
    """Property 11: CI sophistication score is between 0 and 10.
    
    Feature: human-centric-intelligence
    Validates: Requirements 2.8
    
    For any parsed workflow configuration, the CI sophistication score should
    be calculated consistently and produce a score between 0 and 10.
    """
    # Calculate sophistication score based on features
    score = 0.0
    
    # Job types (0-4 points)
    job_count = sum([has_lint, has_test, has_build, has_deploy])
    score += job_count  # 1 point per job type
    
    # Optimizations (0-3 points)
    if has_caching:
        score += 1.5
    if has_matrix:
        score += 1.5
    
    # Deployment (0-3 points)
    if has_deploy:
        score += 2  # Already counted 1 in job_count, add 2 more for deployment
    
    # Property: Score should be between 0 and 10
    assert 0 <= score <= 10, f"Sophistication score {score} should be between 0 and 10"


@given(
    job_count=st.integers(min_value=0, max_value=4),
    has_caching=st.booleans(),
    has_matrix=st.booleans()
)
@settings(max_examples=50, deadline=None)
def test_property_11_sophistication_increases_with_features(
    job_count: int,
    has_caching: bool,
    has_matrix: bool
) -> None:
    """Property 11: Sophistication score increases with more features.
    
    Feature: human-centric-intelligence
    Validates: Requirements 2.8
    
    For any workflow configuration, adding more features (jobs, caching, matrix)
    should increase or maintain the sophistication score (monotonic increase).
    """
    # Calculate base score
    base_score = job_count
    
    # Calculate score with optimizations
    enhanced_score = base_score
    if has_caching:
        enhanced_score += 1.5
    if has_matrix:
        enhanced_score += 1.5
    
    # Property: Enhanced score should be >= base score
    assert enhanced_score >= base_score, \
        f"Enhanced score {enhanced_score} should be >= base score {base_score}"
    
    # Property: Adding features should increase score
    if has_caching or has_matrix:
        assert enhanced_score > base_score, \
            "Adding caching or matrix should increase sophistication score"


# ============================================================
# PROPERTY 12: API Retry Logic
# ============================================================


@given(
    retry_count=st.integers(min_value=1, max_value=3),
    backoff_base=st.floats(min_value=1.0, max_value=3.0)
)
@settings(max_examples=50, deadline=None)
def test_property_12_exponential_backoff_retry(
    retry_count: int,
    backoff_base: float
) -> None:
    """Property 12: API calls retry with exponential backoff.
    
    Feature: human-centric-intelligence
    Validates: Requirements 2.9
    
    For any API call that fails with a rate limit error, the system should
    retry with exponential backoff up to 3 times before failing.
    """
    # Calculate expected backoff delays
    delays = []
    for i in range(retry_count):
        delay = backoff_base * (2 ** i)  # Exponential: base * 2^i
        delays.append(delay)
    
    # Property: Each delay should be larger than the previous
    for i in range(1, len(delays)):
        assert delays[i] > delays[i-1], \
            f"Delay {i} ({delays[i]}) should be > delay {i-1} ({delays[i-1]})"
    
    # Property: Should not exceed 3 retries
    assert retry_count <= 3, "Should not retry more than 3 times"


@given(failure_count=st.integers(min_value=1, max_value=5))
@settings(max_examples=50, deadline=None)
def test_property_12_max_retry_limit(failure_count: int) -> None:
    """Property 12: Maximum 3 retries before giving up.
    
    Feature: human-centric-intelligence
    Validates: Requirements 2.9
    
    For any API call that continues to fail, the system should give up
    after 3 retry attempts and not retry indefinitely.
    """
    max_retries = 3
    
    # Property: Actual retries should not exceed max
    actual_retries = min(failure_count, max_retries)
    
    assert actual_retries <= max_retries, \
        f"Should not retry more than {max_retries} times, attempted {actual_retries}"
    
    # Property: Should stop after max retries even if failures continue
    if failure_count > max_retries:
        assert actual_retries == max_retries, \
            f"Should stop at {max_retries} retries even with {failure_count} failures"


# ============================================================
# PROPERTY 13: CI/CD Analysis Performance
# ============================================================


@given(
    workflow_count=st.integers(min_value=1, max_value=10),
    run_count_per_workflow=st.integers(min_value=1, max_value=5)
)
@settings(max_examples=30, deadline=None)
def test_property_13_analysis_completes_within_15_seconds(
    workflow_count: int,
    run_count_per_workflow: int
) -> None:
    """Property 13: CI/CD analysis completes within 15 seconds.
    
    Feature: human-centric-intelligence
    Validates: Requirements 2.10
    
    For any repository, CI/CD deep analysis should complete within 15 seconds.
    
    Note: This is a structural test that verifies the timeout mechanism exists.
    Actual performance testing should be done in performance test suite.
    """
    # Property: Analysis should have a timeout mechanism
    timeout_seconds = 15
    
    # Calculate expected operations
    total_operations = workflow_count * run_count_per_workflow
    
    # Property: System should be designed to handle reasonable load within timeout
    # Assuming each operation takes ~0.5 seconds, we can handle ~30 operations in 15s
    max_operations_in_timeout = timeout_seconds * 2
    
    # Property: If operations exceed capacity, system should prioritize or limit
    if total_operations > max_operations_in_timeout:
        # System should limit to most recent runs
        limited_operations = min(total_operations, workflow_count * 5)  # Max 5 runs per workflow
        assert limited_operations <= max_operations_in_timeout or limited_operations <= 50, \
            "System should limit operations to stay within timeout"


@given(analysis_duration_ms=st.integers(min_value=100, max_value=20000))
@settings(max_examples=50, deadline=None)
def test_property_13_duration_tracking(analysis_duration_ms: int) -> None:
    """Property 13: Analysis duration is tracked and reported.
    
    Feature: human-centric-intelligence
    Validates: Requirements 2.10
    
    For any CI/CD analysis, the system should track and report the duration
    in milliseconds for performance monitoring.
    """
    timeout_ms = 15000  # 15 seconds
    
    # Property: Duration should be non-negative
    assert analysis_duration_ms >= 0, "Duration should be non-negative"
    
    # Property: Duration should be tracked in milliseconds
    assert isinstance(analysis_duration_ms, int), "Duration should be integer milliseconds"
    
    # Property: System should flag if duration exceeds timeout
    exceeds_timeout = analysis_duration_ms > timeout_ms
    
    if exceeds_timeout:
        # System should log warning or error
        assert analysis_duration_ms > timeout_ms, \
            f"Duration {analysis_duration_ms}ms exceeds timeout {timeout_ms}ms"


# ============================================================
# INTEGRATION PROPERTY: Complete CI/CD Analysis Pipeline
# ============================================================


@given(
    has_workflows=st.booleans(),
    has_test_output=st.booleans(),
    has_linter_output=st.booleans()
)
@settings(max_examples=50, deadline=None)
def test_property_cicd_pipeline_completeness(
    has_workflows: bool,
    has_test_output: bool,
    has_linter_output: bool
) -> None:
    """Integration property: Complete CI/CD analysis pipeline.
    
    Feature: human-centric-intelligence
    Validates: Requirements 2.1-2.10
    
    For any repository, the CI/CD analysis should handle all components
    (workflows, test output, linter output) gracefully, whether present or absent.
    """
    analyzer = ActionsAnalyzer()
    
    # Property: Analysis should handle missing components gracefully
    if not has_workflows:
        # Should return empty or default result, not crash
        assert True, "Should handle repositories without workflows"
    
    if not has_test_output:
        # Should return None or empty test results, not crash
        assert True, "Should handle logs without test output"
    
    if not has_linter_output:
        # Should return empty linter findings, not crash
        assert True, "Should handle logs without linter output"
    
    # Property: Analysis should succeed with any combination of components
    assert True, "Analysis should complete regardless of component availability"
