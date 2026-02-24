"""Strategy detection for understanding WHY teams made technical decisions."""

import re
import time
from pathlib import Path

import structlog

from src.models.analysis import CommitInfo, RepoData, SourceFile
from src.models.strategy import (
    LearningJourney,
    MaturityLevel,
    StrategyAnalysisResult,
    TestStrategy,
    Tradeoff,
)
from src.models.test_execution import TestExecutionResult

logger = structlog.get_logger()


class StrategyDetector:
    """Detects strategic thinking behind technical decisions.
    
    Analyzes test strategy, architecture decisions, and learning patterns
    to understand the reasoning behind technical choices, not just the "what".
    """

    def __init__(self) -> None:
        """Initialize strategy detector."""
        self.logger = logger.bind(component="strategy_detector")

    def analyze(
        self,
        repo_data: RepoData,
        test_results: TestExecutionResult | None = None,
    ) -> StrategyAnalysisResult:
        """Analyze strategic decisions in repository.
        
        Args:
            repo_data: Repository data with commits and files
            test_results: Test execution results (optional)
            
        Returns:
            StrategyAnalysisResult with strategic context
        """
        start_time = time.time()
        
        self.logger.info(
            "strategy_analysis_started",
            repo_url=repo_data.repo_url,
            has_test_results=test_results is not None,
        )

        # Analyze test strategy (now returns strategy and metrics)
        test_strategy, test_metrics = self._analyze_test_strategy(
            repo_data.source_files,
            test_results,
            repo_data.commit_history,
        )
        
        # Log test metrics for debugging
        self.logger.info(
            "test_strategy_metrics",
            test_strategy=test_strategy.value,
            test_to_code_ratio=test_metrics.get('test_to_code_ratio', 0.0),
            tdd_percentage=test_metrics.get('tdd_percentage', 0.0),
        )
        
        # Detect critical path focus
        critical_path_focus = self._detect_critical_path_focus(
            repo_data.source_files,
        )
        
        # Detect architecture tradeoffs
        tradeoffs = self._detect_architecture_tradeoffs(repo_data)
        
        # Detect learning journey
        learning_journey = self._detect_learning_journey(
            repo_data.commit_history,
            repo_data.source_files,
        )
        
        # Classify maturity level
        maturity_level = self._classify_maturity(
            test_strategy,
            tradeoffs,
            learning_journey,
            repo_data,
        )
        
        # Generate strategic context
        strategic_context = self._generate_strategic_context(
            test_strategy,
            critical_path_focus,
            tradeoffs,
            learning_journey,
            maturity_level,
        )
        
        duration_ms = int((time.time() - start_time) * 1000)
        
        self.logger.info(
            "strategy_analysis_completed",
            test_strategy=test_strategy.value,
            critical_path_focus=critical_path_focus,
            maturity_level=maturity_level.value,
            duration_ms=duration_ms,
        )
        
        return StrategyAnalysisResult(
            test_strategy=test_strategy,
            critical_path_focus=critical_path_focus,
            tradeoffs=tradeoffs,
            learning_journey=learning_journey,
            maturity_level=maturity_level,
            strategic_context=strategic_context,
            duration_ms=duration_ms,
        )

    def _analyze_test_strategy(
        self,
        source_files: list[SourceFile],
        test_results: TestExecutionResult | None,
        commit_history: list[CommitInfo],
    ) -> tuple[TestStrategy, dict[str, float]]:
        """Classify test strategy based on test type distribution.
        
        Analyzes:
        - Test file patterns (unit vs integration vs e2e)
        - Test-to-code ratio
        - TDD patterns (tests committed before implementation)
        
        Args:
            source_files: Repository source files
            test_results: Test execution results
            commit_history: Git commit history
            
        Returns:
            Tuple of (TestStrategy classification, metrics dict)
            Metrics include: test_to_code_ratio, tdd_percentage, unit_pct, integration_pct, e2e_pct
        """
        # Find test files and production files
        test_files = [
            f for f in source_files
            if self._is_test_file(f.path)
        ]
        
        production_files = [
            f for f in source_files
            if not self._is_test_file(f.path) and self._is_code_file(f.path)
        ]
        
        # Calculate test-to-code ratio
        test_lines = sum(f.lines for f in test_files)
        production_lines = sum(f.lines for f in production_files)
        test_to_code_ratio = test_lines / production_lines if production_lines > 0 else 0.0
        
        # Detect TDD patterns from commit history
        tdd_percentage = self._detect_tdd_patterns(commit_history, test_files, production_files)
        
        if not test_files:
            # Check if there's polished UI but no tests (demo-first strategy)
            has_ui = any(
                f.path.endswith(('.html', '.css', '.jsx', '.tsx', '.vue', '.svelte'))
                for f in production_files
            )
            if has_ui and production_lines > 500:
                return TestStrategy.DEMO_FIRST, {
                    'test_to_code_ratio': 0.0,
                    'tdd_percentage': 0.0,
                    'unit_pct': 0.0,
                    'integration_pct': 0.0,
                    'e2e_pct': 0.0,
                }
            return TestStrategy.NO_TESTS, {
                'test_to_code_ratio': 0.0,
                'tdd_percentage': 0.0,
                'unit_pct': 0.0,
                'integration_pct': 0.0,
                'e2e_pct': 0.0,
            }
        
        # Count test types by file path patterns
        unit_tests = 0
        integration_tests = 0
        e2e_tests = 0
        
        for test_file in test_files:
            path_lower = test_file.path.lower()
            
            # E2E tests
            if any(keyword in path_lower for keyword in [
                'e2e', 'end-to-end', 'selenium', 'cypress', 'playwright',
                'integration/e2e', 'tests/e2e', 'test/e2e'
            ]):
                e2e_tests += 1
            # Integration tests
            elif any(keyword in path_lower for keyword in [
                'integration', 'api_test', 'api/test', 'tests/integration',
                'test/integration', 'functional'
            ]):
                integration_tests += 1
            # Unit tests (default)
            else:
                unit_tests += 1
        
        total_tests = unit_tests + integration_tests + e2e_tests
        
        if total_tests == 0:
            return TestStrategy.NO_TESTS, {
                'test_to_code_ratio': test_to_code_ratio,
                'tdd_percentage': tdd_percentage,
                'unit_pct': 0.0,
                'integration_pct': 0.0,
                'e2e_pct': 0.0,
            }
        
        # Calculate percentages
        unit_pct = unit_tests / total_tests
        integration_pct = integration_tests / total_tests
        e2e_pct = e2e_tests / total_tests
        
        metrics = {
            'test_to_code_ratio': test_to_code_ratio,
            'tdd_percentage': tdd_percentage,
            'unit_pct': unit_pct,
            'integration_pct': integration_pct,
            'e2e_pct': e2e_pct,
        }
        
        # Classify strategy
        if e2e_pct > 0.5:
            return TestStrategy.E2E_FOCUSED, metrics
        elif integration_pct > 0.5:
            return TestStrategy.INTEGRATION_FOCUSED, metrics
        elif unit_pct > 0.7:
            return TestStrategy.UNIT_FOCUSED, metrics
        else:
            # Mixed strategy - check for critical path focus
            if self._detect_critical_path_focus([f for f in source_files if self._is_test_file(f.path)]):
                return TestStrategy.CRITICAL_PATH, metrics
            return TestStrategy.UNIT_FOCUSED, metrics


    def _is_test_file(self, path: str) -> bool:
        """Check if file is a test file.
        
        Args:
            path: File path
            
        Returns:
            True if test file
        """
        path_lower = path.lower()
        return any([
            'test' in path_lower,
            'spec' in path_lower,
            path_lower.endswith('_test.py'),
            path_lower.endswith('_test.js'),
            path_lower.endswith('_test.ts'),
            path_lower.endswith('.test.js'),
            path_lower.endswith('.test.ts'),
            path_lower.endswith('.spec.js'),
            path_lower.endswith('.spec.ts'),
        ])
    def _is_code_file(self, path: str) -> bool:
        """Check if file is a production code file (not config, docs, etc).

        Args:
            path: File path

        Returns:
            True if production code file
        """
        # Code file extensions
        code_extensions = (
            '.py', '.js', '.ts', '.jsx', '.tsx', '.go', '.rs',
            '.java', '.cpp', '.c', '.h', '.hpp', '.cs', '.rb',
            '.php', '.swift', '.kt', '.scala', '.r', '.m', '.mm'
        )

        # Exclude patterns
        exclude_patterns = [
            'node_modules/', 'venv/', 'env/', '.venv/', '__pycache__/',
            'dist/', 'build/', '.git/', 'vendor/', 'target/',
            'package-lock.json', 'yarn.lock', 'Pipfile.lock',
            'README', 'LICENSE', 'CHANGELOG', '.md', '.txt',
            '.json', '.yaml', '.yml', '.toml', '.ini', '.cfg',
            '.xml', '.html', '.css', '.scss', '.sass', '.less'
        ]

        path_lower = path.lower()

        # Check if it's a code file
        if not any(path_lower.endswith(ext) for ext in code_extensions):
            return False

        # Check if it matches exclude patterns
        if any(pattern in path_lower for pattern in exclude_patterns):
            return False

        return True

    def _detect_tdd_patterns(
        self,
        commit_history: list[CommitInfo],
        test_files: list[SourceFile],
        production_files: list[SourceFile],
    ) -> float:
        """Detect TDD patterns by analyzing commit order.

        TDD pattern: Tests are committed before or alongside implementation.
        We look for commits that add test files before adding production files.

        Args:
            commit_history: Git commit history (newest first)
            test_files: Test files in repository
            production_files: Production code files in repository

        Returns:
            Percentage of test files that appear to follow TDD (0.0-1.0)
        """
        if not test_files or not commit_history:
            return 0.0

        # Build a map of file paths to their first commit (earliest appearance)
        # Commits are newest first, so we iterate in reverse
        file_first_commit: dict[str, CommitInfo] = {}

        for commit in reversed(commit_history):
            # We don't have file-level commit data in CommitInfo
            # This is a simplified heuristic based on commit messages
            message_lower = commit.message.lower()

            # Look for TDD indicators in commit messages
            tdd_indicators = [
                'test', 'tdd', 'spec', 'failing test', 'red-green',
                'write test', 'add test', 'test first'
            ]

            impl_indicators = [
                'implement', 'add feature', 'feature:', 'fix', 'bugfix',
                'add function', 'add method', 'add class'
            ]

            # Count commits with TDD patterns
            has_tdd_indicator = any(indicator in message_lower for indicator in tdd_indicators)
            has_impl_indicator = any(indicator in message_lower for indicator in impl_indicators)

            if has_tdd_indicator and not has_impl_indicator:
                # This commit appears to be test-focused
                file_first_commit[commit.hash] = commit

        # Calculate TDD percentage based on commit message patterns
        # This is a heuristic - true TDD detection would require file-level commit analysis
        tdd_commits = len(file_first_commit)
        total_commits = len(commit_history)

        if total_commits == 0:
            return 0.0

        # Return percentage of commits that appear to follow TDD
        tdd_percentage = min(tdd_commits / total_commits, 1.0)

        return tdd_percentage


    def _detect_critical_path_focus(
        self,
        source_files: list[SourceFile],
    ) -> bool:
        """Check if tests focus on critical paths.
        
        Args:
            source_files: Repository source files
            
        Returns:
            True if critical path focus detected
        """
        test_files = [f for f in source_files if self._is_test_file(f.path)]
        
        if not test_files:
            return False
        
        # Critical path keywords
        critical_keywords = [
            'auth', 'login', 'payment', 'checkout', 'order',
            'transaction', 'security', 'admin', 'user',
        ]
        
        critical_test_count = 0
        
        for test_file in test_files:
            path_lower = test_file.path.lower()
            content_lower = test_file.content.lower()
            
            # Check if test file focuses on critical paths
            if any(keyword in path_lower or keyword in content_lower 
                   for keyword in critical_keywords):
                critical_test_count += 1
        
        # If >50% of tests focus on critical paths
        return critical_test_count / len(test_files) > 0.5

    def _detect_architecture_decisions(
        self,
        repo_data: RepoData,
    ) -> tuple[str, list[str], list[Tradeoff]]:
        """Identify architecture decisions from directory structure and code organization.
        
        Analyzes:
        - Monolith vs microservices architecture
        - Design patterns (MVC, layered, hexagonal, etc.)
        - Trade-offs (speed vs quality, simplicity vs scalability)
        
        Args:
            repo_data: Repository data
            
        Returns:
            Tuple of (architecture_type, design_patterns, tradeoffs)
        """
        source_files = repo_data.source_files
        
        # Detect architecture type
        architecture_type = self._detect_architecture_type(source_files)
        
        # Detect design patterns
        design_patterns = self._detect_design_patterns(source_files)
        
        # Detect tradeoffs
        tradeoffs = self._detect_architecture_tradeoffs_internal(
            source_files,
            architecture_type,
            design_patterns,
        )
        
        return architecture_type, design_patterns, tradeoffs

    def _detect_architecture_type(self, source_files: list[SourceFile]) -> str:
        """Detect if architecture is monolith or microservices.
        
        Indicators:
        - Microservices: Multiple service directories, docker-compose with multiple services,
          API gateway patterns, service mesh configs
        - Monolith: Single application directory, unified codebase
        
        Args:
            source_files: Repository source files
            
        Returns:
            Architecture type: "monolith", "microservices", or "modular_monolith"
        """
        # Check for microservices indicators
        service_dirs = set()
        has_docker_compose = False
        has_api_gateway = False
        has_service_mesh = False
        
        for source_file in source_files:
            path_lower = source_file.path.lower()
            
            # Check for service directories (services/, microservices/, apps/)
            if any(pattern in path_lower for pattern in ['services/', 'microservices/', 'apps/']):
                # Extract service name
                parts = path_lower.split('/')
                for i, part in enumerate(parts):
                    if part in ['services', 'microservices', 'apps'] and i + 1 < len(parts):
                        service_dirs.add(parts[i + 1])
            
            # Check for docker-compose
            if 'docker-compose' in path_lower:
                has_docker_compose = True
                # Check if multiple services defined
                if 'services:' in source_file.content.lower():
                    service_count = source_file.content.lower().count('image:') + \
                                  source_file.content.lower().count('build:')
                    if service_count > 2:  # More than 2 services = microservices
                        service_dirs.add('docker-services')
            
            # Check for API gateway patterns
            if any(pattern in path_lower for pattern in ['gateway', 'api-gateway', 'proxy']):
                has_api_gateway = True
            
            # Check for service mesh (Istio, Linkerd, Consul)
            if any(pattern in path_lower for pattern in ['istio', 'linkerd', 'consul', 'envoy']):
                has_service_mesh = True
        
        # Classify architecture
        if len(service_dirs) >= 3 or has_service_mesh:
            return "microservices"
        elif len(service_dirs) >= 2 or (has_docker_compose and has_api_gateway):
            return "modular_monolith"
        else:
            return "monolith"

    def _detect_design_patterns(self, source_files: list[SourceFile]) -> list[str]:
        """Detect design patterns from code organization.
        
        Patterns detected:
        - MVC (Model-View-Controller)
        - Layered Architecture (presentation, business, data layers)
        - Repository Pattern
        - Service Layer Pattern
        - Hexagonal/Clean Architecture
        - CQRS (Command Query Responsibility Segregation)
        
        Args:
            source_files: Repository source files
            
        Returns:
            List of detected design patterns
        """
        patterns = []
        
        # Track directory structure
        has_models = False
        has_views = False
        has_controllers = False
        has_services = False
        has_repositories = False
        has_handlers = False
        has_commands = False
        has_queries = False
        has_domain = False
        has_infrastructure = False
        has_application = False
        
        for source_file in source_files:
            path_lower = source_file.path.lower()
            
            # Check for MVC components
            if any(pattern in path_lower for pattern in ['models/', 'model/', 'entities/']):
                has_models = True
            if any(pattern in path_lower for pattern in ['views/', 'view/', 'templates/']):
                has_views = True
            if any(pattern in path_lower for pattern in ['controllers/', 'controller/']):
                has_controllers = True
            
            # Check for layered architecture
            if any(pattern in path_lower for pattern in ['services/', 'service/']):
                has_services = True
            if any(pattern in path_lower for pattern in ['repositories/', 'repository/', 'repos/']):
                has_repositories = True
            if any(pattern in path_lower for pattern in ['handlers/', 'handler/']):
                has_handlers = True
            
            # Check for CQRS
            if any(pattern in path_lower for pattern in ['commands/', 'command/']):
                has_commands = True
            if any(pattern in path_lower for pattern in ['queries/', 'query/']):
                has_queries = True
            
            # Check for hexagonal/clean architecture
            if any(pattern in path_lower for pattern in ['domain/', 'core/']):
                has_domain = True
            if any(pattern in path_lower for pattern in ['infrastructure/', 'adapters/']):
                has_infrastructure = True
            if any(pattern in path_lower for pattern in ['application/', 'use-cases/', 'usecases/']):
                has_application = True
        
        # Identify patterns
        if has_models and has_views and has_controllers:
            patterns.append("MVC (Model-View-Controller)")
        
        if has_services and has_repositories:
            patterns.append("Service Layer + Repository Pattern")
        elif has_services:
            patterns.append("Service Layer Pattern")
        elif has_repositories:
            patterns.append("Repository Pattern")
        
        if has_commands and has_queries:
            patterns.append("CQRS (Command Query Responsibility Segregation)")
        
        if has_domain and has_infrastructure and has_application:
            patterns.append("Hexagonal/Clean Architecture")
        elif has_domain and (has_infrastructure or has_application):
            patterns.append("Domain-Driven Design (DDD)")
        
        if has_handlers and not has_controllers:
            patterns.append("Handler Pattern (Event-Driven)")
        
        if not patterns:
            patterns.append("Simple/Flat Structure")
        
        return patterns

    def _detect_architecture_tradeoffs_internal(
        self,
        source_files: list[SourceFile],
        architecture_type: str,
        design_patterns: list[str],
    ) -> list[Tradeoff]:
        """Identify architecture trade-offs based on detected patterns.
        
        Args:
            source_files: Repository source files
            architecture_type: Detected architecture type
            design_patterns: Detected design patterns
            
        Returns:
            List of detected tradeoffs
        """
        tradeoffs: list[Tradeoff] = []
        
        # Check for speed vs security tradeoff
        has_security_issues = self._has_security_patterns(source_files)
        has_fast_implementation = self._has_fast_implementation_patterns(source_files)
        
        if has_security_issues and has_fast_implementation:
            tradeoffs.append(Tradeoff(
                tradeoff_type="speed_vs_security",
                decision="Chose speed over security",
                rationale="For hackathon demo, prioritized getting features working quickly over implementing full security measures",
                impact_on_score="Acceptable for hackathon context - security can be added post-demo",
            ))
        
        # Check for simplicity vs scalability tradeoff
        has_simple_architecture = self._has_simple_architecture(source_files)
        has_scalability_concerns = self._has_scalability_concerns(source_files)
        
        if has_simple_architecture and not has_scalability_concerns:
            tradeoffs.append(Tradeoff(
                tradeoff_type="simplicity_vs_scalability",
                decision="Chose simplicity over scalability",
                rationale="Focused on working demo with simple architecture rather than over-engineering for scale",
                impact_on_score="Smart prioritization for hackathon - avoid premature optimization",
            ))
        
        # Check for over-engineering tradeoff
        if architecture_type == "microservices" and len(source_files) < 100:
            tradeoffs.append(Tradeoff(
                tradeoff_type="simplicity_vs_complexity",
                decision="Chose microservices for small codebase",
                rationale="May be over-engineered for hackathon scope - microservices add complexity",
                impact_on_score="Consider if added complexity is justified by requirements",
            ))
        
        # Check for pattern over-use
        if len(design_patterns) > 3 and len(source_files) < 50:
            tradeoffs.append(Tradeoff(
                tradeoff_type="simplicity_vs_patterns",
                decision="Applied multiple design patterns to small codebase",
                rationale="May indicate over-engineering or strong architectural discipline",
                impact_on_score="Evaluate if patterns add value or just complexity",
            ))
        
        # Check for quality vs speed tradeoff
        has_tests = any(self._is_test_file(f.path) for f in source_files)
        has_documentation = any('readme' in f.path.lower() for f in source_files)
        
        if not has_tests and not has_documentation and len(source_files) > 20:
            tradeoffs.append(Tradeoff(
                tradeoff_type="speed_vs_quality",
                decision="Chose speed over quality practices",
                rationale="Skipped tests and documentation to ship features faster",
                impact_on_score="Acceptable for hackathon, but limits production readiness",
            ))
        
        return tradeoffs

    def _detect_architecture_tradeoffs(
        self,
        repo_data: RepoData,
    ) -> list[Tradeoff]:
        """Identify architecture trade-offs (wrapper for backward compatibility).
        
        Args:
            repo_data: Repository data
            
        Returns:
            List of detected tradeoffs
        """
        architecture_type, design_patterns, tradeoffs = self._detect_architecture_decisions(repo_data)
        return tradeoffs

    def _has_security_patterns(self, source_files: list[SourceFile]) -> bool:
        """Check for security vulnerability patterns.
        
        Args:
            source_files: Repository source files
            
        Returns:
            True if security issues detected
        """
        security_patterns = [
            r'password\s*=\s*["\']',  # Hardcoded passwords
            r'api[_-]?key\s*=\s*["\']',  # Hardcoded API keys
            r'eval\(',  # Eval usage
            r'exec\(',  # Exec usage
        ]
        
        for source_file in source_files:
            for pattern in security_patterns:
                if re.search(pattern, source_file.content, re.IGNORECASE):
                    return True
        
        return False

    def _has_fast_implementation_patterns(self, source_files: list[SourceFile]) -> bool:
        """Check for fast implementation patterns.
        
        Args:
            source_files: Repository source files
            
        Returns:
            True if fast implementation detected
        """
        # Check for rapid development indicators
        for source_file in source_files:
            content_lower = source_file.content.lower()
            
            # Quick and dirty patterns
            if any(keyword in content_lower for keyword in [
                'todo', 'fixme', 'hack', 'quick fix', 'temporary',
            ]):
                return True
        
        return False

    def _has_simple_architecture(self, source_files: list[SourceFile]) -> bool:
        """Check for simple architecture patterns.
        
        Args:
            source_files: Repository source files
            
        Returns:
            True if simple architecture detected
        """
        # Count files - simple architecture has fewer files
        return len(source_files) < 50

    def _has_scalability_concerns(self, source_files: list[SourceFile]) -> bool:
        """Check for scalability patterns.
        
        Args:
            source_files: Repository source files
            
        Returns:
            True if scalability patterns detected
        """
        scalability_keywords = [
            'cache', 'redis', 'queue', 'worker', 'async',
            'microservice', 'load balancer', 'horizontal scaling',
        ]
        
        for source_file in source_files:
            content_lower = source_file.content.lower()
            if any(keyword in content_lower for keyword in scalability_keywords):
                return True
        
        return False

    def _detect_learning_journey(
        self,
        commits: list[CommitInfo],
        source_files: list[SourceFile],
    ) -> LearningJourney | None:
        """Detect if team learned new technology during hackathon.
        
        Args:
            commits: Commit history
            source_files: Repository source files
            
        Returns:
            LearningJourney if detected, None otherwise
        """
        # Learning keywords in commit messages
        learning_keywords = [
            'first', 'learning', 'trying', 'attempt', 'figuring out',
            'new to', 'never used', 'experimenting',
        ]
        
        learning_commits = []
        
        for commit in commits:
            message_lower = commit.message.lower()
            if any(keyword in message_lower for keyword in learning_keywords):
                learning_commits.append(commit.message)
        
        if not learning_commits:
            return None
        
        # Detect technology being learned
        technology = self._detect_new_technology(source_files, commits)
        
        if not technology:
            return None
        
        # Analyze progression
        progression = self._analyze_learning_progression(learning_commits)
        
        # Determine if impressive
        impressive = len(learning_commits) >= 3 and "advanced" in progression.lower()
        
        return LearningJourney(
            technology=technology,
            evidence=learning_commits[:5],  # Top 5 commits
            progression=progression,
            impressive=impressive,
        )

    def _detect_new_technology(
        self,
        source_files: list[SourceFile],
        commits: list[CommitInfo],
    ) -> str | None:
        """Detect new technology being learned.
        
        Args:
            source_files: Repository source files
            commit: Commit history
            
        Returns:
            Technology name if detected
        """
        # Common frameworks/technologies
        technologies = {
            'react': ['react', 'jsx', 'tsx'],
            'vue': ['vue', '.vue'],
            'angular': ['angular', '@angular'],
            'django': ['django', 'manage.py'],
            'flask': ['flask', 'app.py'],
            'fastapi': ['fastapi', 'main.py'],
            'docker': ['dockerfile', 'docker-compose'],
            'kubernetes': ['k8s', 'kubernetes', 'deployment.yaml'],
            'graphql': ['graphql', '.graphql'],
            'typescript': ['.ts', '.tsx'],
        }
        
        for tech_name, patterns in technologies.items():
            for source_file in source_files:
                path_lower = source_file.path.lower()
                content_lower = source_file.content.lower()
                
                if any(pattern in path_lower or pattern in content_lower 
                       for pattern in patterns):
                    return tech_name
        
        return None

    def _analyze_learning_progression(self, commits: list[CommitInfo]) -> str:
        """Analyze learning progression from commits.

        Enhanced to track:
        - Code quality improvements over time
        - Refactoring patterns
        - Skill progression indicators

        Args:
            commits: Full commit history for progression analysis

        Returns:
            Progression description with quality and refactoring insights
        """
        # Extract learning commits
        learning_keywords = [
            'first', 'learning', 'trying', 'attempt', 'figuring out',
            'new to', 'never used', 'experimenting',
        ]

        learning_commits = []
        for commit in commits:
            message_lower = commit.message.lower()
            if any(keyword in message_lower for keyword in learning_keywords):
                learning_commits.append(commit.message)

        if len(learning_commits) == 0:
            # No explicit learning indicators, check for implicit progression
            if len(commits) > 10:
                return self._analyze_implicit_progression(commits)
            return "Initial exploration phase"

        # Analyze code quality improvements
        quality_improvements = self._detect_quality_improvements(commits)

        # Detect refactoring patterns
        refactoring_patterns = self._detect_refactoring_patterns(commits)

        # Build progression description
        progression_parts = []

        # Base progression by commit count
        if len(learning_commits) <= 2:
            progression_parts.append("Initial exploration phase")
        elif len(learning_commits) <= 5:
            progression_parts.append("Active learning with steady progress")
        else:
            progression_parts.append("Advanced learning with significant skill development")

        # Add quality improvement insights
        if quality_improvements:
            progression_parts.append(f"Demonstrated {len(quality_improvements)} code quality improvement(s)")

        # Add refactoring insights
        if refactoring_patterns:
            progression_parts.append(f"Applied {len(refactoring_patterns)} refactoring pattern(s)")

        # Skill progression indicators
        skill_indicators = self._identify_skill_progression(commits, quality_improvements, refactoring_patterns)
        if skill_indicators:
            progression_parts.append(skill_indicators)

        return ". ".join(progression_parts)

    def _detect_quality_improvements(self, commits: list[CommitInfo]) -> list[str]:
        """Detect code quality improvements over time from commit messages.

        Looks for commits that indicate quality improvements:
        - Adding tests after initial implementation
        - Adding error handling
        - Improving documentation
        - Adding validation
        - Performance optimizations

        Args:
            commits: Commit history (newest first)

        Returns:
            List of quality improvement descriptions
        """
        quality_patterns = {
            'testing': [
                r'add.*test', r'write.*test', r'test.*coverage',
                r'unit.*test', r'integration.*test', r'fix.*test'
            ],
            'error_handling': [
                r'add.*error', r'handle.*error', r'error.*handling',
                r'try.*catch', r'exception.*handling', r'validate'
            ],
            'documentation': [
                r'add.*doc', r'update.*doc', r'improve.*doc',
                r'add.*comment', r'document', r'readme'
            ],
            'validation': [
                r'add.*validation', r'validate.*input', r'sanitize',
                r'check.*input', r'input.*validation'
            ],
            'performance': [
                r'optimize', r'performance', r'speed.*up',
                r'improve.*speed', r'cache', r'efficient'
            ],
            'refactor': [
                r'refactor', r'clean.*up', r'improve.*code',
                r'simplify', r'restructure'
            ],
        }

        improvements = []

        for category, patterns in quality_patterns.items():
            for commit in commits:
                message_lower = commit.message.lower()
                for pattern in patterns:
                    if re.search(pattern, message_lower):
                        improvements.append(category)
                        break  # Only count once per category
                if category in improvements:
                    break  # Move to next category

        return improvements

    def _detect_refactoring_patterns(self, commits: list[CommitInfo]) -> list[str]:
        """Detect refactoring patterns from commit messages.

        Refactoring patterns indicate code maturity and quality awareness:
        - Extract method/function
        - Rename for clarity
        - Remove duplication (DRY principle)
        - Simplify complex logic
        - Improve code organization

        Args:
            commits: Commit history

        Returns:
            List of detected refactoring patterns
        """
        refactoring_keywords = {
            'extract': r'extract.*(?:method|function|class|component)',
            'rename': r'rename.*(?:for|to).*(?:clarity|readability|consistency)',
            'dry': r'(?:remove|eliminate).*(?:duplication|duplicate|redundan)',
            'simplify': r'simplify.*(?:logic|code|implementation)',
            'reorganize': r'(?:reorganize|restructure|move).*(?:code|files|modules)',
            'decompose': r'(?:break|split|decompose).*(?:into|to).*(?:smaller|separate)',
            'consolidate': r'consolidate.*(?:logic|code|functions)',
        }

        detected_patterns = []

        for pattern_name, pattern_regex in refactoring_keywords.items():
            for commit in commits:
                message_lower = commit.message.lower()
                if re.search(pattern_regex, message_lower):
                    detected_patterns.append(pattern_name)
                    break  # Only count once per pattern type

        return detected_patterns

    def _identify_skill_progression(
        self,
        commits: list[CommitInfo],
        quality_improvements: list[str],
        refactoring_patterns: list[str],
    ) -> str:
        """Identify skill progression indicators from commit patterns.

        Analyzes the combination of quality improvements and refactoring
        to determine skill progression level.

        Args:
            commits: Commit history
            quality_improvements: Detected quality improvements
            refactoring_patterns: Detected refactoring patterns

        Returns:
            Skill progression description or empty string
        """
        # Calculate progression score
        progression_score = 0

        # Quality improvements contribute to score
        progression_score += len(quality_improvements)

        # Refactoring patterns indicate higher skill level
        progression_score += len(refactoring_patterns) * 2

        # Check for advanced patterns in commit messages
        advanced_keywords = [
            'architecture', 'design pattern', 'solid principles',
            'dependency injection', 'separation of concerns',
            'single responsibility', 'interface', 'abstraction'
        ]

        for commit in commits:
            message_lower = commit.message.lower()
            if any(keyword in message_lower for keyword in advanced_keywords):
                progression_score += 3
                break

        # Classify skill progression
        if progression_score >= 10:
            return "Shows senior-level progression with architectural thinking"
        elif progression_score >= 6:
            return "Shows mid-level progression with quality awareness"
        elif progression_score >= 3:
            return "Shows junior-to-mid progression with improving practices"
        elif progression_score > 0:
            return "Shows early-stage skill development"

        return ""

    def _analyze_implicit_progression(self, commits: list[CommitInfo]) -> str:
        """Analyze implicit skill progression when no explicit learning keywords found.

        Looks at commit patterns over time to detect improvement even without
        explicit "learning" language.

        Args:
            commits: Commit history (newest first)

        Returns:
            Progression description
        """
        if len(commits) < 10:
            return "Limited commit history for progression analysis"

        # Split commits into early and late phases
        mid_point = len(commits) // 2
        early_commits = commits[mid_point:]  # Older commits
        late_commits = commits[:mid_point]   # Newer commits

        # Analyze commit message quality improvement
        early_quality = self._calculate_commit_message_quality(early_commits)
        late_quality = self._calculate_commit_message_quality(late_commits)

        quality_improvement = late_quality - early_quality

        # Check for quality improvements in later commits
        late_quality_improvements = self._detect_quality_improvements(late_commits)

        # Build progression description
        if quality_improvement > 0.2 or len(late_quality_improvements) >= 2:
            return "Shows implicit skill progression with improving commit quality and practices"
        elif quality_improvement > 0.1 or len(late_quality_improvements) >= 1:
            return "Shows gradual improvement in development practices"
        else:
            return "Consistent development approach throughout project"

    def _calculate_commit_message_quality(self, commits: list[CommitInfo]) -> float:
        """Calculate commit message quality score.

        Quality indicators:
        - Length > 10 characters
        - Contains context (what and why)
        - Not generic ("fix", "update", "wip")
        - Proper capitalization

        Args:
            commits: List of commits to analyze

        Returns:
            Quality score between 0.0 and 1.0
        """
        if not commits:
            return 0.0

        quality_score = 0
        generic_patterns = [r'^fix$', r'^update$', r'^wip$', r'^changes$', r'^stuff$']

        for commit in commits:
            message = commit.message.strip()
            score = 0

            # Length check
            if len(message) > 10:
                score += 0.25

            # Not generic
            is_generic = any(re.match(pattern, message.lower()) for pattern in generic_patterns)
            if not is_generic:
                score += 0.25

            # Contains context (has multiple words)
            if len(message.split()) >= 3:
                score += 0.25

            # Proper capitalization
            if message[0].isupper():
                score += 0.25

            quality_score += score

        return quality_score / len(commits)

    def _classify_maturity(
        self,
        test_strategy: TestStrategy,
        tradeoffs: list[Tradeoff],
        learning_journey: LearningJourney | None,
        repo_data: RepoData,
    ) -> MaturityLevel:
        """Classify team maturity level.
        
        Args:
            test_strategy: Test strategy classification
            tradeoffs: Detected tradeoffs
            learning_journey: Learning journey if detected
            repo_data: Repository data
            
        Returns:
            MaturityLevel classification
        """
        maturity_score = 0
        
        # Test strategy scoring
        if test_strategy == TestStrategy.CRITICAL_PATH:
            maturity_score += 3  # Senior thinking
        elif test_strategy in [TestStrategy.INTEGRATION_FOCUSED, TestStrategy.E2E_FOCUSED]:
            maturity_score += 2  # Mid-level thinking
        elif test_strategy == TestStrategy.UNIT_FOCUSED:
            maturity_score += 1  # Junior thinking
        
        # Tradeoff awareness
        if len(tradeoffs) > 0:
            maturity_score += 2  # Aware of tradeoffs = senior
        
        # Learning journey
        if learning_journey and learning_journey.impressive:
            maturity_score += 1  # Growth mindset
        
        # CI/CD sophistication
        if len(repo_data.workflow_definitions) > 0:
            maturity_score += 1
        
        # Documentation quality
        if repo_data.readme_content and len(repo_data.readme_content) > 500:
            maturity_score += 1
        
        # Classify based on score
        if maturity_score >= 6:
            return MaturityLevel.SENIOR
        elif maturity_score >= 3:
            return MaturityLevel.MID
        else:
            return MaturityLevel.JUNIOR

    def _detect_context_awareness(
        self,
        repo_data: RepoData,
    ) -> dict[str, bool]:
        """Detect context awareness through documentation quality.

        Checks for:
        - README with problem statement
        - Architecture diagrams
        - API documentation

        Args:
            repo_data: Repository data

        Returns:
            Dictionary with context awareness indicators:
            - has_problem_statement: README contains problem/challenge description
            - has_architecture_diagram: Architecture diagrams present
            - has_api_docs: API documentation present
        """
        result = {
            'has_problem_statement': False,
            'has_architecture_diagram': False,
            'has_api_docs': False,
        }

        # Check README for problem statement
        if repo_data.readme_content:
            readme_lower = repo_data.readme_content.lower()

            # Problem statement indicators
            problem_keywords = [
                'problem', 'challenge', 'issue', 'motivation',
                'why we built', 'inspiration', 'background',
                'the need', 'pain point', 'objective', 'goal'
            ]

            # Check if README has a problem statement section
            has_problem_section = any(
                keyword in readme_lower for keyword in problem_keywords
            )

            # Check for structured problem description (headers + content)
            problem_headers = [
                '## problem', '## challenge', '## motivation',
                '## inspiration', '## background', '## objective',
                '# problem', '# challenge', '# motivation'
            ]

            has_problem_header = any(
                header in readme_lower for header in problem_headers
            )

            # Problem statement detected if keywords present or dedicated section
            result['has_problem_statement'] = has_problem_section or has_problem_header

        # Check for architecture diagrams
        diagram_extensions = ['.png', '.jpg', '.jpeg', '.svg', '.gif', '.drawio', '.mermaid']
        diagram_keywords = ['architecture', 'diagram', 'design', 'flow', 'schema']

        for source_file in repo_data.source_files:
            path_lower = source_file.path.lower()

            # Check for diagram files with architecture-related names
            if any(ext in path_lower for ext in diagram_extensions):
                if any(keyword in path_lower for keyword in diagram_keywords):
                    result['has_architecture_diagram'] = True
                    break

            # Check for mermaid diagrams in markdown files
            if path_lower.endswith('.md'):
                if '```mermaid' in source_file.content.lower():
                    result['has_architecture_diagram'] = True
                    break

        # Check for API documentation
        api_doc_patterns = [
            'api.md', 'api_docs', 'api-docs', 'api_documentation',
            'swagger', 'openapi', 'postman', 'api_reference',
            'endpoints.md', 'routes.md'
        ]

        for source_file in repo_data.source_files:
            path_lower = source_file.path.lower()

            # Check for dedicated API documentation files
            if any(pattern in path_lower for pattern in api_doc_patterns):
                result['has_api_docs'] = True
                break

            # Check for OpenAPI/Swagger specs
            if path_lower.endswith(('.yaml', '.yml', '.json')):
                content_lower = source_file.content.lower()
                if 'openapi' in content_lower or 'swagger' in content_lower:
                    result['has_api_docs'] = True
                    break

        # Also check README for API documentation section
        if not result['has_api_docs'] and repo_data.readme_content:
            readme_lower = repo_data.readme_content.lower()
            api_headers = [
                '## api', '## endpoints', '## routes', '## api reference',
                '## api documentation', '# api', '# endpoints'
            ]

            if any(header in readme_lower for header in api_headers):
                # Verify it's not just a header but has actual content
                # Look for HTTP methods or endpoint patterns
                http_methods = ['get ', 'post ', 'put ', 'delete ', 'patch ']
                endpoint_patterns = ['/api/', 'endpoint:', 'route:']

                has_api_content = any(
                    method in readme_lower for method in http_methods
                ) or any(
                    pattern in readme_lower for pattern in endpoint_patterns
                )

                if has_api_content:
                    result['has_api_docs'] = True

        self.logger.info(
            "context_awareness_detected",
            has_problem_statement=result['has_problem_statement'],
            has_architecture_diagram=result['has_architecture_diagram'],
            has_api_docs=result['has_api_docs'],
        )

        return result

    def _generate_strategic_context(
        self,
        test_strategy: TestStrategy,
        critical_path_focus: bool,
        tradeoffs: list[Tradeoff],
        learning_journey: LearningJourney | None,
        maturity_level: MaturityLevel,
    ) -> str:
        """Generate strategic context for scoring.

        Args:
            test_strategy: Test strategy classification
            critical_path_focus: Critical path focus detected
            tradeoffs: Detected tradeoffs
            learning_journey: Learning journey if detected
            maturity_level: Maturity level classification

        Returns:
            Strategic context description
        """
        context_parts = []

        # Test strategy context
        if test_strategy == TestStrategy.CRITICAL_PATH:
            context_parts.append(
                "Team demonstrates senior-level thinking by focusing tests on critical paths "
                "(authentication, payments, core business logic) rather than achieving high "
                "coverage on trivial code."
            )
        elif test_strategy == TestStrategy.INTEGRATION_FOCUSED:
            context_parts.append(
                "Team prioritized integration tests over unit tests, showing product-focused "
                "thinking - they want to ensure the system works end-to-end."
            )
        elif test_strategy == TestStrategy.DEMO_FIRST:
            context_parts.append(
                "Team chose a demo-first strategy with minimal testing, prioritizing "
                "visible features over test coverage - acceptable for hackathon context."
            )

        # Tradeoff context
        if tradeoffs:
            context_parts.append(
                f"Team made {len(tradeoffs)} conscious architecture tradeoff(s), "
                "showing awareness of constraints and priorities."
            )

        # Learning journey context
        if learning_journey:
            context_parts.append(
                f"Team learned {learning_journey.technology} during the hackathon, "
                f"demonstrating growth mindset and adaptability. {learning_journey.progression}"
            )

        # Maturity context
        context_parts.append(
            f"Overall maturity level: {maturity_level.value.upper()}. "
            f"{'Production-ready thinking with strategic prioritization.' if maturity_level == MaturityLevel.SENIOR else ''}"
            f"{'Solid fundamentals with room for strategic improvement.' if maturity_level == MaturityLevel.MID else ''}"
            f"{'Tutorial-following approach, needs more experience with strategic thinking.' if maturity_level == MaturityLevel.JUNIOR else ''}"
        )

        return " ".join(context_parts)

