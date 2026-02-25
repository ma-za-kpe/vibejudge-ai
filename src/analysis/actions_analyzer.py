"""GitHub Actions workflow analysis."""

from src.utils.github_client import GitHubClient
from src.utils.logging import get_logger

logger = get_logger(__name__)


class ActionsAnalyzer:
    """Analyze GitHub Actions workflows and runs."""

    def __init__(self, github_token: str | None = None):
        """Initialize Actions analyzer.

        Args:
            github_token: GitHub personal access token (optional)
        """
        self.client = GitHubClient(token=github_token)

    def analyze(self, owner: str, repo: str) -> dict:
        """Analyze GitHub Actions for a repository.

        Args:
            owner: Repository owner
            repo: Repository name

        Returns:
            Dict with workflow_runs, workflow_definitions, and disqualification info:
            {
                "workflow_runs": list,
                "workflow_definitions": list,
                "disqualified": bool,
                "disqualification_reason": str | None
            }
        """
        logger.info("actions_analysis_started", owner=owner, repo=repo)

        # Fetch workflow runs
        workflow_runs = self.client.fetch_workflow_runs(owner, repo, max_runs=50)

        # Fetch workflow definition files
        workflow_definitions = self.client.fetch_workflow_files(owner, repo)

        # Check for disqualification: no CI/CD workflows
        disqualified = False
        disqualification_reason = None

        if not workflow_runs and not workflow_definitions:
            disqualified = True
            disqualification_reason = (
                "No GitHub Actions workflows found. CI/CD is required for hackathon participation."
            )
            logger.warning(
                "repository_disqualified",
                owner=owner,
                repo=repo,
                reason=disqualification_reason,
            )

        logger.info(
            "actions_analysis_complete",
            owner=owner,
            repo=repo,
            runs=len(workflow_runs),
            definitions=len(workflow_definitions),
            disqualified=disqualified,
        )

        return {
            "workflow_runs": workflow_runs,
            "workflow_definitions": workflow_definitions,
            "disqualified": disqualified,
            "disqualification_reason": disqualification_reason,
        }

    def _fetch_workflow_logs(self, owner: str, repo: str, max_runs: int = 5) -> list[dict]:
        """Fetch logs for most recent workflow runs.

        Args:
            owner: Repository owner
            repo: Repository name
            max_runs: Maximum number of runs to fetch logs for (default: 5)

        Returns:
            List of dicts with run metadata and log content:
            [
                {
                    "run_id": int,
                    "name": str,
                    "status": str,
                    "conclusion": str | None,
                    "created_at": datetime,
                    "log_content": str,
                },
                ...
            ]
        """

        logger.info(
            "fetching_workflow_logs",
            owner=owner,
            repo=repo,
            max_runs=max_runs,
        )

        # First, get the most recent workflow runs
        workflow_runs = self.client.fetch_workflow_runs(owner, repo, max_runs=max_runs)

        if not workflow_runs:
            logger.info("no_workflow_runs_found", owner=owner, repo=repo)
            return []

        logs_with_metadata = []

        for run in workflow_runs[:max_runs]:
            log_content = self._fetch_single_run_logs(
                owner=owner,
                repo=repo,
                run_id=run.run_id,
                run_name=run.name,
            )

            if log_content:
                logs_with_metadata.append(
                    {
                        "run_id": run.run_id,
                        "name": run.name,
                        "status": run.status,
                        "conclusion": run.conclusion,
                        "created_at": run.created_at,
                        "log_content": log_content,
                    }
                )

        logger.info(
            "workflow_logs_fetched",
            owner=owner,
            repo=repo,
            requested=max_runs,
            fetched=len(logs_with_metadata),
        )

        return logs_with_metadata

    def _fetch_single_run_logs(
        self,
        owner: str,
        repo: str,
        run_id: int,
        run_name: str,
        max_retries: int = 3,
    ) -> str | None:
        """Fetch logs for a single workflow run with exponential backoff.

        Args:
            owner: Repository owner
            repo: Repository name
            run_id: Workflow run ID
            run_name: Workflow run name (for logging)
            max_retries: Maximum number of retry attempts

        Returns:
            Log content as string, or None if fetch failed
        """
        import time

        import httpx

        url = f"/repos/{owner}/{repo}/actions/runs/{run_id}/logs"

        for attempt in range(max_retries):
            try:
                # GitHub returns logs as a zip file
                resp = self.client.client.get(url, follow_redirects=True)

                # Handle rate limiting
                if resp.status_code == 403:
                    rate_limit_remaining = resp.headers.get("X-RateLimit-Remaining", "0")
                    if rate_limit_remaining == "0":
                        # Calculate backoff: 2^attempt seconds
                        backoff_seconds = 2**attempt
                        logger.warning(
                            "github_rate_limit_hit",
                            owner=owner,
                            repo=repo,
                            run_id=run_id,
                            attempt=attempt + 1,
                            backoff_seconds=backoff_seconds,
                        )
                        time.sleep(backoff_seconds)
                        continue

                # Handle not found (logs may be expired or unavailable)
                if resp.status_code == 404:
                    logger.info(
                        "workflow_logs_not_found",
                        owner=owner,
                        repo=repo,
                        run_id=run_id,
                        run_name=run_name,
                    )
                    return None

                resp.raise_for_status()

                # Extract logs from zip file
                log_content = self._extract_logs_from_zip(resp.content)

                logger.info(
                    "workflow_log_fetched",
                    owner=owner,
                    repo=repo,
                    run_id=run_id,
                    run_name=run_name,
                    log_size=len(log_content),
                )

                return log_content

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 403:
                    # Rate limit - retry with backoff
                    backoff_seconds = 2**attempt
                    logger.warning(
                        "github_rate_limit_retry",
                        owner=owner,
                        repo=repo,
                        run_id=run_id,
                        attempt=attempt + 1,
                        backoff_seconds=backoff_seconds,
                    )
                    time.sleep(backoff_seconds)
                    continue
                else:
                    logger.warning(
                        "workflow_log_fetch_failed",
                        owner=owner,
                        repo=repo,
                        run_id=run_id,
                        status_code=e.response.status_code,
                        error=str(e),
                    )
                    return None

            except Exception as e:
                logger.warning(
                    "workflow_log_fetch_error",
                    owner=owner,
                    repo=repo,
                    run_id=run_id,
                    attempt=attempt + 1,
                    error=str(e),
                )

                if attempt < max_retries - 1:
                    backoff_seconds = 2**attempt
                    time.sleep(backoff_seconds)
                    continue
                else:
                    return None

        logger.error(
            "workflow_log_fetch_exhausted",
            owner=owner,
            repo=repo,
            run_id=run_id,
            max_retries=max_retries,
        )
        return None

    def _extract_logs_from_zip(self, zip_content: bytes) -> str:
        """Extract and concatenate all log files from GitHub Actions log zip.

        Args:
            zip_content: Raw zip file bytes from GitHub API

        Returns:
            Concatenated log content as string
        """
        import io
        import zipfile

        try:
            with zipfile.ZipFile(io.BytesIO(zip_content)) as zip_file:
                log_parts = []

                for file_name in sorted(zip_file.namelist()):
                    if file_name.endswith(".txt"):
                        try:
                            content = zip_file.read(file_name).decode("utf-8", errors="ignore")
                            log_parts.append(f"=== {file_name} ===\n{content}\n")
                        except Exception as e:
                            logger.warning(
                                "log_file_extraction_failed",
                                file_name=file_name,
                                error=str(e),
                            )
                            continue

                return "\n".join(log_parts)

        except zipfile.BadZipFile as e:
            logger.error("invalid_zip_file", error=str(e))
            return ""
        except Exception as e:
            logger.error("log_extraction_failed", error=str(e))
            return ""

    def close(self) -> None:
        """Close the GitHub client."""
        self.client.close()

    def _parse_linter_output(
        self, log_content: str, repo_files: set[str] | None = None
    ) -> list[dict]:
        """Parse linter output from CI/CD logs.

        Detects and parses multiple linter formats:
        - Flake8: file.py:line:col: CODE message
        - ESLint: file.js:line:col: message (rule-name)
        - Bandit: >> Issue: [severity] message\\n   Location: file.py:line

        Args:
            log_content: Raw log content from workflow run
            repo_files: Set of valid file paths in repository (for validation)

        Returns:
            List of normalized findings as dicts with fields:
            - tool: str (flake8, eslint, bandit)
            - file: str
            - line: int | None
            - code: str (error code)
            - message: str
            - severity: str (critical, high, medium, low, info)
            - category: str (syntax, import, security, style, complexity)
            - recommendation: str
            - verified: bool (whether file path exists in repo)
        """
        import re

        findings = []

        # Split log into lines for parsing
        lines = log_content.split("\n")

        # Pattern 1: Flake8 format - file.py:line:col: CODE message
        # Example: src/api/main.py:42:80: E501 line too long (82 > 79 characters)
        flake8_pattern = re.compile(r"^([^:]+):(\d+):(\d+):\s+([A-Z]\d+)\s+(.+)$")

        # Pattern 2: ESLint format - file.js:line:col: message (rule-name)
        # Example: src/utils/helper.js:15:3: 'foo' is assigned a value but never used (no-unused-vars)
        eslint_pattern = re.compile(r"^([^:]+):(\d+):(\d+):\s+(.+?)\s+\(([^)]+)\)$")

        # Pattern 3: Bandit format - >> Issue: [severity] message
        #                            Location: file.py:line
        # Example:
        # >> Issue: [B201:flask_debug_true] A Flask app appears to be run with debug=True
        #    Severity: High   Confidence: High
        #    Location: src/app.py:10
        bandit_issue_pattern = re.compile(r"^>>\s+Issue:\s+\[([^\]]+)\]\s+(.+)$")
        bandit_location_pattern = re.compile(r"^\s+Location:\s+([^:]+):(\d+)$")

        i = 0
        while i < len(lines):
            line = lines[i].strip()

            # Try Flake8 pattern
            flake8_match = flake8_pattern.match(line)
            if flake8_match:
                file_path = flake8_match.group(1).strip()
                line_num = int(flake8_match.group(2))
                code = flake8_match.group(4)
                message = flake8_match.group(5)

                finding = self._normalize_flake8_finding(
                    file_path=file_path,
                    line_num=line_num,
                    code=code,
                    message=message,
                    repo_files=repo_files,
                )
                findings.append(finding)
                i += 1
                continue

            # Try ESLint pattern
            eslint_match = eslint_pattern.match(line)
            if eslint_match:
                file_path = eslint_match.group(1).strip()
                line_num = int(eslint_match.group(2))
                message = eslint_match.group(4)
                rule_name = eslint_match.group(5)

                finding = self._normalize_eslint_finding(
                    file_path=file_path,
                    line_num=line_num,
                    message=message,
                    rule_name=rule_name,
                    repo_files=repo_files,
                )
                findings.append(finding)
                i += 1
                continue

            # Try Bandit pattern (multi-line)
            bandit_match = bandit_issue_pattern.match(line)
            if bandit_match:
                code = bandit_match.group(1)
                message = bandit_match.group(2)

                # Look ahead for Location line (within next 5 lines)
                location_found = False
                for j in range(i + 1, min(i + 6, len(lines))):
                    location_match = bandit_location_pattern.match(lines[j])
                    if location_match:
                        file_path = location_match.group(1).strip()
                        line_num = int(location_match.group(2))

                        finding = self._normalize_bandit_finding(
                            file_path=file_path,
                            line_num=line_num,
                            code=code,
                            message=message,
                            repo_files=repo_files,
                        )
                        findings.append(finding)
                        location_found = True
                        i = j + 1
                        break

                if not location_found:
                    # Bandit issue without location - skip
                    i += 1
                continue

            i += 1

        logger.info(
            "linter_output_parsed",
            total_findings=len(findings),
            flake8_count=sum(1 for f in findings if f["tool"] == "flake8"),
            eslint_count=sum(1 for f in findings if f["tool"] == "eslint"),
            bandit_count=sum(1 for f in findings if f["tool"] == "bandit"),
        )

        return findings

    def _normalize_flake8_finding(
        self,
        file_path: str,
        line_num: int,
        code: str,
        message: str,
        repo_files: set[str] | None,
    ) -> dict:
        """Normalize Flake8 finding to standard format.

        Args:
            file_path: File path from Flake8 output
            line_num: Line number
            code: Flake8 error code (e.g., E501, W503)
            message: Error message
            repo_files: Set of valid file paths for validation

        Returns:
            Normalized finding dict
        """
        # Map Flake8 codes to severity and category
        severity = "low"
        category = "style"

        # E9xx, F8xx = syntax errors (critical)
        if code.startswith("E9") or code.startswith("F8"):
            severity = "critical"
            category = "syntax"
        # F4xx, F6xx, F7xx = import errors (high)
        elif code.startswith("F4") or code.startswith("F6") or code.startswith("F7"):
            severity = "high"
            category = "import"
        # F = PyFlakes errors (medium)
        elif code.startswith("F"):
            severity = "medium"
            category = "syntax"
        # E = PEP8 errors (low)
        elif code.startswith("E"):
            severity = "low"
            category = "style"
        # W = PEP8 warnings (info)
        elif code.startswith("W"):
            severity = "info"
            category = "style"
        # C = complexity (medium)
        elif code.startswith("C"):
            severity = "medium"
            category = "complexity"

        # Validate file path
        verified = False
        if repo_files is not None:
            verified = file_path in repo_files

        return {
            "tool": "flake8",
            "file": file_path,
            "line": line_num,
            "code": code,
            "message": message,
            "severity": severity,
            "category": category,
            "recommendation": self._generate_recommendation(category, code, message),
            "verified": verified,
        }

    def _normalize_eslint_finding(
        self,
        file_path: str,
        line_num: int,
        message: str,
        rule_name: str,
        repo_files: set[str] | None,
    ) -> dict:
        """Normalize ESLint finding to standard format.

        Args:
            file_path: File path from ESLint output
            line_num: Line number
            message: Error message
            rule_name: ESLint rule name (e.g., no-unused-vars)
            repo_files: Set of valid file paths for validation

        Returns:
            Normalized finding dict
        """
        # Map ESLint rules to severity and category
        severity = "low"
        category = "style"

        # Security rules (high)
        security_rules = {
            "no-eval",
            "no-implied-eval",
            "no-new-func",
            "no-script-url",
            "no-unsafe-innerhtml",
        }
        if rule_name in security_rules:
            severity = "high"
            category = "security"

        # Import/module rules (medium)
        import_rules = {
            "import/no-unresolved",
            "import/named",
            "import/default",
            "import/namespace",
            "no-undef",
        }
        if rule_name in import_rules:
            severity = "medium"
            category = "import"

        # Syntax/error rules (critical)
        syntax_rules = {"no-unreachable", "no-dupe-keys", "no-duplicate-case"}
        if rule_name in syntax_rules:
            severity = "critical"
            category = "syntax"

        # Complexity rules (medium)
        complexity_rules = {"complexity", "max-depth", "max-nested-callbacks"}
        if rule_name in complexity_rules:
            severity = "medium"
            category = "complexity"

        # Validate file path
        verified = False
        if repo_files is not None:
            verified = file_path in repo_files

        return {
            "tool": "eslint",
            "file": file_path,
            "line": line_num,
            "code": rule_name,
            "message": message,
            "severity": severity,
            "category": category,
            "recommendation": self._generate_recommendation(category, rule_name, message),
            "verified": verified,
        }

    def _normalize_bandit_finding(
        self,
        file_path: str,
        line_num: int,
        code: str,
        message: str,
        repo_files: set[str] | None,
    ) -> dict:
        """Normalize Bandit finding to standard format.

        Args:
            file_path: File path from Bandit output
            line_num: Line number
            code: Bandit issue code (e.g., B201:flask_debug_true)
            message: Issue description
            repo_files: Set of valid file paths for validation

        Returns:
            Normalized finding dict
        """
        # Bandit findings are always security-related
        category = "security"

        # Extract severity from code if present
        # Bandit codes often include severity hints
        severity = "high"  # Default for security issues

        # Map common Bandit codes to severity
        critical_codes = {
            "B201",  # flask_debug_true
            "B301",  # pickle
            "B302",  # marshal
            "B303",  # md5
            "B304",  # insecure_cipher
            "B305",  # insecure_cipher_mode
            "B306",  # mktemp_q
            "B307",  # eval
            "B308",  # mark_safe
            "B309",  # httpsconnection
            "B310",  # urllib_urlopen
            "B311",  # random
            "B312",  # telnetlib
            "B313",  # xml_bad_cElementTree
            "B314",  # xml_bad_ElementTree
            "B315",  # xml_bad_expatreader
            "B316",  # xml_bad_expatbuilder
            "B317",  # xml_bad_sax
            "B318",  # xml_bad_minidom
            "B319",  # xml_bad_pulldom
            "B320",  # xml_bad_etree
            "B601",  # paramiko_calls
            "B602",  # shell_injection
            "B603",  # subprocess_without_shell_equals_true
            "B604",  # any_other_function_with_shell_equals_true
            "B605",  # start_process_with_a_shell
            "B606",  # start_process_with_no_shell
            "B607",  # start_process_with_partial_path
        }

        # Extract code number (e.g., B201 from B201:flask_debug_true)
        code_num = code.split(":")[0] if ":" in code else code

        if code_num in critical_codes:
            severity = "critical"

        # Validate file path
        verified = False
        if repo_files is not None:
            verified = file_path in repo_files

        return {
            "tool": "bandit",
            "file": file_path,
            "line": line_num,
            "code": code,
            "message": message,
            "severity": severity,
            "category": category,
            "recommendation": self._generate_recommendation(category, code, message),
            "verified": verified,
        }

    def _generate_recommendation(self, category: str, code: str, message: str) -> str:
        """Generate actionable recommendation based on finding.

        Args:
            category: Finding category (syntax, import, security, style, complexity)
            code: Error/rule code
            message: Error message

        Returns:
            Actionable recommendation string
        """
        # Category-based recommendations
        recommendations = {
            "syntax": "Fix syntax error to ensure code can execute properly.",
            "import": "Resolve import issue to ensure all dependencies are available.",
            "security": "Address security vulnerability to protect against potential attacks.",
            "style": "Improve code style for better readability and maintainability.",
            "complexity": "Reduce code complexity by refactoring into smaller functions.",
        }

        base_recommendation = recommendations.get(category, "Review and address this issue.")

        # Add specific guidance for common issues
        if "unused" in message.lower():
            return f"{base_recommendation} Remove unused code to reduce clutter."
        elif "undefined" in message.lower() or "not defined" in message.lower():
            return f"{base_recommendation} Ensure all variables and imports are properly defined."
        elif "too long" in message.lower():
            return f"{base_recommendation} Break long lines into multiple lines."
        elif "debug" in message.lower():
            return f"{base_recommendation} Disable debug mode in production."

        return base_recommendation

    def _parse_test_output(self, log_content: str) -> dict | None:
        """Parse test output from CI/CD logs.

        Detects and parses multiple test framework formats:
        - pytest: PASSED, FAILED, ERROR, SKIPPED counts
        - Jest: Tests: X passed, Y failed, Z total
        - go test: PASS, FAIL with test names

        Args:
            log_content: Raw log content from workflow run

        Returns:
            Dict with test results matching TestExecutionResult structure:
            {
                "framework": str,
                "total_tests": int,
                "passed_tests": int,
                "failed_tests": int,
                "skipped_tests": int,
                "failing_tests": list[dict],
            }
            Returns None if no test output detected.
        """
        import re

        # Pattern 1: pytest summary format
        # Example: ===== 42 passed, 3 failed, 1 skipped in 5.23s =====
        # Example: ===== 10 passed in 2.15s =====
        pytest_pattern = re.compile(
            r"=+\s*(?:(\d+)\s+passed)?(?:,\s*(\d+)\s+failed)?(?:,\s*(\d+)\s+error)?(?:,\s*(\d+)\s+skipped)?.*?in\s+[\d.]+s\s*=+"
        )

        # Pattern 2: Jest summary format
        # Example: Tests: 5 passed, 2 failed, 7 total
        # Example: Tests: 10 passed, 10 total
        jest_pattern = re.compile(
            r"Tests:\s*(?:(\d+)\s+passed)?(?:,\s*(\d+)\s+failed)?(?:,\s*(\d+)\s+skipped)?(?:,\s*)?(\d+)\s+total"
        )

        # Pattern 3: go test summary format
        # Example: PASS
        # Example: FAIL
        # Example: ok  	github.com/user/repo	0.123s
        # Example: FAIL	github.com/user/repo	0.456s
        go_test_ok_pattern = re.compile(r"^ok\s+[\w./]+\s+[\d.]+s", re.MULTILINE)
        go_test_fail_pattern = re.compile(r"^FAIL\s+[\w./]+\s+[\d.]+s", re.MULTILINE)
        go_test_pass_pattern = re.compile(r"^PASS$", re.MULTILINE)

        # Try pytest pattern
        pytest_match = pytest_pattern.search(log_content)
        if pytest_match:
            passed = int(pytest_match.group(1) or 0)
            failed = int(pytest_match.group(2) or 0)
            error = int(pytest_match.group(3) or 0)
            skipped = int(pytest_match.group(4) or 0)

            # Combine failed and error counts
            failed_total = failed + error
            total = passed + failed_total + skipped

            # Extract failing test names
            failing_tests = self._extract_pytest_failures(log_content)

            logger.info(
                "pytest_output_detected",
                total=total,
                passed=passed,
                failed=failed_total,
                skipped=skipped,
            )

            return {
                "framework": "pytest",
                "total_tests": total,
                "passed_tests": passed,
                "failed_tests": failed_total,
                "skipped_tests": skipped,
                "failing_tests": failing_tests,
            }

        # Try Jest pattern
        jest_match = jest_pattern.search(log_content)
        if jest_match:
            passed = int(jest_match.group(1) or 0)
            failed = int(jest_match.group(2) or 0)
            skipped = int(jest_match.group(3) or 0)
            total = int(jest_match.group(4))

            # Extract failing test names
            failing_tests = self._extract_jest_failures(log_content)

            logger.info(
                "jest_output_detected",
                total=total,
                passed=passed,
                failed=failed,
                skipped=skipped,
            )

            return {
                "framework": "jest",
                "total_tests": total,
                "passed_tests": passed,
                "failed_tests": failed,
                "skipped_tests": skipped,
                "failing_tests": failing_tests,
            }

        # Try go test pattern
        go_ok_matches = go_test_ok_pattern.findall(log_content)
        go_fail_matches = go_test_fail_pattern.findall(log_content)
        go_pass_matches = go_test_pass_pattern.findall(log_content)

        if go_ok_matches or go_fail_matches or go_pass_matches:
            # Count packages that passed/failed
            passed = len(go_ok_matches) + len(go_pass_matches)
            failed = len(go_fail_matches)
            total = passed + failed

            # Extract failing test names
            failing_tests = self._extract_go_test_failures(log_content)

            logger.info(
                "go_test_output_detected",
                total=total,
                passed=passed,
                failed=failed,
            )

            return {
                "framework": "go_test",
                "total_tests": total,
                "passed_tests": passed,
                "failed_tests": failed,
                "skipped_tests": 0,
                "failing_tests": failing_tests,
            }

        # No test output detected
        logger.debug("no_test_output_detected")
        return None

    def _extract_pytest_failures(self, log_content: str) -> list[dict]:
        """Extract failing test names and error messages from pytest output.

        Args:
            log_content: Raw log content

        Returns:
            List of dicts with name, error_message, file, line
        """
        import re

        failing_tests = []

        # Pattern: FAILED tests/test_file.py::test_name - AssertionError: message
        # Pattern: ERROR tests/test_file.py::test_name - ImportError: message
        failure_pattern = re.compile(
            r"^(FAILED|ERROR)\s+([^:]+)::([^\s]+)\s*-\s*(.+)$", re.MULTILINE
        )

        for match in failure_pattern.finditer(log_content):
            match.group(1)
            file_path = match.group(2)
            test_name = match.group(3)
            error_message = match.group(4).strip()

            failing_tests.append(
                {
                    "name": f"{file_path}::{test_name}",
                    "error_message": error_message,
                    "file": file_path,
                    "line": None,
                }
            )

        return failing_tests

    def _extract_jest_failures(self, log_content: str) -> list[dict]:
        """Extract failing test names and error messages from Jest output.

        Args:
            log_content: Raw log content

        Returns:
            List of dicts with name, error_message, file, line
        """
        import re

        failing_tests = []

        # Pattern: ● Test suite name › test name
        #          Error message
        # Pattern: FAIL src/test.js
        #          ● test name
        failure_pattern = re.compile(r"●\s+(.+?)\s+›\s+(.+?)$", re.MULTILINE)

        # Also look for file paths with FAIL
        file_pattern = re.compile(r"FAIL\s+([^\s]+\.(?:js|ts|jsx|tsx))")

        current_file = None
        for line in log_content.split("\n"):
            # Track current test file
            file_match = file_pattern.search(line)
            if file_match:
                current_file = file_match.group(1)

            # Extract test failures
            failure_match = failure_pattern.search(line)
            if failure_match:
                suite_name = failure_match.group(1).strip()
                test_name = failure_match.group(2).strip()

                failing_tests.append(
                    {
                        "name": f"{suite_name} › {test_name}",
                        "error_message": "Test failed (see logs for details)",
                        "file": current_file or "unknown",
                        "line": None,
                    }
                )

        return failing_tests

    def _extract_go_test_failures(self, log_content: str) -> list[dict]:
        """Extract failing test names and error messages from go test output.

        Args:
            log_content: Raw log content

        Returns:
            List of dicts with name, error_message, file, line
        """
        import re

        failing_tests = []

        # Pattern: --- FAIL: TestName (0.00s)
        #              file.go:123: error message
        failure_pattern = re.compile(r"---\s+FAIL:\s+(\w+)\s+\([\d.]+s\)", re.MULTILINE)

        # Pattern for error location: file.go:123: message
        error_location_pattern = re.compile(r"^\s+([^:]+):(\d+):\s+(.+)$", re.MULTILINE)

        lines = log_content.split("\n")
        i = 0

        while i < len(lines):
            line = lines[i]

            # Look for FAIL marker
            failure_match = failure_pattern.search(line)
            if failure_match:
                test_name = failure_match.group(1)

                # Look ahead for error location (within next 10 lines)
                error_message = "Test failed"
                file_path = "unknown"
                line_num = None

                for j in range(i + 1, min(i + 11, len(lines))):
                    error_match = error_location_pattern.search(lines[j])
                    if error_match:
                        file_path = error_match.group(1).strip()
                        line_num = int(error_match.group(2))
                        error_message = error_match.group(3).strip()
                        break

                failing_tests.append(
                    {
                        "name": test_name,
                        "error_message": error_message,
                        "file": file_path,
                        "line": line_num,
                    }
                )

            i += 1

        return failing_tests

    def _parse_coverage_output(self, log_content: str) -> dict[str, float]:
        """Parse coverage output from CI/CD logs.

        Detects and parses multiple coverage formats:
        - coverage.py: TOTAL X%
        - Istanbul/nyc: All files | X% | Y% | Z%
        - Per-file coverage if available

        Args:
            log_content: Raw log content from workflow run

        Returns:
            Dict mapping file paths to coverage percentages:
            {
                "src/api/main.py": 85.5,
                "src/utils/helper.py": 92.3,
                "TOTAL": 88.7,
            }
            Returns empty dict if no coverage output detected.
        """
        import re

        coverage_by_file = {}

        # Pattern 1: coverage.py total format
        # Example: TOTAL                                      1234    123     90%
        # Example: TOTAL                                                      85%
        coverage_py_total_pattern = re.compile(
            r"^TOTAL\s+(?:\d+\s+\d+\s+)?(\d+(?:\.\d+)?)%", re.MULTILINE
        )

        # Pattern 2: coverage.py per-file format
        # Example: src/api/main.py                            100     10     90%
        coverage_py_file_pattern = re.compile(
            r"^([^\s]+\.py)\s+(?:\d+\s+\d+\s+)?(\d+(?:\.\d+)?)%", re.MULTILINE
        )

        # Pattern 3: Istanbul/nyc summary format
        # Example: All files      |   85.5 |    92.3 |   78.9 |   85.5 |
        # Columns: Statements | Branches | Functions | Lines
        istanbul_total_pattern = re.compile(
            r"All files\s+\|\s+(\d+(?:\.\d+)?)\s+\|\s+(\d+(?:\.\d+)?)\s+\|\s+(\d+(?:\.\d+)?)\s+\|\s+(\d+(?:\.\d+)?)"
        )

        # Pattern 4: Istanbul/nyc per-file format
        # Example: src/utils/helper.js |   92.5 |    88.0 |   95.0 |   92.5 |
        istanbul_file_pattern = re.compile(
            r"^([^\s|]+\.(?:js|ts|jsx|tsx))\s+\|\s+(\d+(?:\.\d+)?)\s+\|\s+(\d+(?:\.\d+)?)\s+\|\s+(\d+(?:\.\d+)?)\s+\|\s+(\d+(?:\.\d+)?)",
            re.MULTILINE,
        )

        # Pattern 5: Go coverage format
        # Example: coverage: 85.5% of statements
        go_coverage_pattern = re.compile(r"coverage:\s+(\d+(?:\.\d+)?)%\s+of\s+statements")

        # Pattern 6: SimpleCov (Ruby) format
        # Example: 85.5% covered
        simplecov_pattern = re.compile(r"(\d+(?:\.\d+)?)%\s+covered")

        # Try coverage.py patterns
        coverage_py_total_match = coverage_py_total_pattern.search(log_content)
        if coverage_py_total_match:
            total_coverage = float(coverage_py_total_match.group(1))
            coverage_by_file["TOTAL"] = total_coverage

            # Extract per-file coverage
            for match in coverage_py_file_pattern.finditer(log_content):
                file_path = match.group(1)
                file_coverage = float(match.group(2))
                coverage_by_file[file_path] = file_coverage

            logger.info(
                "coverage_py_detected",
                total_coverage=total_coverage,
                files_with_coverage=len(coverage_by_file) - 1,  # Exclude TOTAL
            )
            return coverage_by_file

        # Try Istanbul/nyc patterns
        istanbul_total_match = istanbul_total_pattern.search(log_content)
        if istanbul_total_match:
            # Use line coverage (4th column) as the primary metric
            line_coverage = float(istanbul_total_match.group(4))
            coverage_by_file["TOTAL"] = line_coverage

            # Extract per-file coverage
            for match in istanbul_file_pattern.finditer(log_content):
                file_path = match.group(1)
                # Use line coverage (5th column) for per-file
                file_coverage = float(match.group(5))
                coverage_by_file[file_path] = file_coverage

            logger.info(
                "istanbul_coverage_detected",
                total_coverage=line_coverage,
                files_with_coverage=len(coverage_by_file) - 1,  # Exclude TOTAL
            )
            return coverage_by_file

        # Try Go coverage pattern
        go_coverage_match = go_coverage_pattern.search(log_content)
        if go_coverage_match:
            total_coverage = float(go_coverage_match.group(1))
            coverage_by_file["TOTAL"] = total_coverage

            logger.info(
                "go_coverage_detected",
                total_coverage=total_coverage,
            )
            return coverage_by_file

        # Try SimpleCov pattern
        simplecov_match = simplecov_pattern.search(log_content)
        if simplecov_match:
            total_coverage = float(simplecov_match.group(1))
            coverage_by_file["TOTAL"] = total_coverage

            logger.info(
                "simplecov_coverage_detected",
                total_coverage=total_coverage,
            )
            return coverage_by_file

        # No coverage output detected
        logger.debug("no_coverage_output_detected")
        return coverage_by_file
