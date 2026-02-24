"""Test execution data models."""

from pydantic import BaseModel, Field, computed_field


class TestFramework(str):
    """Detected test framework."""

    PYTEST = "pytest"
    JEST = "jest"
    MOCHA = "mocha"
    VITEST = "vitest"
    GO_TEST = "go_test"
    UNKNOWN = "unknown"


class FailingTest(BaseModel):
    """Details of a failing test."""

    name: str
    error_message: str
    file: str
    line: int | None = None


class TestExecutionResult(BaseModel):
    """Result from test execution."""

    framework: str
    total_tests: int
    passed_tests: int
    failed_tests: int
    skipped_tests: int
    coverage_by_file: dict[str, float] = Field(default_factory=dict)
    failing_tests: list[FailingTest] = Field(default_factory=list)
    duration_ms: int = 0
    timed_out: bool = False
    dependencies_installed: bool = False

    @computed_field
    @property
    def pass_rate(self) -> float:
        """Calculate pass rate as passed / total."""
        if self.total_tests == 0:
            return 0.0
        return self.passed_tests / self.total_tests
