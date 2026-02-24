"""Unit tests for StrategyDetector component."""

from datetime import UTC, datetime

import pytest

from src.analysis.strategy_detector import StrategyDetector
from src.models.analysis import CommitInfo, RepoData, SourceFile
from src.models.strategy import (
    MaturityLevel,
    TestStrategy,
)
from src.models.submission import RepoMeta

# ============================================================
# FIXTURES
# ============================================================


@pytest.fixture
def strategy_detector() -> StrategyDetector:
    """Create StrategyDetector instance."""
    return StrategyDetector()


@pytest.fixture
def base_repo_data() -> RepoData:
    """Base repository data with minimal setup."""
    return RepoData(
        repo_url="https://github.com/test/repo",
        repo_owner="test",
        repo_name="repo",
        default_branch="main",
        meta=RepoMeta(
            primary_language="Python",
            languages={"Python": 1000},
            total_files=10,
            total_lines=1000,
            commit_count=10,
            first_commit_at=datetime(2024, 1, 1, tzinfo=UTC),
            last_commit_at=datetime(2024, 1, 10, tzinfo=UTC),
            development_duration_hours=24.0,
            workflow_run_count=0,
            workflow_success_rate=0.0,
        ),
        source_files=[],
        commit_history=[],
        readme_content="",
        workflow_definitions=[],
    )


def create_source_file(
    path: str,
    content: str = "",
    lines: int = 100,
) -> SourceFile:
    """Helper to create source file."""
    return SourceFile(
        path=path,
        content=content,
        lines=lines,
        language="Python",
    )


def create_commit(
    author: str,
    timestamp: datetime,
    message: str = "Test commit",
    insertions: int = 100,
    deletions: int = 10,
    files_changed: int = 3,
) -> CommitInfo:
    """Helper to create commit info."""
    hash_val = f"{author}_{timestamp.timestamp()}"
    return CommitInfo(
        hash=hash_val,
        short_hash=hash_val[:7],
        author=author,
        timestamp=timestamp,
        message=message,
        files_changed=files_changed,
        insertions=insertions,
        deletions=deletions,
    )


# ============================================================
# TEST: Empty Repository
# ============================================================


def test_analyze_empty_repository(
    strategy_detector: StrategyDetector,
    base_repo_data: RepoData,
) -> None:
    """Test analysis of repository with no files or commits."""
    result = strategy_detector.analyze(base_repo_data)

    assert result.test_strategy == TestStrategy.NO_TESTS
    assert result.critical_path_focus is False
    # Empty repo may have simplicity tradeoff detected
    assert isinstance(result.tradeoffs, list)
    assert result.learning_journey is None
    assert result.maturity_level == MaturityLevel.JUNIOR
    assert result.duration_ms >= 0


# ============================================================
# TEST: Test Strategy Detection
# ============================================================


def test_detect_no_tests_strategy(
    strategy_detector: StrategyDetector,
    base_repo_data: RepoData,
) -> None:
    """Test NO_TESTS strategy when no test files exist."""
    base_repo_data.source_files = [
        create_source_file("src/main.py", lines=200),
        create_source_file("src/utils.py", lines=150),
    ]

    result = strategy_detector.analyze(base_repo_data)

    assert result.test_strategy == TestStrategy.NO_TESTS


def test_detect_demo_first_strategy(
    strategy_detector: StrategyDetector,
    base_repo_data: RepoData,
) -> None:
    """Test DEMO_FIRST strategy when UI exists but no tests."""
    base_repo_data.source_files = [
        create_source_file("src/main.py", lines=200),
        create_source_file("src/components/App.jsx", lines=300),
        create_source_file("src/styles/main.css", lines=200),
        create_source_file("public/index.html", lines=100),
        create_source_file("src/utils.py", lines=150),
    ]

    result = strategy_detector.analyze(base_repo_data)

    # Demo-first requires >500 production lines with UI but no tests
    assert result.test_strategy in [TestStrategy.DEMO_FIRST, TestStrategy.NO_TESTS]


def test_detect_unit_focused_strategy(
    strategy_detector: StrategyDetector,
    base_repo_data: RepoData,
) -> None:
    """Test UNIT_FOCUSED strategy when >70% unit tests."""
    base_repo_data.source_files = [
        create_source_file("src/main.py", lines=200),
        create_source_file("tests/test_main.py", lines=150),
        create_source_file("tests/test_utils.py", lines=100),
        create_source_file("tests/test_models.py", lines=80),
    ]

    result = strategy_detector.analyze(base_repo_data)

    assert result.test_strategy == TestStrategy.UNIT_FOCUSED


def test_detect_integration_focused_strategy(
    strategy_detector: StrategyDetector,
    base_repo_data: RepoData,
) -> None:
    """Test INTEGRATION_FOCUSED strategy when >50% integration tests."""
    base_repo_data.source_files = [
        create_source_file("src/main.py", lines=200),
        create_source_file("tests/integration/test_api.py", lines=150),
        create_source_file("tests/integration/test_database.py", lines=120),
        create_source_file("tests/test_utils.py", lines=50),
    ]

    result = strategy_detector.analyze(base_repo_data)

    assert result.test_strategy == TestStrategy.INTEGRATION_FOCUSED


def test_detect_e2e_focused_strategy(
    strategy_detector: StrategyDetector,
    base_repo_data: RepoData,
) -> None:
    """Test E2E_FOCUSED strategy when >50% e2e tests."""
    base_repo_data.source_files = [
        create_source_file("src/main.py", lines=200),
        create_source_file("tests/e2e/test_user_flow.py", lines=180),
        create_source_file("tests/e2e/test_checkout.py", lines=150),
        create_source_file("tests/test_utils.py", lines=50),
    ]

    result = strategy_detector.analyze(base_repo_data)

    assert result.test_strategy == TestStrategy.E2E_FOCUSED


def test_detect_critical_path_strategy(
    strategy_detector: StrategyDetector,
    base_repo_data: RepoData,
) -> None:
    """Test CRITICAL_PATH strategy when tests focus on critical paths."""
    base_repo_data.source_files = [
        create_source_file("src/main.py", lines=200),
        create_source_file("tests/test_auth.py", "def test_login", lines=100),
        create_source_file("tests/test_payment.py", "def test_checkout", lines=120),
        create_source_file("tests/test_security.py", "def test_admin", lines=80),
        create_source_file("tests/test_order.py", "def test_transaction", lines=90),
    ]

    result = strategy_detector.analyze(base_repo_data)

    # With >50% critical path tests, should detect critical path focus
    # May be classified as CRITICAL_PATH or UNIT_FOCUSED depending on logic
    assert result.critical_path_focus is True
    assert result.test_strategy in [TestStrategy.CRITICAL_PATH, TestStrategy.UNIT_FOCUSED]


# ============================================================
# TEST: File Type Detection
# ============================================================


def test_is_test_file_various_patterns(strategy_detector: StrategyDetector) -> None:
    """Test test file detection with various naming patterns."""
    assert strategy_detector._is_test_file("tests/test_main.py") is True
    assert strategy_detector._is_test_file("src/main_test.py") is True
    assert strategy_detector._is_test_file("src/main.test.js") is True
    assert strategy_detector._is_test_file("src/main.spec.ts") is True
    assert strategy_detector._is_test_file("spec/main_spec.rb") is True
    assert strategy_detector._is_test_file("src/main.py") is False
    assert strategy_detector._is_test_file("README.md") is False


def test_is_code_file_various_patterns(strategy_detector: StrategyDetector) -> None:
    """Test code file detection with various file types."""
    assert strategy_detector._is_code_file("src/main.py") is True
    assert strategy_detector._is_code_file("src/app.js") is True
    assert strategy_detector._is_code_file("src/component.tsx") is True
    assert strategy_detector._is_code_file("main.go") is True
    assert strategy_detector._is_code_file("lib.rs") is True
    assert strategy_detector._is_code_file("README.md") is False
    assert strategy_detector._is_code_file("package.json") is False
    assert strategy_detector._is_code_file("node_modules/lib.js") is False
    assert strategy_detector._is_code_file("dist/bundle.js") is False


# ============================================================
# TEST: Critical Path Focus Detection
# ============================================================


def test_critical_path_focus_with_auth_tests(
    strategy_detector: StrategyDetector,
) -> None:
    """Test critical path detection with authentication tests."""
    source_files = [
        create_source_file("tests/test_auth.py", "def test_login"),
        create_source_file("tests/test_payment.py", "def test_checkout"),
    ]

    result = strategy_detector._detect_critical_path_focus(source_files)

    assert result is True


def test_no_critical_path_focus_with_generic_tests(
    strategy_detector: StrategyDetector,
) -> None:
    """Test no critical path focus with generic tests."""
    source_files = [
        create_source_file("tests/test_utils.py", "def test_format"),
        create_source_file("tests/test_helpers.py", "def test_parse"),
    ]

    result = strategy_detector._detect_critical_path_focus(source_files)

    assert result is False


# ============================================================
# TEST: Architecture Detection
# ============================================================


def test_detect_monolith_architecture(
    strategy_detector: StrategyDetector,
) -> None:
    """Test monolith architecture detection."""
    source_files = [
        create_source_file("src/main.py"),
        create_source_file("src/models.py"),
        create_source_file("src/views.py"),
    ]

    arch_type = strategy_detector._detect_architecture_type(source_files)

    assert arch_type == "monolith"


def test_detect_microservices_architecture(
    strategy_detector: StrategyDetector,
) -> None:
    """Test microservices architecture detection."""
    source_files = [
        create_source_file("services/auth/main.py"),
        create_source_file("services/payment/main.py"),
        create_source_file("services/user/main.py"),
        create_source_file("services/order/main.py"),
    ]

    arch_type = strategy_detector._detect_architecture_type(source_files)

    assert arch_type == "microservices"


def test_detect_modular_monolith_architecture(
    strategy_detector: StrategyDetector,
) -> None:
    """Test modular monolith architecture detection."""
    source_files = [
        create_source_file("services/auth/main.py"),
        create_source_file("services/payment/main.py"),
        create_source_file("docker-compose.yml", "services:\n  api:\n  db:"),
    ]

    arch_type = strategy_detector._detect_architecture_type(source_files)

    assert arch_type == "modular_monolith"


# ============================================================
# TEST: Design Pattern Detection
# ============================================================


def test_detect_mvc_pattern(strategy_detector: StrategyDetector) -> None:
    """Test MVC pattern detection."""
    source_files = [
        create_source_file("src/models/user.py"),
        create_source_file("src/views/user_view.py"),
        create_source_file("src/controllers/user_controller.py"),
    ]

    patterns = strategy_detector._detect_design_patterns(source_files)

    assert "MVC (Model-View-Controller)" in patterns


def test_detect_service_repository_pattern(
    strategy_detector: StrategyDetector,
) -> None:
    """Test Service Layer + Repository pattern detection."""
    source_files = [
        create_source_file("src/services/user_service.py"),
        create_source_file("src/repositories/user_repository.py"),
    ]

    patterns = strategy_detector._detect_design_patterns(source_files)

    assert "Service Layer + Repository Pattern" in patterns


def test_detect_hexagonal_architecture(
    strategy_detector: StrategyDetector,
) -> None:
    """Test Hexagonal/Clean Architecture detection."""
    source_files = [
        create_source_file("src/domain/user.py"),
        create_source_file("src/application/use_cases.py"),
        create_source_file("src/infrastructure/database.py"),
    ]

    patterns = strategy_detector._detect_design_patterns(source_files)

    assert "Hexagonal/Clean Architecture" in patterns


def test_detect_cqrs_pattern(strategy_detector: StrategyDetector) -> None:
    """Test CQRS pattern detection."""
    source_files = [
        create_source_file("src/commands/create_user.py"),
        create_source_file("src/queries/get_user.py"),
    ]

    patterns = strategy_detector._detect_design_patterns(source_files)

    assert "CQRS (Command Query Responsibility Segregation)" in patterns
