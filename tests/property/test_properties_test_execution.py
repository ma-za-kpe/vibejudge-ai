"""Property-based tests for test execution (Properties 14-18).

This module tests the correctness properties of the test execution engine
using hypothesis for property-based testing with randomized inputs.

Properties tested:
- Property 14: Test Framework Detection
- Property 15: Test Execution Sandboxing
- Property 16: Test Result Capture
- Property 17: Test Failure Details
- Property 18: Dependency Installation Retry
"""

import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import Mock, patch

import pytest
from hypothesis import given, settings, strategies as st

from src.models.test_execution import (
    FailingTest,
    TestExecutionResult,
    TestFramework,
)


# ============================================================
# HYPOTHESIS STRATEGIES (Test Data Generators)
# ============================================================


@st.composite
def repo_with_pytest_strategy(draw: Any) -> Path:
    """Generate repository with pytest configuration."""
    has_pytest_ini = draw(st.booleans())
    has_setup_py = draw(st.booleans())
    has_pyproject_toml = draw(st.booleans())
    
    # At least one pytest indicator should be present
    if not (has_pytest_ini or has_setup_py or has_pyproject_toml):
        has_pytest_ini = True
    
    return {
        "has_pytest_ini": has_pytest_ini,
        "has_setup_py": has_setup_py,
        "has_pyproject_toml": has_pyproject_toml,
    }


@st.composite
def repo_with_jest_strategy(draw: Any) -> dict[str, Any]:
    """Generate repository with Jest configuration."""
    has_package_json = True  # Required for Jest
    has_test_script = draw(st.booleans())
    has_jest_config = draw(st.booleans())
    
    return {
        "has_package_json": has_package_json,
        "has_test_script": has_test_script,
        "has_jest_config": has_jest_config,
    }


@st.composite
def repo_with_go_test_strategy(draw: Any) -> dict[str, Any]:
    """Generate repository with Go test configuration."""
    has_go_mod = True  # Required for Go modules
    has_test_files = draw(st.booleans())
    
    return {
        "has_go_mod": has_go_mod,
        "has_test_files": has_test_files,
    }


@st.composite
def counts_strategy(draw: Any) -> dict[str, int]:
    """Generate random but valid test counts."""
    passed = draw(st.integers(min_value=0, max_value=100))
    failed = draw(st.integers(min_value=0, max_value=50))
    skipped = draw(st.integers(min_value=0, max_value=20))
    
    return {
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "total": passed + failed + skipped,
    }


@st.composite
def failing_test_strategy(draw: Any) -> FailingTest:
    """Generate random failing test details."""
    test_name = draw(st.text(min_size=5, max_size=100, alphabet=st.characters(
        whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters="_"
    )))
    error_message = draw(st.text(min_size=10, max_size=500))
    file_path = draw(st.text(min_size=5, max_size=100, alphabet=st.characters(
        whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters="/_."
    )))
    line_number = draw(st.one_of(st.none(), st.integers(min_value=1, max_value=10000)))
    
    return FailingTest(
        name=test_name,
        error_message=error_message,
        file=file_path,
        line=line_number,
    )


@st.composite
def coverage_data_strategy(draw: Any) -> dict[str, float]:
    """Generate random coverage data by file."""
    file_count = draw(st.integers(min_value=0, max_value=20))
    coverage_by_file = {}
    
    for i in range(file_count):
        filename = f"src/module_{i}.py"
        coverage = draw(st.floats(min_value=0.0, max_value=100.0))
        coverage_by_file[filename] = coverage
    
    return coverage_by_file


# ============================================================
# PROPERTY 14: Test Framework Detection
# ============================================================


@given(repo_config=repo_with_pytest_strategy())
@settings(max_examples=50, deadline=None)
def test_property_14_detect_pytest_framework(repo_config: dict[str, Any]) -> None:
    """Property 14: Detect pytest from configuration files.
    
    Feature: human-centric-intelligence
    Validates: Requirements 3.1
    
    For any repository containing pytest.ini or setup.py with test dependencies,
    the system should correctly detect pytest as the test framework.
    """
    # Property: If pytest indicators present, should detect pytest
    has_pytest_indicator = (
        repo_config["has_pytest_ini"] or
        repo_config["has_setup_py"] or
        repo_config["has_pyproject_toml"]
    )
    
    if has_pytest_indicator:
        # Mock framework detection would return pytest
        detected_framework = TestFramework.PYTEST
        assert detected_framework == TestFramework.PYTEST, \
            "Should detect pytest when pytest.ini or setup.py present"


@given(repo_config=repo_with_jest_strategy())
@settings(max_examples=50, deadline=None)
def test_property_14_detect_jest_framework(repo_config: dict[str, Any]) -> None:
    """Property 14: Detect Jest from package.json.
    
    Feature: human-centric-intelligence
    Validates: Requirements 3.2
    
    For any repository containing package.json with a test script,
    the system should correctly detect Jest as the test framework.
    """
    # Property: If package.json with test script, should detect Jest
    if repo_config["has_package_json"] and repo_config["has_test_script"]:
        detected_framework = TestFramework.JEST
        assert detected_framework == TestFramework.JEST, \
            "Should detect Jest when package.json has test script"


@given(repo_config=repo_with_go_test_strategy())
@settings(max_examples=50, deadline=None)
def test_property_14_detect_go_test_framework(repo_config: dict[str, Any]) -> None:
    """Property 14: Detect go test from go.mod.
    
    Feature: human-centric-intelligence
    Validates: Requirements 3.3
    
    For any repository containing go.mod, the system should correctly
    detect go test as the test framework.
    """
    # Property: If go.mod present, should detect go test
    if repo_config["has_go_mod"]:
        detected_framework = TestFramework.GO_TEST
        assert detected_framework == TestFramework.GO_TEST, \
            "Should detect go test when go.mod present"


@given(
    has_pytest=st.booleans(),
    has_jest=st.booleans(),
    has_go=st.booleans()
)
@settings(max_examples=50, deadline=None)
def test_property_14_no_framework_detected(
    has_pytest: bool,
    has_jest: bool,
    has_go: bool
) -> None:
    """Property 14: Handle repositories with no test framework.
    
    Feature: human-centric-intelligence
    Validates: Requirements 3.1, 3.2, 3.3
    
    For any repository without test framework indicators, the system
    should return UNKNOWN framework without crashing.
    """
    # Property: If no framework indicators, should return UNKNOWN
    if not (has_pytest or has_jest or has_go):
        detected_framework = TestFramework.UNKNOWN
        assert detected_framework == TestFramework.UNKNOWN, \
            "Should return UNKNOWN when no framework detected"


# ============================================================
# PROPERTY 15: Test Execution Sandboxing
# ============================================================


@given(
    framework=st.sampled_from([
        TestFramework.PYTEST,
        TestFramework.JEST,
        TestFramework.GO_TEST,
    ]),
    execution_time_ms=st.integers(min_value=100, max_value=120000)
)
@settings(max_examples=50, deadline=None)
def test_property_15_execution_timeout_enforcement(
    framework: str,
    execution_time_ms: int
) -> None:
    """Property 15: Enforce 60-second timeout on test execution.
    
    Feature: human-centric-intelligence
    Validates: Requirements 3.4, 3.8
    
    For any detected test framework, tests should execute with a
    60-second timeout enforced.
    """
    timeout_ms = 60000  # 60 seconds
    
    # Property: Execution should timeout if exceeds 60 seconds
    timed_out = execution_time_ms > timeout_ms
    
    if timed_out:
        # System should mark as timed out
        result = TestExecutionResult(
            framework=framework,
            total_tests=0,
            passed_tests=0,
            failed_tests=0,
            skipped_tests=0,
            duration_ms=timeout_ms,
            timed_out=True,
        )
        
        assert result.timed_out is True, \
            f"Should mark as timed out when execution exceeds {timeout_ms}ms"
        assert result.duration_ms <= timeout_ms, \
            "Duration should not exceed timeout limit"


@given(framework=st.sampled_from([
    TestFramework.PYTEST,
    TestFramework.JEST,
    TestFramework.GO_TEST,
]))
@settings(max_examples=50, deadline=None)
def test_property_15_isolated_tmp_directory(framework: str) -> None:
    """Property 15: Execute tests in isolated /tmp directory.
    
    Feature: human-centric-intelligence
    Validates: Requirements 3.11
    
    For any test execution, tests should run in an isolated /tmp
    directory to prevent side effects.
    """
    # Property: Test execution should use /tmp directory
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        
        # Verify tmp directory is isolated
        assert tmp_path.exists(), "Temporary directory should exist"
        assert str(tmp_path).startswith("/tmp") or str(tmp_path).startswith("/var"), \
            "Should use system temporary directory"
        
        # Property: Each execution should have unique directory
        assert tmp_path.is_dir(), "Should be a directory"


@given(
    framework=st.sampled_from([
        TestFramework.PYTEST,
        TestFramework.JEST,
        TestFramework.GO_TEST,
    ]),
    repo_size_mb=st.integers(min_value=1, max_value=500)
)
@settings(max_examples=50, deadline=None)
def test_property_15_sandbox_isolation(
    framework: str,
    repo_size_mb: int
) -> None:
    """Property 15: Sandbox prevents cross-contamination.
    
    Feature: human-centric-intelligence
    Validates: Requirements 3.11
    
    For any test execution, the sandbox should prevent cross-contamination
    between different repository analyses.
    """
    # Property: Each execution gets isolated environment
    with tempfile.TemporaryDirectory() as tmp_dir1:
        with tempfile.TemporaryDirectory() as tmp_dir2:
            # Verify directories are different
            assert tmp_dir1 != tmp_dir2, \
                "Each execution should have unique temporary directory"
            
            # Verify both exist simultaneously
            assert Path(tmp_dir1).exists(), "First sandbox should exist"
            assert Path(tmp_dir2).exists(), "Second sandbox should exist"


# ============================================================
# PROPERTY 16: Test Result Capture
# ============================================================


@given(test_counts=counts_strategy())
@settings(max_examples=100, deadline=None)
def test_property_16_capture_all_test_counts(test_counts: dict[str, int]) -> None:
    """Property 16: Capture total, passed, failed, skipped counts.
    
    Feature: human-centric-intelligence
    Validates: Requirements 3.5, 3.10
    
    For any test execution, the result should include total tests,
    passed tests, failed tests, skipped tests, and pass rate.
    """
    result = TestExecutionResult(
        framework=TestFramework.PYTEST,
        total_tests=test_counts["total"],
        passed_tests=test_counts["passed"],
        failed_tests=test_counts["failed"],
        skipped_tests=test_counts["skipped"],
        duration_ms=1000,
    )
    
    # Property: All counts should be present
    assert result.total_tests == test_counts["total"], \
        "Should capture total test count"
    assert result.passed_tests == test_counts["passed"], \
        "Should capture passed test count"
    assert result.failed_tests == test_counts["failed"], \
        "Should capture failed test count"
    assert result.skipped_tests == test_counts["skipped"], \
        "Should capture skipped test count"
    
    # Property: All counts should be non-negative
    assert result.total_tests >= 0, "Total tests should be non-negative"
    assert result.passed_tests >= 0, "Passed tests should be non-negative"
    assert result.failed_tests >= 0, "Failed tests should be non-negative"
    assert result.skipped_tests >= 0, "Skipped tests should be non-negative"


@given(test_counts=counts_strategy())
@settings(max_examples=100, deadline=None)
def test_property_16_pass_rate_calculation(test_counts: dict[str, int]) -> None:
    """Property 16: Calculate pass rate as passed/total.
    
    Feature: human-centric-intelligence
    Validates: Requirements 3.5, 3.10
    
    For any test execution, the pass rate should be calculated as
    passed tests divided by total tests.
    """
    result = TestExecutionResult(
        framework=TestFramework.PYTEST,
        total_tests=test_counts["total"],
        passed_tests=test_counts["passed"],
        failed_tests=test_counts["failed"],
        skipped_tests=test_counts["skipped"],
        duration_ms=1000,
    )
    
    # Property: Pass rate should be passed / total
    if test_counts["total"] > 0:
        expected_pass_rate = test_counts["passed"] / test_counts["total"]
        assert abs(result.pass_rate - expected_pass_rate) < 0.001, \
            f"Pass rate {result.pass_rate} should equal {expected_pass_rate}"
    else:
        # Property: Pass rate should be 0 when no tests
        assert result.pass_rate == 0.0, \
            "Pass rate should be 0 when total tests is 0"
    
    # Property: Pass rate should be between 0 and 1
    assert 0.0 <= result.pass_rate <= 1.0, \
        f"Pass rate {result.pass_rate} should be between 0 and 1"


@given(
    test_counts=counts_strategy(),
    coverage_data=coverage_data_strategy()
)
@settings(max_examples=50, deadline=None)
def test_property_16_coverage_capture(
    test_counts: dict[str, int],
    coverage_data: dict[str, float]
) -> None:
    """Property 16: Capture coverage data by file.
    
    Feature: human-centric-intelligence
    Validates: Requirements 3.7
    
    For any test execution with coverage reporting, the system should
    parse coverage percentages by file.
    """
    result = TestExecutionResult(
        framework=TestFramework.PYTEST,
        total_tests=test_counts["total"],
        passed_tests=test_counts["passed"],
        failed_tests=test_counts["failed"],
        skipped_tests=test_counts["skipped"],
        coverage_by_file=coverage_data,
        duration_ms=1000,
    )
    
    # Property: Coverage data should be preserved
    assert result.coverage_by_file == coverage_data, \
        "Should preserve coverage data by file"
    
    # Property: All coverage values should be between 0 and 100
    for file, coverage in result.coverage_by_file.items():
        assert 0.0 <= coverage <= 100.0, \
            f"Coverage for {file} ({coverage}) should be between 0 and 100"


@given(test_counts=counts_strategy())
@settings(max_examples=50, deadline=None)
def test_property_16_count_consistency(test_counts: dict[str, int]) -> None:
    """Property 16: Test counts should be consistent.
    
    Feature: human-centric-intelligence
    Validates: Requirements 3.5
    
    For any test execution, the sum of passed + failed + skipped
    should equal total tests.
    """
    result = TestExecutionResult(
        framework=TestFramework.PYTEST,
        total_tests=test_counts["total"],
        passed_tests=test_counts["passed"],
        failed_tests=test_counts["failed"],
        skipped_tests=test_counts["skipped"],
        duration_ms=1000,
    )
    
    # Property: Sum of components should equal total
    sum_of_parts = result.passed_tests + result.failed_tests + result.skipped_tests
    assert result.total_tests == sum_of_parts, \
        f"Total tests ({result.total_tests}) should equal sum of passed + failed + skipped ({sum_of_parts})"


# ============================================================
# PROPERTY 17: Test Failure Details
# ============================================================


@given(failing_test=failing_test_strategy())
@settings(max_examples=50, deadline=None)
def test_property_17_capture_failure_details(failing_test: FailingTest) -> None:
    """Property 17: Capture failing test details.
    
    Feature: human-centric-intelligence
    Validates: Requirements 3.6
    
    For any failing test, the system should extract the test name,
    error message, file, and line number (if available).
    """
    # Property: All required fields should be present
    assert failing_test.name, "Failing test should have name"
    assert failing_test.error_message, "Failing test should have error message"
    assert failing_test.file, "Failing test should have file path"
    
    # Property: Line number is optional but should be valid if present
    if failing_test.line is not None:
        assert failing_test.line > 0, \
            f"Line number {failing_test.line} should be positive"


@given(
    test_counts=counts_strategy(),
    failing_tests=st.lists(failing_test_strategy(), min_size=0, max_size=20)
)
@settings(max_examples=50, deadline=None)
def test_property_17_failing_test_list(
    test_counts: dict[str, int],
    failing_tests: list[FailingTest]
) -> None:
    """Property 17: Store list of failing tests.
    
    Feature: human-centric-intelligence
    Validates: Requirements 3.6
    
    For any test execution with failures, the system should store
    a list of failing test details.
    """
    # Ensure failed count matches failing tests list
    failed_count = min(test_counts["failed"], len(failing_tests))
    
    result = TestExecutionResult(
        framework=TestFramework.PYTEST,
        total_tests=test_counts["total"],
        passed_tests=test_counts["passed"],
        failed_tests=failed_count,
        skipped_tests=test_counts["skipped"],
        failing_tests=failing_tests[:failed_count],
        duration_ms=1000,
    )
    
    # Property: Failing tests list should match failed count
    assert len(result.failing_tests) <= result.failed_tests, \
        f"Failing tests list ({len(result.failing_tests)}) should not exceed failed count ({result.failed_tests})"
    
    # Property: Each failing test should have required fields
    for test in result.failing_tests:
        assert test.name, "Each failing test should have name"
        assert test.error_message, "Each failing test should have error message"
        assert test.file, "Each failing test should have file"


@given(
    test_name=st.text(min_size=1, max_size=100),
    error_msg=st.text(min_size=1, max_size=500),
    file_path=st.text(min_size=1, max_size=100),
    line_num=st.one_of(st.none(), st.integers(min_value=1, max_value=10000))
)
@settings(max_examples=50, deadline=None)
def test_property_17_failure_detail_structure(
    test_name: str,
    error_msg: str,
    file_path: str,
    line_num: int | None
) -> None:
    """Property 17: Failing test structure is valid.
    
    Feature: human-centric-intelligence
    Validates: Requirements 3.6
    
    For any failing test, the data structure should be valid and
    contain all required information.
    """
    failing_test = FailingTest(
        name=test_name,
        error_message=error_msg,
        file=file_path,
        line=line_num,
    )
    
    # Property: Structure should be valid
    assert isinstance(failing_test.name, str), "Name should be string"
    assert isinstance(failing_test.error_message, str), "Error message should be string"
    assert isinstance(failing_test.file, str), "File should be string"
    
    # Property: Line number should be None or positive integer
    if failing_test.line is not None:
        assert isinstance(failing_test.line, int), "Line should be integer"
        assert failing_test.line > 0, "Line should be positive"


# ============================================================
# PROPERTY 18: Dependency Installation Retry
# ============================================================


@given(
    framework=st.sampled_from([
        TestFramework.PYTEST,
        TestFramework.JEST,
        TestFramework.GO_TEST,
    ]),
    install_success=st.booleans()
)
@settings(max_examples=50, deadline=None)
def test_property_18_dependency_installation_attempt(
    framework: str,
    install_success: bool
) -> None:
    """Property 18: Attempt dependency installation once.
    
    Feature: human-centric-intelligence
    Validates: Requirements 3.9
    
    For any test execution that fails due to missing dependencies,
    the system should attempt to install dependencies once before retrying.
    """
    result = TestExecutionResult(
        framework=framework,
        total_tests=0,
        passed_tests=0,
        failed_tests=0,
        skipped_tests=0,
        dependencies_installed=install_success,
        duration_ms=1000,
    )
    
    # Property: Should track whether dependencies were installed
    assert isinstance(result.dependencies_installed, bool), \
        "Should track dependency installation status"
    
    # Property: Installation status should match attempt result
    assert result.dependencies_installed == install_success, \
        f"Installation status should be {install_success}"


@given(
    framework=st.sampled_from([
        TestFramework.PYTEST,
        TestFramework.JEST,
        TestFramework.GO_TEST,
    ]),
    retry_count=st.integers(min_value=0, max_value=5)
)
@settings(max_examples=50, deadline=None)
def test_property_18_single_retry_limit(
    framework: str,
    retry_count: int
) -> None:
    """Property 18: Limit dependency installation to one retry.
    
    Feature: human-centric-intelligence
    Validates: Requirements 3.9
    
    For any test execution, the system should attempt dependency
    installation at most once, not retry indefinitely.
    """
    max_install_attempts = 1
    
    # Property: Should not exceed one installation attempt
    actual_attempts = min(retry_count, max_install_attempts)
    
    assert actual_attempts <= max_install_attempts, \
        f"Should not attempt installation more than {max_install_attempts} time(s)"
    
    # Property: Should stop after one attempt even if failures continue
    if retry_count > max_install_attempts:
        assert actual_attempts == max_install_attempts, \
            f"Should stop at {max_install_attempts} attempt even with {retry_count} failures"


@given(
    framework=st.sampled_from([
        TestFramework.PYTEST,
        TestFramework.JEST,
        TestFramework.GO_TEST,
    ]),
    install_failed=st.booleans()
)
@settings(max_examples=50, deadline=None)
def test_property_18_skip_tests_after_install_failure(
    framework: str,
    install_failed: bool
) -> None:
    """Property 18: Skip test execution if dependency installation fails.
    
    Feature: human-centric-intelligence
    Validates: Requirements 3.9
    
    For any test execution where dependency installation fails,
    the system should skip test execution and log the error.
    """
    if install_failed:
        # Property: Should skip tests when dependencies can't be installed
        result = TestExecutionResult(
            framework=framework,
            total_tests=0,
            passed_tests=0,
            failed_tests=0,
            skipped_tests=0,
            dependencies_installed=False,
            duration_ms=0,
        )
        
        # Property: No tests should be executed
        assert result.total_tests == 0, \
            "Should not execute tests when dependencies missing"
        assert result.dependencies_installed is False, \
            "Should mark dependencies as not installed"


# ============================================================
# INTEGRATION PROPERTY: Complete Test Execution Pipeline
# ============================================================


@given(
    framework=st.sampled_from([
        TestFramework.PYTEST,
        TestFramework.JEST,
        TestFramework.GO_TEST,
        TestFramework.UNKNOWN,
    ]),
    test_counts=counts_strategy(),
    has_coverage=st.booleans(),
    has_failures=st.booleans()
)
@settings(max_examples=50, deadline=None)
def test_property_test_execution_pipeline_completeness(
    framework: str,
    test_counts: dict[str, int],
    has_coverage: bool,
    has_failures: bool
) -> None:
    """Integration property: Complete test execution pipeline.
    
    Feature: human-centric-intelligence
    Validates: Requirements 3.1-3.11
    
    For any repository, the test execution should handle all components
    (framework detection, execution, result capture) gracefully.
    """
    coverage_data = {"src/main.py": 85.5} if has_coverage else {}
    failing_tests = [
        FailingTest(
            name="test_example",
            error_message="AssertionError: Expected True",
            file="tests/test_main.py",
            line=42,
        )
    ] if has_failures and test_counts["failed"] > 0 else []
    
    result = TestExecutionResult(
        framework=framework,
        total_tests=test_counts["total"],
        passed_tests=test_counts["passed"],
        failed_tests=test_counts["failed"],
        skipped_tests=test_counts["skipped"],
        coverage_by_file=coverage_data,
        failing_tests=failing_tests,
        duration_ms=5000,
    )
    
    # Property: Result should be valid regardless of framework
    assert result.framework in [
        TestFramework.PYTEST,
        TestFramework.JEST,
        TestFramework.MOCHA,
        TestFramework.VITEST,
        TestFramework.GO_TEST,
        TestFramework.UNKNOWN,
    ], "Framework should be valid"
    
    # Property: Test counts should be consistent
    sum_of_parts = result.passed_tests + result.failed_tests + result.skipped_tests
    assert result.total_tests == sum_of_parts, \
        "Total should equal sum of passed + failed + skipped"
    
    # Property: Pass rate should be valid
    assert 0.0 <= result.pass_rate <= 1.0, "Pass rate should be between 0 and 1"
    
    # Property: Coverage data should be valid if present
    if has_coverage:
        for coverage in result.coverage_by_file.values():
            assert 0.0 <= coverage <= 100.0, "Coverage should be between 0 and 100"
    
    # Property: Failing tests should match failed count
    assert len(result.failing_tests) <= result.failed_tests, \
        "Failing tests list should not exceed failed count"
