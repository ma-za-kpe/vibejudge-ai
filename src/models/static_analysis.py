"""Static analysis data models.

This module defines Pydantic models for static analysis results from tools
like Flake8, ESLint, Bandit, etc.
"""

from enum import Enum

from pydantic import Field

from src.models.common import Severity, VibeJudgeBase


class PrimaryLanguage(str, Enum):
    """Primary programming language."""

    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    GO = "go"
    RUST = "rust"
    UNKNOWN = "unknown"


class StaticFinding(VibeJudgeBase):
    """Normalized finding from static analysis tool."""

    tool: str  # flake8, bandit, eslint, etc.
    file: str
    line: int | None = None
    code: str  # Error code (E501, B201, etc.)
    message: str
    severity: Severity
    category: str  # syntax | import | security | style | complexity
    recommendation: str
    verified: bool = False  # Evidence validation status


class StaticAnalysisResult(VibeJudgeBase):
    """Result from static analysis engine."""

    language: PrimaryLanguage
    tools_run: list[str]
    tools_failed: list[str]
    findings: list[StaticFinding]
    total_issues: int
    critical_issues: int
    duration_ms: int
