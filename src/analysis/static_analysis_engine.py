"""Static analysis engine for running code quality tools across multiple languages."""

import json
import os
import subprocess
import time
from collections import Counter
from pathlib import Path
from typing import TypedDict

import structlog

from src.models.common import Severity
from src.models.static_analysis import (
    PrimaryLanguage,
    StaticAnalysisResult,
    StaticFinding,
)

logger = structlog.get_logger()


class ToolConfig(TypedDict):
    """Configuration for a static analysis tool."""

    name: str
    cmd: list[str]
    timeout: int


# Tool configurations by language
STATIC_TOOLS: dict[str, list[ToolConfig]] = {
    "python": [
        {"name": "flake8", "cmd": ["flake8", "--format=json", "."], "timeout": 30},
        {"name": "bandit", "cmd": ["bandit", "-r", "-f", "json", "."], "timeout": 30},
        {"name": "safety", "cmd": ["safety", "check", "--json"], "timeout": 20},
        {"name": "radon", "cmd": ["radon", "cc", "-j", "."], "timeout": 20},
    ],
    "javascript": [
        {"name": "eslint", "cmd": ["eslint", "--format=json", "."], "timeout": 30},
        {"name": "npm_audit", "cmd": ["npm", "audit", "--json"], "timeout": 20},
    ],
    "typescript": [
        {"name": "eslint", "cmd": ["eslint", "--format=json", "."], "timeout": 30},
        {"name": "npm_audit", "cmd": ["npm", "audit", "--json"], "timeout": 20},
    ],
    "go": [
        {"name": "go_vet", "cmd": ["go", "vet", "./..."], "timeout": 30},
        {"name": "staticcheck", "cmd": ["staticcheck", "./..."], "timeout": 30},
    ],
    "rust": [
        {"name": "clippy", "cmd": ["cargo", "clippy", "--message-format=json"], "timeout": 30},
        {"name": "cargo_audit", "cmd": ["cargo", "audit", "--json"], "timeout": 20},
    ],
}


class StaticAnalysisEngine:
    """Orchestrates static analysis tools for multiple languages."""

    def __init__(self) -> None:
        """Initialize the static analysis engine."""
        self.logger = logger.bind(component="static_analysis_engine")

    def analyze(self, repo_path: str, timeout_seconds: int = 30) -> StaticAnalysisResult:
        """Run static analysis on repository.

        Args:
            repo_path: Path to cloned repository
            timeout_seconds: Timeout per tool (default: 30)

        Returns:
            StaticAnalysisResult with normalized findings
        """
        start_time = time.time()
        self.logger.info("static_analysis_started", repo_path=repo_path)

        # Detect primary language
        language = self._detect_language(repo_path)
        self.logger.info("language_detected", language=language)

        # Get tools for this language
        tools = STATIC_TOOLS.get(language, [])
        if not tools:
            self.logger.warning("no_tools_for_language", language=language)
            return StaticAnalysisResult(
                language=language,
                tools_run=[],
                tools_failed=[],
                findings=[],
                total_issues=0,
                critical_issues=0,
                duration_ms=int((time.time() - start_time) * 1000),
            )

        # Run tools based on language
        all_findings: list[StaticFinding] = []
        tools_run: list[str] = []
        tools_failed: list[str] = []

        if language == PrimaryLanguage.PYTHON:
            findings, run, failed = self._run_python_tools(repo_path, timeout_seconds)
            all_findings.extend(findings)
            tools_run.extend(run)
            tools_failed.extend(failed)
        elif language in (PrimaryLanguage.JAVASCRIPT, PrimaryLanguage.TYPESCRIPT):
            findings, run, failed = self._run_javascript_tools(repo_path, timeout_seconds)
            all_findings.extend(findings)
            tools_run.extend(run)
            tools_failed.extend(failed)
        elif language == PrimaryLanguage.GO:
            findings, run, failed = self._run_go_tools(repo_path, timeout_seconds)
            all_findings.extend(findings)
            tools_run.extend(run)
            tools_failed.extend(failed)
        elif language == PrimaryLanguage.RUST:
            findings, run, failed = self._run_rust_tools(repo_path, timeout_seconds)
            all_findings.extend(findings)
            tools_run.extend(run)
            tools_failed.extend(failed)

        # Validate evidence for all findings
        for finding in all_findings:
            self._validate_evidence(finding, repo_path)

        # Calculate statistics
        total_issues = len(all_findings)
        critical_issues = sum(1 for f in all_findings if f.severity == Severity.CRITICAL)

        duration_ms = int((time.time() - start_time) * 1000)

        self.logger.info(
            "static_analysis_completed",
            language=language,
            tools_run=len(tools_run),
            tools_failed=len(tools_failed),
            total_issues=total_issues,
            critical_issues=critical_issues,
            duration_ms=duration_ms,
        )

        return StaticAnalysisResult(
            language=language,
            tools_run=tools_run,
            tools_failed=tools_failed,
            findings=all_findings,
            total_issues=total_issues,
            critical_issues=critical_issues,
            duration_ms=duration_ms,
        )

    def _detect_language(self, repo_path: str) -> PrimaryLanguage:
        """Detect primary language from file extensions.

        Args:
            repo_path: Path to repository

        Returns:
            Detected primary language
        """
        extension_counts: Counter[str] = Counter()

        try:
            for root, _, files in os.walk(repo_path):
                # Skip hidden directories and common non-source directories
                if any(
                    part.startswith(".")
                    or part in ("node_modules", "venv", "__pycache__", "target", "dist", "build")
                    for part in Path(root).parts
                ):
                    continue

                for file in files:
                    ext = Path(file).suffix.lower()
                    if ext:
                        extension_counts[ext] += 1
        except Exception as e:
            self.logger.error("language_detection_failed", error=str(e))
            return PrimaryLanguage.UNKNOWN

        # Map extensions to languages
        if not extension_counts:
            return PrimaryLanguage.UNKNOWN

        most_common_ext = extension_counts.most_common(1)[0][0]

        language_map = {
            ".py": PrimaryLanguage.PYTHON,
            ".js": PrimaryLanguage.JAVASCRIPT,
            ".jsx": PrimaryLanguage.JAVASCRIPT,
            ".ts": PrimaryLanguage.TYPESCRIPT,
            ".tsx": PrimaryLanguage.TYPESCRIPT,
            ".go": PrimaryLanguage.GO,
            ".rs": PrimaryLanguage.RUST,
        }

        return language_map.get(most_common_ext, PrimaryLanguage.UNKNOWN)

    def _run_python_tools(
        self, repo_path: str, timeout_seconds: int
    ) -> tuple[list[StaticFinding], list[str], list[str]]:
        """Run Python static analysis tools.

        Args:
            repo_path: Path to repository
            timeout_seconds: Timeout per tool

        Returns:
            Tuple of (findings, tools_run, tools_failed)
        """
        findings: list[StaticFinding] = []
        tools_run: list[str] = []
        tools_failed: list[str] = []

        for tool_config in STATIC_TOOLS["python"]:
            tool_name = tool_config["name"]
            cmd = tool_config["cmd"]
            timeout = tool_config["timeout"]

            try:
                # Check if tool is installed
                check_cmd = [cmd[0], "--version"]
                subprocess.run(
                    check_cmd,
                    capture_output=True,
                    timeout=5,
                    cwd=repo_path,
                )
            except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.CalledProcessError):
                self.logger.warning("tool_not_installed", tool=tool_name)
                tools_failed.append(tool_name)
                continue

            # Run the tool
            try:
                self.logger.info("running_tool", tool=tool_name, timeout=timeout)
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    timeout=timeout,
                    cwd=repo_path,
                    text=True,
                )

                # Parse output
                tool_findings = self._parse_python_tool_output(
                    tool_name, result.stdout, result.stderr
                )
                findings.extend(tool_findings)
                tools_run.append(tool_name)

                self.logger.info("tool_completed", tool=tool_name, findings=len(tool_findings))

            except subprocess.TimeoutExpired:
                self.logger.warning("tool_timeout", tool=tool_name, timeout=timeout)
                tools_failed.append(tool_name)
            except Exception as e:
                self.logger.error("tool_execution_failed", tool=tool_name, error=str(e))
                tools_failed.append(tool_name)

        return findings, tools_run, tools_failed

    def _run_javascript_tools(
        self, repo_path: str, timeout_seconds: int
    ) -> tuple[list[StaticFinding], list[str], list[str]]:
        """Run JavaScript/TypeScript static analysis tools.

        Args:
            repo_path: Path to repository
            timeout_seconds: Timeout per tool

        Returns:
            Tuple of (findings, tools_run, tools_failed)
        """
        findings: list[StaticFinding] = []
        tools_run: list[str] = []
        tools_failed: list[str] = []

        for tool_config in STATIC_TOOLS["javascript"]:
            tool_name = tool_config["name"]
            cmd = tool_config["cmd"]
            timeout = tool_config["timeout"]

            try:
                # Check if tool is installed
                check_cmd = [cmd[0], "--version"]
                subprocess.run(
                    check_cmd,
                    capture_output=True,
                    timeout=5,
                    cwd=repo_path,
                )
            except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.CalledProcessError):
                self.logger.warning("tool_not_installed", tool=tool_name)
                tools_failed.append(tool_name)
                continue

            # Run the tool
            try:
                self.logger.info("running_tool", tool=tool_name, timeout=timeout)
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    timeout=timeout,
                    cwd=repo_path,
                    text=True,
                )

                # Parse output
                tool_findings = self._parse_javascript_tool_output(
                    tool_name, result.stdout, result.stderr
                )
                findings.extend(tool_findings)
                tools_run.append(tool_name)

                self.logger.info("tool_completed", tool=tool_name, findings=len(tool_findings))

            except subprocess.TimeoutExpired:
                self.logger.warning("tool_timeout", tool=tool_name, timeout=timeout)
                tools_failed.append(tool_name)
            except Exception as e:
                self.logger.error("tool_execution_failed", tool=tool_name, error=str(e))
                tools_failed.append(tool_name)

        return findings, tools_run, tools_failed

    def _run_go_tools(
        self, repo_path: str, timeout_seconds: int
    ) -> tuple[list[StaticFinding], list[str], list[str]]:
        """Run Go static analysis tools.

        Args:
            repo_path: Path to repository
            timeout_seconds: Timeout per tool

        Returns:
            Tuple of (findings, tools_run, tools_failed)
        """
        findings: list[StaticFinding] = []
        tools_run: list[str] = []
        tools_failed: list[str] = []

        for tool_config in STATIC_TOOLS["go"]:
            tool_name = tool_config["name"]
            cmd = tool_config["cmd"]
            timeout = tool_config["timeout"]

            try:
                # Check if tool is installed
                check_cmd = [cmd[0], "version"]
                subprocess.run(
                    check_cmd,
                    capture_output=True,
                    timeout=5,
                    cwd=repo_path,
                )
            except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.CalledProcessError):
                self.logger.warning("tool_not_installed", tool=tool_name)
                tools_failed.append(tool_name)
                continue

            # Run the tool
            try:
                self.logger.info("running_tool", tool=tool_name, timeout=timeout)
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    timeout=timeout,
                    cwd=repo_path,
                    text=True,
                )

                # Parse output
                tool_findings = self._parse_go_tool_output(tool_name, result.stdout, result.stderr)
                findings.extend(tool_findings)
                tools_run.append(tool_name)

                self.logger.info("tool_completed", tool=tool_name, findings=len(tool_findings))

            except subprocess.TimeoutExpired:
                self.logger.warning("tool_timeout", tool=tool_name, timeout=timeout)
                tools_failed.append(tool_name)
            except Exception as e:
                self.logger.error("tool_execution_failed", tool=tool_name, error=str(e))
                tools_failed.append(tool_name)

        return findings, tools_run, tools_failed

    def _run_rust_tools(
        self, repo_path: str, timeout_seconds: int
    ) -> tuple[list[StaticFinding], list[str], list[str]]:
        """Run Rust static analysis tools.

        Args:
            repo_path: Path to repository
            timeout_seconds: Timeout per tool

        Returns:
            Tuple of (findings, tools_run, tools_failed)
        """
        findings: list[StaticFinding] = []
        tools_run: list[str] = []
        tools_failed: list[str] = []

        for tool_config in STATIC_TOOLS["rust"]:
            tool_name = tool_config["name"]
            cmd = tool_config["cmd"]
            timeout = tool_config["timeout"]

            try:
                # Check if tool is installed
                check_cmd = [cmd[0], "--version"]
                subprocess.run(
                    check_cmd,
                    capture_output=True,
                    timeout=5,
                    cwd=repo_path,
                )
            except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.CalledProcessError):
                self.logger.warning("tool_not_installed", tool=tool_name)
                tools_failed.append(tool_name)
                continue

            # Run the tool
            try:
                self.logger.info("running_tool", tool=tool_name, timeout=timeout)
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    timeout=timeout,
                    cwd=repo_path,
                    text=True,
                )

                # Parse output
                tool_findings = self._parse_rust_tool_output(
                    tool_name, result.stdout, result.stderr
                )
                findings.extend(tool_findings)
                tools_run.append(tool_name)

                self.logger.info("tool_completed", tool=tool_name, findings=len(tool_findings))

            except subprocess.TimeoutExpired:
                self.logger.warning("tool_timeout", tool=tool_name, timeout=timeout)
                tools_failed.append(tool_name)
            except Exception as e:
                self.logger.error("tool_execution_failed", tool=tool_name, error=str(e))
                tools_failed.append(tool_name)

        return findings, tools_run, tools_failed

    def _parse_python_tool_output(
        self, tool_name: str, stdout: str, stderr: str
    ) -> list[StaticFinding]:
        """Parse Python tool output into normalized findings.

        Args:
            tool_name: Name of the tool
            stdout: Standard output from tool
            stderr: Standard error from tool

        Returns:
            List of normalized findings
        """
        findings: list[StaticFinding] = []

        try:
            if tool_name == "flake8":
                data = json.loads(stdout) if stdout else {}
                for file_path, issues in data.items():
                    for issue in issues:
                        finding = self._normalize_finding(
                            tool=tool_name,
                            file=file_path,
                            line=issue.get("line_number"),
                            code=issue.get("code", "UNKNOWN"),
                            message=issue.get("text", ""),
                            severity=self._map_severity(issue.get("code", "")),
                            category="style",
                        )
                        findings.append(finding)

            elif tool_name == "bandit":
                data = json.loads(stdout) if stdout else {}
                for issue in data.get("results", []):
                    finding = self._normalize_finding(
                        tool=tool_name,
                        file=issue.get("filename", ""),
                        line=issue.get("line_number"),
                        code=issue.get("test_id", "UNKNOWN"),
                        message=issue.get("issue_text", ""),
                        severity=self._map_bandit_severity(issue.get("issue_severity", "LOW")),
                        category="security",
                    )
                    findings.append(finding)

            elif tool_name == "safety":
                data = json.loads(stdout) if stdout else {}
                for vuln in data.get("vulnerabilities", []):
                    finding = self._normalize_finding(
                        tool=tool_name,
                        file="requirements.txt",
                        line=None,
                        code=vuln.get("id", "UNKNOWN"),
                        message=f"{vuln.get('package', 'Unknown')}: {vuln.get('advisory', '')}",
                        severity=Severity.HIGH,
                        category="security",
                    )
                    findings.append(finding)

            elif tool_name == "radon":
                data = json.loads(stdout) if stdout else {}
                for file_path, metrics in data.items():
                    for metric in metrics:
                        if metric.get("complexity", 0) > 10:
                            finding = self._normalize_finding(
                                tool=tool_name,
                                file=file_path,
                                line=metric.get("lineno"),
                                code="CC",
                                message=f"High complexity: {metric.get('complexity')}",
                                severity=Severity.MEDIUM,
                                category="complexity",
                            )
                            findings.append(finding)

        except json.JSONDecodeError as e:
            self.logger.error("json_parse_error", tool=tool_name, error=str(e))
        except Exception as e:
            self.logger.error("parse_error", tool=tool_name, error=str(e))

        return findings

    def _parse_javascript_tool_output(
        self, tool_name: str, stdout: str, stderr: str
    ) -> list[StaticFinding]:
        """Parse JavaScript/TypeScript tool output into normalized findings.

        Args:
            tool_name: Name of the tool
            stdout: Standard output from tool
            stderr: Standard error from tool

        Returns:
            List of normalized findings
        """
        findings: list[StaticFinding] = []

        try:
            if tool_name == "eslint":
                data = json.loads(stdout) if stdout else []
                for file_result in data:
                    for msg in file_result.get("messages", []):
                        finding = self._normalize_finding(
                            tool=tool_name,
                            file=file_result.get("filePath", ""),
                            line=msg.get("line"),
                            code=msg.get("ruleId", "UNKNOWN"),
                            message=msg.get("message", ""),
                            severity=self._map_eslint_severity(msg.get("severity", 1)),
                            category="style",
                        )
                        findings.append(finding)

            elif tool_name == "npm_audit":
                data = json.loads(stdout) if stdout else {}
                for vuln_name, vuln_data in data.get("vulnerabilities", {}).items():
                    via = vuln_data.get("via", [])
                    message = (
                        via[0].get("title", "Vulnerability found")
                        if isinstance(via, list) and via
                        else "Vulnerability found"
                    )
                    finding = self._normalize_finding(
                        tool=tool_name,
                        file="package.json",
                        line=None,
                        code=vuln_name,
                        message=message,
                        severity=self._map_npm_severity(vuln_data.get("severity", "low")),
                        category="security",
                    )
                    findings.append(finding)

        except json.JSONDecodeError as e:
            self.logger.error("json_parse_error", tool=tool_name, error=str(e))
        except Exception as e:
            self.logger.error("parse_error", tool=tool_name, error=str(e))

        return findings

    def _parse_go_tool_output(
        self, tool_name: str, stdout: str, stderr: str
    ) -> list[StaticFinding]:
        """Parse Go tool output into normalized findings.

        Args:
            tool_name: Name of the tool
            stdout: Standard output from tool
            stderr: Standard error from tool

        Returns:
            List of normalized findings
        """
        findings: list[StaticFinding] = []

        try:
            output = stderr if stderr else stdout

            for line in output.split("\n"):
                if not line.strip():
                    continue

                parts = line.split(":", 3)
                if len(parts) >= 3:
                    finding = self._normalize_finding(
                        tool=tool_name,
                        file=parts[0],
                        line=int(parts[1]) if parts[1].isdigit() else None,
                        code=tool_name.upper(),
                        message=parts[-1].strip() if len(parts) > 3 else line,
                        severity=Severity.MEDIUM,
                        category="style",
                    )
                    findings.append(finding)

        except Exception as e:
            self.logger.error("parse_error", tool=tool_name, error=str(e))

        return findings

    def _parse_rust_tool_output(
        self, tool_name: str, stdout: str, stderr: str
    ) -> list[StaticFinding]:
        """Parse Rust tool output into normalized findings.

        Args:
            tool_name: Name of the tool
            stdout: Standard output from tool
            stderr: Standard error from tool

        Returns:
            List of normalized findings
        """
        findings: list[StaticFinding] = []

        try:
            if tool_name == "clippy":
                for line in stdout.split("\n"):
                    if not line.strip():
                        continue
                    try:
                        data = json.loads(line)
                        if data.get("reason") == "compiler-message":
                            msg = data.get("message", {})
                            spans = msg.get("spans", [])
                            if spans:
                                span = spans[0]
                                finding = self._normalize_finding(
                                    tool=tool_name,
                                    file=span.get("file_name", ""),
                                    line=span.get("line_start"),
                                    code=msg.get("code", {}).get("code", "UNKNOWN"),
                                    message=msg.get("message", ""),
                                    severity=self._map_rust_severity(msg.get("level", "warning")),
                                    category="style",
                                )
                                findings.append(finding)
                    except json.JSONDecodeError:
                        continue

            elif tool_name == "cargo_audit":
                data = json.loads(stdout) if stdout else {}
                for vuln in data.get("vulnerabilities", {}).get("list", []):
                    finding = self._normalize_finding(
                        tool=tool_name,
                        file="Cargo.toml",
                        line=None,
                        code=vuln.get("advisory", {}).get("id", "UNKNOWN"),
                        message=vuln.get("advisory", {}).get("title", ""),
                        severity=Severity.HIGH,
                        category="security",
                    )
                    findings.append(finding)

        except json.JSONDecodeError as e:
            self.logger.error("json_parse_error", tool=tool_name, error=str(e))
        except Exception as e:
            self.logger.error("parse_error", tool=tool_name, error=str(e))

        return findings

    def _normalize_finding(
        self,
        tool: str,
        file: str,
        line: int | None,
        code: str,
        message: str,
        severity: Severity,
        category: str,
    ) -> StaticFinding:
        """Convert tool-specific output to normalized format.

        Args:
            tool: Tool name
            file: File path
            line: Line number (optional)
            code: Error code
            message: Error message
            severity: Severity level
            category: Finding category

        Returns:
            Normalized StaticFinding
        """
        recommendation = self._generate_recommendation(category, code, message)

        return StaticFinding(
            tool=tool,
            file=file,
            line=line,
            code=code,
            message=message,
            severity=severity,
            category=category,
            recommendation=recommendation,
            verified=False,
        )

    def _validate_evidence(self, finding: StaticFinding, repo_path: str) -> None:
        """Verify file and line number exist.

        Args:
            finding: Finding to validate (modified in place)
            repo_path: Path to repository
        """
        try:
            file_path = Path(repo_path) / finding.file

            if not file_path.exists():
                finding.verified = False
                self.logger.warning(
                    "evidence_validation_failed",
                    file=finding.file,
                    reason="file_not_found",
                )
                return

            if finding.line is not None:
                with open(file_path, encoding="utf-8", errors="ignore") as f:
                    line_count = sum(1 for _ in f)

                if finding.line > line_count or finding.line < 1:
                    finding.verified = False
                    self.logger.warning(
                        "evidence_validation_failed",
                        file=finding.file,
                        line=finding.line,
                        line_count=line_count,
                        reason="invalid_line_number",
                    )
                    return

            finding.verified = True

        except Exception as e:
            finding.verified = False
            self.logger.error("evidence_validation_error", file=finding.file, error=str(e))
            self.logger.error("evidence_validation_error", file=finding.file, error=str(e))

    def _generate_recommendation(self, category: str, code: str, message: str) -> str:
        """Generate recommendation based on finding category.

        Args:
            category: Finding category
            code: Error code
            message: Error message

        Returns:
            Recommendation string
        """
        recommendations = {
            "syntax": "Fix syntax error to ensure code can be parsed correctly.",
            "import": "Verify import statement and ensure module is installed.",
            "security": "Review security vulnerability and apply recommended fix.",
            "style": "Follow code style guidelines for better readability.",
            "complexity": "Refactor to reduce complexity and improve maintainability.",
        }
        return recommendations.get(category, "Review and address this issue.")

    def _map_severity(self, code: str) -> Severity:
        """Map error code to severity level.

        Args:
            code: Error code

        Returns:
            Severity level
        """
        if code.startswith("E"):
            return Severity.HIGH
        elif code.startswith("W"):
            return Severity.MEDIUM
        return Severity.LOW

    def _map_bandit_severity(self, severity: str) -> Severity:
        """Map Bandit severity to our severity enum.

        Args:
            severity: Bandit severity string

        Returns:
            Severity level
        """
        mapping = {
            "HIGH": Severity.CRITICAL,
            "MEDIUM": Severity.HIGH,
            "LOW": Severity.MEDIUM,
        }
        return mapping.get(severity.upper(), Severity.LOW)

    def _map_eslint_severity(self, severity: int) -> Severity:
        """Map ESLint severity to our severity enum.

        Args:
            severity: ESLint severity (1=warning, 2=error)

        Returns:
            Severity level
        """
        return Severity.HIGH if severity == 2 else Severity.MEDIUM

    def _map_npm_severity(self, severity: str) -> Severity:
        """Map npm audit severity to our severity enum.

        Args:
            severity: npm severity string

        Returns:
            Severity level
        """
        mapping = {
            "critical": Severity.CRITICAL,
            "high": Severity.HIGH,
            "moderate": Severity.MEDIUM,
            "low": Severity.LOW,
        }
        return mapping.get(severity.lower(), Severity.LOW)

    def _map_rust_severity(self, level: str) -> Severity:
        """Map Rust compiler level to our severity enum.

        Args:
            level: Rust level string

        Returns:
            Severity level
        """
        mapping = {
            "error": Severity.HIGH,
            "warning": Severity.MEDIUM,
            "note": Severity.LOW,
        }
        return mapping.get(level.lower(), Severity.MEDIUM)
