"""Brand voice transformation for warm, educational feedback.

This module transforms cold technical findings into warm, educational feedback
following the pattern: Acknowledge → Explain Context → Show Fix → Explain Why → Provide Resources.
"""

import structlog

from src.models.common import Severity
from src.models.feedback import (
    ActionableFeedback,
    CodeExample,
    EffortEstimate,
    LearningResource,
)
from src.models.scores import (
    AIDetectionEvidence,
    BugHunterEvidence,
    InnovationEvidence,
    PerformanceEvidence,
)
from src.models.strategy import StrategyAnalysisResult

logger = structlog.get_logger()


class BrandVoiceTransformer:
    """Transforms technical findings into educational feedback.
    
    Responsibilities:
    - Transform cold technical findings into warm educational feedback
    - Add code examples (vulnerable vs fixed)
    - Include learning resources (documentation, tutorials)
    - Provide effort estimates and difficulty levels
    - Follow pattern: Acknowledge → Explain Context → Show Fix → Explain Why → Provide Resources
    """

    def __init__(self) -> None:
        """Initialize the brand voice transformer."""
        self.logger = logger.bind(component="brand_voice_transformer")

    def transform_findings(
        self,
        findings: list[
            BugHunterEvidence
            | PerformanceEvidence
            | InnovationEvidence
            | AIDetectionEvidence
        ],
        strategy_context: StrategyAnalysisResult | None = None,
    ) -> list[ActionableFeedback]:
        """Transform findings into actionable feedback.
        
        Args:
            findings: Raw technical findings from agents
            strategy_context: Strategic context for scoring adjustments
            
        Returns:
            List of actionable feedback items with warm tone
        """
        self.logger.info(
            "transforming_findings",
            finding_count=len(findings),
            has_strategy_context=strategy_context is not None,
        )

        actionable_feedback: list[ActionableFeedback] = []

        for finding in findings:
            try:
                if isinstance(finding, BugHunterEvidence):
                    feedback = self._transform_bug_hunter_finding(
                        finding, strategy_context
                    )
                elif isinstance(finding, PerformanceEvidence):
                    feedback = self._transform_performance_finding(
                        finding, strategy_context
                    )
                elif isinstance(finding, InnovationEvidence):
                    feedback = self._transform_innovation_finding(finding)
                elif isinstance(finding, AIDetectionEvidence):
                    feedback = self._transform_ai_detection_finding(finding)
                else:
                    self.logger.warning(
                        "unknown_finding_type", finding_type=type(finding).__name__
                    )
                    continue

                actionable_feedback.append(feedback)

            except Exception as e:
                self.logger.error(
                    "transform_finding_failed",
                    finding=finding.finding,
                    error=str(e),
                )
                continue

        self.logger.info(
            "transformation_complete",
            input_count=len(findings),
            output_count=len(actionable_feedback),
        )

        return actionable_feedback

    def _transform_bug_hunter_finding(
        self,
        finding: BugHunterEvidence,
        strategy_context: StrategyAnalysisResult | None,
    ) -> ActionableFeedback:
        """Transform BugHunter finding with warm tone.
        
        Args:
            finding: BugHunter evidence item
            strategy_context: Strategic context for adjustments
            
        Returns:
            ActionableFeedback with warm educational tone
        """
        # Generate acknowledgment
        acknowledgment = self._generate_acknowledgment(finding.category)

        # Generate context
        context = self._generate_context(finding.category, strategy_context)

        # Generate code example
        code_example = self._add_code_examples(finding)

        # Generate explanations
        why_vulnerable = self._explain_vulnerability(finding)
        why_fixed = self._explain_fix(finding)

        # Generate testing instructions
        testing_instructions = self._generate_testing_instructions(finding)

        # Generate learning resources
        learning_resources = self._generate_learning_resources(finding.category)

        # Estimate effort (must be done before priority calculation)
        effort_estimate = self._estimate_effort(finding)

        # Calculate priority considering both severity and effort
        priority = self._calculate_priority_with_effort(finding.severity, effort_estimate)

        # Explain business impact
        business_impact = self._explain_business_impact(finding)

        return ActionableFeedback(
            priority=priority,
            finding=finding.finding,
            acknowledgment=acknowledgment,
            context=context,
            code_example=code_example,
            why_vulnerable=why_vulnerable,
            why_fixed=why_fixed,
            testing_instructions=testing_instructions,
            learning_resources=learning_resources,
            effort_estimate=effort_estimate,
            business_impact=business_impact,
        )
    def _transform_tone(self, text: str) -> str:
        """Transform cold technical language into warm, encouraging language.

        Replaces negative words with positive alternatives and adds encouraging framing.

        Args:
            text: Original technical text

        Returns:
            Transformed text with warm, educational tone
        """
        # Replace negative words with positive alternatives
        replacements = {
            # Error/failure language
            "error": "opportunity to improve",
            "Error": "Opportunity to improve",
            "ERROR": "OPPORTUNITY TO IMPROVE",
            "failure": "learning moment",
            "Failure": "Learning moment",
            "FAILURE": "LEARNING MOMENT",
            "failed": "can be improved",
            "Failed": "Can be improved",
            "FAILED": "CAN BE IMPROVED",
            "bad": "can improve",
            "Bad": "Can improve",
            "BAD": "CAN IMPROVE",
            "wrong": "could be better",
            "Wrong": "Could be better",
            "WRONG": "COULD BE BETTER",
            "broken": "needs attention",
            "Broken": "Needs attention",
            "BROKEN": "NEEDS ATTENTION",

            # Blame language
            "you failed": "this can be improved",
            "You failed": "This can be improved",
            "you didn't": "consider",
            "You didn't": "Consider",
            "you forgot": "remember to",
            "You forgot": "Remember to",
            "you should have": "consider",
            "You should have": "Consider",
            "you must": "we recommend",
            "You must": "We recommend",

            # Harsh technical terms
            "vulnerable": "could be more secure",
            "Vulnerable": "Could be more secure",
            "VULNERABLE": "COULD BE MORE SECURE",
            "insecure": "could use security improvements",
            "Insecure": "Could use security improvements",
            "INSECURE": "COULD USE SECURITY IMPROVEMENTS",
            "missing": "would benefit from",
            "Missing": "Would benefit from",
            "MISSING": "WOULD BENEFIT FROM",
            "lacks": "could include",
            "Lacks": "Could include",
            "LACKS": "COULD INCLUDE",
        }

        transformed = text
        for old, new in replacements.items():
            transformed = transformed.replace(old, new)

        # Add encouraging phrases at the beginning if text starts with negative patterns
        negative_starts = [
            "This code",
            "The code",
            "Your code",
            "This implementation",
            "The implementation",
            "Your implementation",
        ]

        for negative_start in negative_starts:
            if transformed.startswith(negative_start):
                # Add encouraging prefix
                encouraging_prefixes = [
                    "Great start! ",
                    "You're on the right track! ",
                    "Nice work so far! ",
                ]
                # Use hash of text to consistently pick same prefix for same input
                prefix_idx = hash(text) % len(encouraging_prefixes)
                transformed = encouraging_prefixes[prefix_idx] + transformed
                break

        return transformed


    def _transform_performance_finding(
        self,
        finding: PerformanceEvidence,
        strategy_context: StrategyAnalysisResult | None,
    ) -> ActionableFeedback:
        """Transform Performance finding with warm tone.
        
        Args:
            finding: Performance evidence item
            strategy_context: Strategic context for adjustments
            
        Returns:
            ActionableFeedback with warm educational tone
        """
        priority = self._severity_to_priority(finding.severity)
        acknowledgment = self._generate_acknowledgment(finding.category)
        context = self._generate_context(finding.category, strategy_context)

        return ActionableFeedback(
            priority=priority,
            finding=finding.finding,
            acknowledgment=acknowledgment,
            context=context,
            code_example=None,
            why_vulnerable=f"This pattern can impact {finding.category} performance.",
            why_fixed=finding.recommendation,
            testing_instructions="Test performance under load to verify improvements.",
            learning_resources=self._generate_learning_resources(finding.category),
            effort_estimate=self._estimate_effort_from_severity(finding.severity),
            business_impact=self._explain_business_impact_performance(finding),
        )

    def _transform_innovation_finding(
        self, finding: InnovationEvidence
    ) -> ActionableFeedback:
        """Transform Innovation finding (positive feedback).
        
        Args:
            finding: Innovation evidence item
            
        Returns:
            ActionableFeedback celebrating innovation
        """
        return ActionableFeedback(
            priority=5,  # Positive findings are lower priority
            finding=finding.finding,
            acknowledgment=f"Great work on this {finding.category} aspect!",
            context=f"This shows {finding.impact} innovation in your approach.",
            code_example=None,
            why_vulnerable="N/A - This is a strength",
            why_fixed="N/A - This is a strength",
            testing_instructions="Keep building on this strength!",
            learning_resources=[],
            effort_estimate=EffortEstimate(minutes=0, difficulty="N/A"),
            business_impact=finding.detail,
        )

    def _transform_ai_detection_finding(
        self, finding: AIDetectionEvidence
    ) -> ActionableFeedback:
        """Transform AI Detection finding with neutral tone.
        
        Args:
            finding: AI Detection evidence item
            
        Returns:
            ActionableFeedback with neutral educational tone
        """
        return ActionableFeedback(
            priority=3,
            finding=finding.finding,
            acknowledgment="We noticed some interesting patterns in your development process.",
            context=f"Based on {finding.source}, we observed: {finding.detail}",
            code_example=None,
            why_vulnerable="N/A - This is observational",
            why_fixed="N/A - This is observational",
            testing_instructions="Continue developing with transparency about your process.",
            learning_resources=[],
            effort_estimate=EffortEstimate(minutes=0, difficulty="N/A"),
            business_impact=f"Signal: {finding.signal} (confidence: {finding.confidence:.0%})",
        )

    def _severity_to_priority(self, severity: Severity) -> int:
        """Convert severity to priority (1-5, 1=highest).
        
        Priority considers both severity and effort:
        - Priority 1 (Critical): High-severity issues that should be fixed first
        - Priority 2 (High): Important issues with moderate effort
        - Priority 3 (Medium): Balance of severity and effort
        - Priority 4 (Low): Minor issues or high-effort improvements
        - Priority 5 (Info): Nice-to-have improvements
        
        Args:
            severity: Finding severity
            
        Returns:
            Priority level (1-5)
        """
        severity_map = {
            Severity.CRITICAL: 1,
            Severity.HIGH: 2,
            Severity.MEDIUM: 3,
            Severity.LOW: 4,
            Severity.INFO: 5,
        }
        return severity_map.get(severity, 3)
    
    def _calculate_priority_with_effort(
        self, 
        severity: Severity, 
        effort: EffortEstimate
    ) -> int:
        """Calculate priority considering both severity and effort.
        
        Prioritization strategy:
        - Quick wins (high severity, low effort): Priority 1
        - Critical issues (critical severity): Priority 1 regardless of effort
        - High-impact moderate effort: Priority 2
        - Low-effort improvements: Priority 3-4 (do these while fixing bigger issues)
        - High-effort low-severity: Priority 4-5 (defer for later)
        
        Args:
            severity: Finding severity
            effort: Effort estimate
            
        Returns:
            Priority level (1-5) optimized for quick wins
        """
        base_priority = self._severity_to_priority(severity)
        
        # Critical severity always gets priority 1
        if severity == Severity.CRITICAL:
            return 1
        
        # Quick wins: High severity + low effort = bump up priority
        if severity == Severity.HIGH and effort.minutes <= 15:
            return 1  # Quick security/bug fixes are top priority
        
        # Medium severity + quick fix = good priority
        if severity == Severity.MEDIUM and effort.minutes <= 10:
            return 2  # Easy improvements
        
        # High effort + low severity = lower priority
        if severity in [Severity.LOW, Severity.INFO] and effort.minutes >= 60:
            return 5  # Defer major refactoring of minor issues
        
        # High effort + medium severity = slightly lower priority
        if severity == Severity.MEDIUM and effort.minutes >= 120:
            return 4  # Defer time-consuming moderate issues
        
        return base_priority

    def _generate_acknowledgment(self, category: str) -> str:
        """Generate warm acknowledgment based on category.
        
        Args:
            category: Finding category
            
        Returns:
            Warm acknowledgment message
        """
        acknowledgments = {
            "security": "Great start on building your application! Security is often overlooked in hackathons.",
            "bug": "You've built something functional, which is the hardest part!",
            "code_smell": "Your code works, which is the most important thing in a hackathon.",
            "testing": "You've made progress on your project - that's what matters most!",
            "architecture": "You've created a working system, which shows good problem-solving.",
            "database": "Your data layer is functional, which is a solid foundation.",
            "api": "Your API is serving requests, which is the core functionality.",
            "scalability": "You've built a working prototype - scalability can come next!",
        }
        return acknowledgments.get(
            category, "You've made great progress on your hackathon project!"
        )

    def _generate_context(
        self, category: str, strategy_context: StrategyAnalysisResult | None
    ) -> str:
        """Generate context explaining why this is common in hackathons.
        
        Args:
            category: Finding category
            strategy_context: Strategic context for adjustments
            
        Returns:
            Context explanation
        """
        base_context = {
            "security": "Security issues are extremely common in hackathons when teams prioritize speed over hardening. This is totally normal!",
            "bug": "Bugs happen when you're moving fast and trying new things. That's part of the learning process.",
            "testing": "Test coverage often takes a back seat during hackathons when you're racing against the clock.",
            "architecture": "Architecture decisions in hackathons often favor speed over long-term maintainability.",
        }

        context = base_context.get(
            category,
            "This is a common pattern we see in hackathon projects when teams are optimizing for demo-readiness.",
        )

        # Add strategic context if available
        if strategy_context:
            context += f" Your team's {strategy_context.test_strategy.value} approach shows {strategy_context.maturity_level.value}-level thinking."

        return context

    def _explain_vulnerability(self, finding: BugHunterEvidence) -> str:
        """Explain why the current approach is vulnerable.
        
        Args:
            finding: BugHunter evidence
            
        Returns:
            Explanation of vulnerability
        """
        return f"The current implementation in {finding.file} has a {finding.severity.value} severity {finding.category} issue: {finding.finding}"

    def _explain_fix(self, finding: BugHunterEvidence) -> str:
        """Explain why the fix solves the problem.
        
        Args:
            finding: BugHunter evidence
            
        Returns:
            Explanation of fix
        """
        return finding.recommendation

    def _generate_testing_instructions(self, finding: BugHunterEvidence) -> str:
        """Generate testing instructions for the fix.
        
        Args:
            finding: BugHunter evidence
            
        Returns:
            Testing instructions
        """
        if finding.category == "security":
            return "Test with malicious inputs to verify the fix prevents exploitation."
        elif finding.category == "bug":
            return "Add a unit test that reproduces the bug, then verify it passes after the fix."
        elif finding.category == "testing":
            return "Run your test suite to ensure coverage increases and tests pass."
        else:
            return "Verify the fix works by testing the affected functionality."

    def _generate_learning_resources(self, category: str) -> list[LearningResource]:
        """Generate learning resources for the category.
        
        Maps finding categories to curated learning resources including official
        documentation, tutorials, and articles. Prioritizes free, high-quality
        resources from authoritative sources.
        
        Args:
            category: Finding category (security, testing, architecture, etc.)
            
        Returns:
            List of learning resources with title, URL, and resource type
        """
        resources_map = {
            # Security resources
            "security": [
                LearningResource(
                    title="OWASP Top 10 Web Application Security Risks",
                    url="https://owasp.org/www-project-top-ten/",
                    resource_type="guide",
                ),
                LearningResource(
                    title="Python Security Best Practices Cheat Sheet",
                    url="https://snyk.io/blog/python-security-best-practices-cheat-sheet/",
                    resource_type="guide",
                ),
                LearningResource(
                    title="OWASP Cheat Sheet Series",
                    url="https://cheatsheetseries.owasp.org/",
                    resource_type="documentation",
                ),
            ],
            
            # Testing resources
            "testing": [
                LearningResource(
                    title="pytest Official Documentation",
                    url="https://docs.pytest.org/",
                    resource_type="documentation",
                ),
                LearningResource(
                    title="Testing Best Practices Guide",
                    url="https://testdriven.io/blog/testing-best-practices/",
                    resource_type="guide",
                ),
                LearningResource(
                    title="Test-Driven Development Tutorial",
                    url="https://realpython.com/python-testing/",
                    resource_type="tutorial",
                ),
            ],
            
            # Architecture resources
            "architecture": [
                LearningResource(
                    title="System Design Primer",
                    url="https://github.com/donnemartin/system-design-primer",
                    resource_type="guide",
                ),
                LearningResource(
                    title="Clean Architecture Principles",
                    url="https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html",
                    resource_type="guide",
                ),
                LearningResource(
                    title="Microservices Patterns",
                    url="https://microservices.io/patterns/index.html",
                    resource_type="documentation",
                ),
            ],
            
            # Database resources
            "database": [
                LearningResource(
                    title="PostgreSQL Tutorial",
                    url="https://www.postgresql.org/docs/current/tutorial.html",
                    resource_type="documentation",
                ),
                LearningResource(
                    title="Database Design Best Practices",
                    url="https://www.sqlshack.com/learn-sql-database-design/",
                    resource_type="guide",
                ),
                LearningResource(
                    title="SQL Performance Tuning",
                    url="https://use-the-index-luke.com/",
                    resource_type="guide",
                ),
            ],
            
            # API design resources
            "api": [
                LearningResource(
                    title="REST API Design Best Practices",
                    url="https://restfulapi.net/",
                    resource_type="guide",
                ),
                LearningResource(
                    title="FastAPI Documentation",
                    url="https://fastapi.tiangolo.com/",
                    resource_type="documentation",
                ),
                LearningResource(
                    title="API Security Best Practices",
                    url="https://owasp.org/www-project-api-security/",
                    resource_type="guide",
                ),
            ],
            
            # Scalability resources
            "scalability": [
                LearningResource(
                    title="Scalability Patterns",
                    url="https://github.com/binhnguyennus/awesome-scalability",
                    resource_type="guide",
                ),
                LearningResource(
                    title="Caching Strategies",
                    url="https://aws.amazon.com/caching/best-practices/",
                    resource_type="documentation",
                ),
                LearningResource(
                    title="High Scalability Blog",
                    url="http://highscalability.com/",
                    resource_type="guide",
                ),
            ],
            
            # Bug/code quality resources
            "bug": [
                LearningResource(
                    title="Debugging Techniques",
                    url="https://realpython.com/python-debugging-pdb/",
                    resource_type="tutorial",
                ),
                LearningResource(
                    title="Error Handling Best Practices",
                    url="https://docs.python.org/3/tutorial/errors.html",
                    resource_type="documentation",
                ),
            ],
            
            # Code smell resources
            "code_smell": [
                LearningResource(
                    title="Refactoring Guru - Code Smells",
                    url="https://refactoring.guru/refactoring/smells",
                    resource_type="guide",
                ),
                LearningResource(
                    title="Clean Code Principles",
                    url="https://github.com/ryanmcdermott/clean-code-python",
                    resource_type="guide",
                ),
                LearningResource(
                    title="Python Code Quality Tools",
                    url="https://realpython.com/python-code-quality/",
                    resource_type="tutorial",
                ),
            ],
            
            # Dependency management resources
            "dependency": [
                LearningResource(
                    title="Python Dependency Management Guide",
                    url="https://packaging.python.org/en/latest/tutorials/managing-dependencies/",
                    resource_type="documentation",
                ),
                LearningResource(
                    title="Security Vulnerability Scanning",
                    url="https://pypi.org/project/safety/",
                    resource_type="documentation",
                ),
                LearningResource(
                    title="Keeping Dependencies Updated",
                    url="https://dependabot.com/docs/",
                    resource_type="guide",
                ),
            ],
            
            # Performance resources
            "performance": [
                LearningResource(
                    title="Python Performance Tips",
                    url="https://wiki.python.org/moin/PythonSpeed/PerformanceTips",
                    resource_type="documentation",
                ),
                LearningResource(
                    title="Profiling Python Code",
                    url="https://realpython.com/python-profiling/",
                    resource_type="tutorial",
                ),
            ],
            
            # CI/CD resources
            "cicd": [
                LearningResource(
                    title="GitHub Actions Documentation",
                    url="https://docs.github.com/en/actions",
                    resource_type="documentation",
                ),
                LearningResource(
                    title="CI/CD Best Practices",
                    url="https://www.atlassian.com/continuous-delivery/principles/continuous-integration-vs-delivery-vs-deployment",
                    resource_type="guide",
                ),
            ],
            
            # Documentation resources
            "documentation": [
                LearningResource(
                    title="Write the Docs Guide",
                    url="https://www.writethedocs.org/guide/",
                    resource_type="guide",
                ),
                LearningResource(
                    title="README Best Practices",
                    url="https://github.com/matiassingers/awesome-readme",
                    resource_type="guide",
                ),
            ],
        }
        
        # Return resources for the category, or empty list if category not found
        return resources_map.get(category, [])

    def _estimate_effort(self, finding: BugHunterEvidence) -> EffortEstimate:
        """Estimate effort to fix the finding with category-specific logic.
        
        Categorizes fixes into:
        - Quick (5min): Simple style fixes, formatting, imports
        - Medium (30min): Logic bugs, test additions, refactoring
        - Involved (2hr+): Security vulnerabilities, architecture changes
        
        Args:
            finding: BugHunter evidence
            
        Returns:
            Effort estimate with minutes, difficulty, and prioritization guidance
        """
        # Category-specific effort estimation
        category = finding.category.lower()
        severity = finding.severity
        
        # Quick fixes (5-15 minutes) - Easy difficulty
        if category in ["style", "complexity"] and severity in [Severity.LOW, Severity.INFO]:
            return EffortEstimate(minutes=5, difficulty="Easy")
        
        if category == "import" and severity == Severity.MEDIUM:
            return EffortEstimate(minutes=10, difficulty="Easy")
        
        if category == "code_smell" and severity == Severity.LOW:
            return EffortEstimate(minutes=15, difficulty="Easy")
        
        # Medium fixes (30-60 minutes) - Moderate difficulty
        if category == "bug" and severity in [Severity.MEDIUM, Severity.HIGH]:
            return EffortEstimate(minutes=45, difficulty="Moderate")
        
        if category == "testing" and severity == Severity.MEDIUM:
            return EffortEstimate(minutes=30, difficulty="Moderate")
        
        if category == "dependency" and severity == Severity.MEDIUM:
            return EffortEstimate(minutes=30, difficulty="Moderate")
        
        if category == "code_smell" and severity in [Severity.MEDIUM, Severity.HIGH]:
            return EffortEstimate(minutes=60, difficulty="Moderate")
        
        # Involved fixes (2+ hours) - Advanced difficulty
        if category == "security":
            if severity == Severity.CRITICAL:
                return EffortEstimate(minutes=180, difficulty="Advanced")
            elif severity == Severity.HIGH:
                return EffortEstimate(minutes=120, difficulty="Advanced")
            else:
                return EffortEstimate(minutes=60, difficulty="Moderate")
        
        if category == "bug" and severity == Severity.CRITICAL:
            return EffortEstimate(minutes=120, difficulty="Advanced")
        
        if category == "dependency" and severity in [Severity.HIGH, Severity.CRITICAL]:
            return EffortEstimate(minutes=90, difficulty="Advanced")
        
        # Fallback to severity-based estimation
        return self._estimate_effort_from_severity(severity)

    def _estimate_effort_from_severity(self, severity: Severity) -> EffortEstimate:
        """Estimate effort from severity level.
        
        Args:
            severity: Finding severity
            
        Returns:
            Effort estimate
        """
        if severity == Severity.CRITICAL:
            return EffortEstimate(minutes=120, difficulty="Advanced")
        elif severity == Severity.HIGH:
            return EffortEstimate(minutes=60, difficulty="Moderate")
        elif severity == Severity.MEDIUM:
            return EffortEstimate(minutes=30, difficulty="Moderate")
        else:
            return EffortEstimate(minutes=15, difficulty="Easy")

    def _explain_business_impact(self, finding: BugHunterEvidence) -> str:
        """Explain business impact of the issue.
        
        Args:
            finding: BugHunter evidence
            
        Returns:
            Business impact explanation
        """
        impact_map = {
            "security": "Security vulnerabilities can lead to data breaches, loss of user trust, and legal liability.",
            "bug": "Bugs can cause user frustration, lost transactions, and negative reviews.",
            "testing": "Lack of tests makes it risky to add features or refactor, slowing down development.",
            "dependency": "Outdated dependencies can have security vulnerabilities and compatibility issues.",
        }
        return impact_map.get(
            finding.category,
            "This issue can impact user experience and system reliability.",
        )

    def _explain_business_impact_performance(
        self, finding: PerformanceEvidence
    ) -> str:
        """Explain business impact of performance issues.
        
        Args:
            finding: Performance evidence
            
        Returns:
            Business impact explanation
        """
        impact_map = {
            "architecture": "Poor architecture makes it hard to scale and maintain the system as it grows.",
            "database": "Database inefficiencies can cause slow page loads and poor user experience.",
            "api": "API design issues can make integration difficult and limit adoption.",
            "scalability": "Scalability issues mean the system may fail under increased load.",
        }
        return impact_map.get(
            finding.category,
            "This can impact system performance and user satisfaction.",
        )

    def _add_code_examples(
        self,
        finding: BugHunterEvidence | PerformanceEvidence,
    ) -> CodeExample | None:
        """Generate before/after code examples for a finding.
        
        For each finding, generates a code snippet showing:
        1. The vulnerable/problematic code (before)
        2. The fixed/improved code (after)
        3. An explanation of why the fix improves the code
        
        Args:
            finding: Evidence item with file, line, category, and recommendation
            
        Returns:
            CodeExample with vulnerable_code, fixed_code, and explanation,
            or None if code example cannot be generated for this finding type
        """
        # Map category to code example generator
        if isinstance(finding, BugHunterEvidence):
            if finding.category == "security":
                return self._generate_security_example(finding)
            elif finding.category == "bug":
                return self._generate_bug_example(finding)
            elif finding.category == "testing":
                return self._generate_testing_example(finding)
            elif finding.category == "code_smell":
                return self._generate_code_smell_example(finding)
            elif finding.category == "dependency":
                return self._generate_dependency_example(finding)
        elif isinstance(finding, PerformanceEvidence):
            if finding.category == "database":
                return self._generate_database_example(finding)
            elif finding.category == "api":
                return self._generate_api_example(finding)
            elif finding.category == "architecture":
                return self._generate_architecture_example(finding)
            elif finding.category == "scalability":
                return self._generate_scalability_example(finding)

        # Default: return None if no specific example generator exists
        return None

    def _generate_security_example(self, finding: BugHunterEvidence) -> CodeExample:
        """Generate security-related code example.
        
        Args:
            finding: BugHunter evidence with security category
            
        Returns:
            CodeExample showing vulnerable and fixed code
        """
        # Detect specific security issue types from finding text
        finding_lower = finding.finding.lower()
        
        if "sql injection" in finding_lower or "sql" in finding_lower:
            return CodeExample(
                vulnerable_code=f"""# {finding.file}:{finding.line or '?'}
# ❌ Vulnerable to SQL injection
def get_user(username):
    query = f"SELECT * FROM users WHERE username = '{{username}}'"
    return db.execute(query)""",
                fixed_code=f"""# {finding.file}:{finding.line or '?'}
# ✅ Protected with parameterized query
def get_user(username):
    query = "SELECT * FROM users WHERE username = ?"
    return db.execute(query, (username,))""",
                explanation="Parameterized queries prevent SQL injection by treating user input as data, not executable code. The database driver automatically escapes special characters, making it impossible for attackers to inject malicious SQL commands.",
            )
        
        elif "password" in finding_lower or "hash" in finding_lower:
            return CodeExample(
                vulnerable_code=f"""# {finding.file}:{finding.line or '?'}
# ❌ Storing passwords in plain text
def create_user(username, password):
    user = User(username=username, password=password)
    db.save(user)""",
                fixed_code=f"""# {finding.file}:{finding.line or '?'}
# ✅ Hashing passwords with bcrypt
import bcrypt

def create_user(username, password):
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
    user = User(username=username, password_hash=hashed)
    db.save(user)""",
                explanation="Hashing passwords with bcrypt protects user credentials even if the database is compromised. Bcrypt includes a salt and is computationally expensive, making brute-force attacks impractical.",
            )
        
        elif "xss" in finding_lower or "cross-site" in finding_lower or "escape" in finding_lower:
            return CodeExample(
                vulnerable_code=f"""# {finding.file}:{finding.line or '?'}
# ❌ Vulnerable to XSS attacks
@app.route('/search')
def search():
    query = request.args.get('q')
    return f"<h1>Results for: {{query}}</h1>" """,
                fixed_code=f"""# {finding.file}:{finding.line or '?'}
# ✅ Escaping user input
from markupsafe import escape

@app.route('/search')
def search():
    query = request.args.get('q')
    return f"<h1>Results for: {{escape(query)}}</h1>" """,
                explanation="Escaping user input prevents XSS attacks by converting special HTML characters (like <, >, &) into safe entities. This ensures user input is displayed as text, not executed as code.",
            )
        
        elif "secret" in finding_lower or "api key" in finding_lower or "token" in finding_lower:
            return CodeExample(
                vulnerable_code=f"""# {finding.file}:{finding.line or '?'}
# ❌ Hardcoded secrets in source code
API_KEY = "sk_live_abc123xyz789"
db_password = "MySecretPassword123"

def connect():
    return db.connect(password=db_password)""",
                fixed_code=f"""# {finding.file}:{finding.line or '?'}
# ✅ Loading secrets from environment variables
import os

API_KEY = os.environ.get("API_KEY")
db_password = os.environ.get("DB_PASSWORD")

def connect():
    return db.connect(password=db_password)""",
                explanation="Environment variables keep secrets out of source code, preventing accidental exposure in version control. Use .env files locally and secret managers (AWS Secrets Manager, etc.) in production.",
            )
        
        else:
            # Generic security example
            return CodeExample(
                vulnerable_code=f"""# {finding.file}:{finding.line or '?'}
# ❌ Current implementation
# {finding.finding}""",
                fixed_code=f"""# {finding.file}:{finding.line or '?'}
# ✅ Improved implementation
# {finding.recommendation}""",
                explanation="This fix addresses the security concern by implementing proper validation, sanitization, or access controls to prevent potential exploits.",
            )

    def _generate_bug_example(self, finding: BugHunterEvidence) -> CodeExample:
        """Generate bug-related code example.
        
        Args:
            finding: BugHunter evidence with bug category
            
        Returns:
            CodeExample showing buggy and fixed code
        """
        finding_lower = finding.finding.lower()
        
        if "null" in finding_lower or "none" in finding_lower or "undefined" in finding_lower:
            return CodeExample(
                vulnerable_code=f"""# {finding.file}:{finding.line or '?'}
# ❌ No null check
def process_order(order):
    total = order.items.sum()  # Crashes if items is None
    return total * 1.1""",
                fixed_code=f"""# {finding.file}:{finding.line or '?'}
# ✅ Defensive null check
def process_order(order):
    if not order or not order.items:
        return 0
    total = order.items.sum()
    return total * 1.1""",
                explanation="Null checks prevent crashes when data is missing or invalid. This defensive programming pattern makes your code more robust and user-friendly.",
            )
        
        elif "divide" in finding_lower or "division" in finding_lower or "zero" in finding_lower:
            return CodeExample(
                vulnerable_code=f"""# {finding.file}:{finding.line or '?'}
# ❌ Division by zero risk
def calculate_average(total, count):
    return total / count  # Crashes if count is 0""",
                fixed_code=f"""# {finding.file}:{finding.line or '?'}
# ✅ Handle edge case
def calculate_average(total, count):
    if count == 0:
        return 0
    return total / count""",
                explanation="Checking for zero before division prevents runtime errors. This is especially important when count comes from user input or database queries that might return empty results.",
            )
        
        elif "index" in finding_lower or "array" in finding_lower or "list" in finding_lower:
            return CodeExample(
                vulnerable_code=f"""# {finding.file}:{finding.line or '?'}
# ❌ Index out of bounds risk
def get_first_item(items):
    return items[0]  # Crashes if items is empty""",
                fixed_code=f"""# {finding.file}:{finding.line or '?'}
# ✅ Safe array access
def get_first_item(items):
    if not items:
        return None
    return items[0]""",
                explanation="Checking array length before accessing elements prevents index errors. Returning None or a default value makes the function more predictable and easier to use.",
            )
        
        else:
            # Generic bug example
            return CodeExample(
                vulnerable_code=f"""# {finding.file}:{finding.line or '?'}
# ❌ Current implementation
# {finding.finding}""",
                fixed_code=f"""# {finding.file}:{finding.line or '?'}
# ✅ Fixed implementation
# {finding.recommendation}""",
                explanation="This fix addresses the bug by adding proper error handling, validation, or edge case handling to prevent unexpected behavior.",
            )

    def _generate_testing_example(self, finding: BugHunterEvidence) -> CodeExample:
        """Generate testing-related code example.
        
        Args:
            finding: BugHunter evidence with testing category
            
        Returns:
            CodeExample showing test implementation
        """
        return CodeExample(
            vulnerable_code=f"""# {finding.file}:{finding.line or '?'}
# ❌ No tests for this functionality
def calculate_discount(price, percentage):
    return price * (1 - percentage / 100)

# No test file exists""",
            fixed_code=f"""# tests/test_{finding.file.replace('/', '_').replace('.py', '')}.py
# ✅ Comprehensive test coverage
import pytest

def test_calculate_discount_normal():
    assert calculate_discount(100, 10) == 90

def test_calculate_discount_zero():
    assert calculate_discount(100, 0) == 100

def test_calculate_discount_full():
    assert calculate_discount(100, 100) == 0

def test_calculate_discount_invalid():
    with pytest.raises(ValueError):
        calculate_discount(100, -10)""",
            explanation="Tests verify your code works correctly and prevent regressions when you make changes. Start with happy path tests, then add edge cases (zero, negative, boundary values).",
        )

    def _generate_code_smell_example(self, finding: BugHunterEvidence) -> CodeExample:
        """Generate code smell example.
        
        Args:
            finding: BugHunter evidence with code_smell category
            
        Returns:
            CodeExample showing refactored code
        """
        finding_lower = finding.finding.lower()
        
        if "duplicate" in finding_lower or "repeated" in finding_lower:
            return CodeExample(
                vulnerable_code=f"""# {finding.file}:{finding.line or '?'}
# ❌ Duplicated code
def send_welcome_email(user):
    subject = "Welcome!"
    body = f"Hi {{user.name}}, welcome to our app!"
    send_email(user.email, subject, body)

def send_reset_email(user):
    subject = "Password Reset"
    body = f"Hi {{user.name}}, click here to reset."
    send_email(user.email, subject, body)""",
                fixed_code=f"""# {finding.file}:{finding.line or '?'}
# ✅ Extracted common logic
def send_user_email(user, subject, body_template):
    body = body_template.format(name=user.name)
    send_email(user.email, subject, body)

def send_welcome_email(user):
    send_user_email(user, "Welcome!", "Hi {{name}}, welcome!")

def send_reset_email(user):
    send_user_email(user, "Password Reset", "Hi {{name}}, click here.")""",
                explanation="Extracting common logic into a shared function reduces duplication and makes maintenance easier. When you need to change email sending logic, you only update one place.",
            )
        
        elif "complex" in finding_lower or "long" in finding_lower:
            return CodeExample(
                vulnerable_code=f"""# {finding.file}:{finding.line or '?'}
# ❌ Complex nested logic
def process(data):
    if data:
        if data.valid:
            if data.user:
                if data.user.active:
                    return data.user.process()
    return None""",
                fixed_code=f"""# {finding.file}:{finding.line or '?'}
# ✅ Early returns for clarity
def process(data):
    if not data:
        return None
    if not data.valid:
        return None
    if not data.user or not data.user.active:
        return None
    return data.user.process()""",
                explanation="Early returns (guard clauses) reduce nesting and make code easier to read. Each condition is clear and independent, making the logic flow more obvious.",
            )
        
        else:
            # Generic code smell example
            return CodeExample(
                vulnerable_code=f"""# {finding.file}:{finding.line or '?'}
# ❌ Current implementation
# {finding.finding}""",
                fixed_code=f"""# {finding.file}:{finding.line or '?'}
# ✅ Refactored implementation
# {finding.recommendation}""",
                explanation="This refactoring improves code readability, maintainability, and follows best practices for clean code.",
            )

    def _generate_dependency_example(self, finding: BugHunterEvidence) -> CodeExample:
        """Generate dependency-related code example.
        
        Args:
            finding: BugHunter evidence with dependency category
            
        Returns:
            CodeExample showing dependency update
        """
        return CodeExample(
            vulnerable_code=f"""# requirements.txt
# ❌ Outdated dependencies with known vulnerabilities
flask==1.0.0
requests==2.18.0
django==2.0.0""",
            fixed_code=f"""# requirements.txt
# ✅ Updated to latest secure versions
flask==3.0.0
requests==2.31.0
django==5.0.0

# Run: pip install -r requirements.txt --upgrade""",
            explanation="Keeping dependencies updated patches security vulnerabilities and provides bug fixes. Use tools like 'pip list --outdated' or 'safety check' to identify vulnerable packages.",
        )

    def _generate_database_example(self, finding: PerformanceEvidence) -> CodeExample:
        """Generate database performance example.
        
        Args:
            finding: Performance evidence with database category
            
        Returns:
            CodeExample showing database optimization
        """
        finding_lower = finding.finding.lower()
        
        if "n+1" in finding_lower or "query" in finding_lower:
            return CodeExample(
                vulnerable_code=f"""# {finding.file}:{finding.line or '?'}
# ❌ N+1 query problem
def get_posts_with_authors():
    posts = Post.query.all()
    for post in posts:
        print(post.author.name)  # Separate query for each post!""",
                fixed_code=f"""# {finding.file}:{finding.line or '?'}
# ✅ Eager loading with join
def get_posts_with_authors():
    posts = Post.query.options(joinedload(Post.author)).all()
    for post in posts:
        print(post.author.name)  # No extra queries!""",
                explanation="Eager loading fetches related data in a single query instead of making N separate queries. This dramatically improves performance when displaying lists with relationships.",
            )
        
        elif "index" in finding_lower:
            return CodeExample(
                vulnerable_code=f"""# {finding.file}:{finding.line or '?'}
# ❌ No database index
class User(db.Model):
    email = db.Column(db.String(120))
    
# Query is slow on large tables
User.query.filter_by(email=email).first()""",
                fixed_code=f"""# {finding.file}:{finding.line or '?'}
# ✅ Add index for frequently queried column
class User(db.Model):
    email = db.Column(db.String(120), index=True)

# Query is now fast even with millions of users
User.query.filter_by(email=email).first()""",
                explanation="Database indexes speed up queries by creating a sorted lookup structure. Add indexes to columns used in WHERE clauses, JOIN conditions, or ORDER BY statements.",
            )
        
        else:
            # Generic database example
            return CodeExample(
                vulnerable_code=f"""# {finding.file}:{finding.line or '?'}
# ❌ Current implementation
# {finding.finding}""",
                fixed_code=f"""# {finding.file}:{finding.line or '?'}
# ✅ Optimized implementation
# {finding.recommendation}""",
                explanation="This optimization improves database performance by reducing query count, adding indexes, or optimizing query structure.",
            )

    def _generate_api_example(self, finding: PerformanceEvidence) -> CodeExample:
        """Generate API design example.
        
        Args:
            finding: Performance evidence with api category
            
        Returns:
            CodeExample showing API improvement
        """
        finding_lower = finding.finding.lower()
        
        if "pagination" in finding_lower:
            return CodeExample(
                vulnerable_code=f"""# {finding.file}:{finding.line or '?'}
# ❌ No pagination - returns all records
@app.route('/api/users')
def get_users():
    users = User.query.all()  # Could be millions!
    return jsonify([u.to_dict() for u in users])""",
                fixed_code=f"""# {finding.file}:{finding.line or '?'}
# ✅ Pagination for large datasets
@app.route('/api/users')
def get_users():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    users = User.query.paginate(page=page, per_page=per_page)
    return jsonify({{
        'items': [u.to_dict() for u in users.items],
        'total': users.total,
        'page': page,
        'pages': users.pages
    }})""",
                explanation="Pagination prevents overwhelming clients with huge responses and reduces server load. Return metadata (total, page, pages) so clients can build navigation UI.",
            )
        
        elif "rate limit" in finding_lower or "throttle" in finding_lower:
            return CodeExample(
                vulnerable_code=f"""# {finding.file}:{finding.line or '?'}
# ❌ No rate limiting
@app.route('/api/search')
def search():
    query = request.args.get('q')
    return jsonify(expensive_search(query))""",
                fixed_code=f"""# {finding.file}:{finding.line or '?'}
# ✅ Rate limiting to prevent abuse
from flask_limiter import Limiter

limiter = Limiter(app, key_func=lambda: request.remote_addr)

@app.route('/api/search')
@limiter.limit("10 per minute")
def search():
    query = request.args.get('q')
    return jsonify(expensive_search(query))""",
                explanation="Rate limiting prevents API abuse and protects your server from being overwhelmed. Set limits based on endpoint cost (expensive operations get lower limits).",
            )
        
        else:
            # Generic API example
            return CodeExample(
                vulnerable_code=f"""# {finding.file}:{finding.line or '?'}
# ❌ Current implementation
# {finding.finding}""",
                fixed_code=f"""# {finding.file}:{finding.line or '?'}
# ✅ Improved implementation
# {finding.recommendation}""",
                explanation="This improvement makes the API more efficient, scalable, and user-friendly by following REST best practices.",
            )

    def _generate_architecture_example(self, finding: PerformanceEvidence) -> CodeExample:
        """Generate architecture example.
        
        Args:
            finding: Performance evidence with architecture category
            
        Returns:
            CodeExample showing architectural improvement
        """
        return CodeExample(
            vulnerable_code=f"""# {finding.file}:{finding.line or '?'}
# ❌ Tight coupling - hard to test and maintain
class OrderController:
    def create_order(self, data):
        # Business logic mixed with database access
        order = Order(**data)
        db.session.add(order)
        db.session.commit()
        send_email(order.user.email, "Order confirmed")
        return order""",
            fixed_code=f"""# {finding.file}:{finding.line or '?'}
# ✅ Separation of concerns - testable and maintainable
class OrderService:
    def __init__(self, db, email_service):
        self.db = db
        self.email_service = email_service
    
    def create_order(self, data):
        order = Order(**data)
        self.db.save(order)
        self.email_service.send_confirmation(order)
        return order

class OrderController:
    def create_order(self, data):
        return order_service.create_order(data)""",
            explanation="Separating concerns (business logic, data access, external services) makes code easier to test, maintain, and modify. Each class has a single responsibility.",
        )

    def _generate_scalability_example(self, finding: PerformanceEvidence) -> CodeExample:
        """Generate scalability example.
        
        Args:
            finding: Performance evidence with scalability category
            
        Returns:
            CodeExample showing scalability improvement
        """
        finding_lower = finding.finding.lower()
        
        if "cache" in finding_lower or "caching" in finding_lower:
            return CodeExample(
                vulnerable_code=f"""# {finding.file}:{finding.line or '?'}
# ❌ Expensive computation on every request
@app.route('/api/stats')
def get_stats():
    # Recalculates from millions of records every time
    return jsonify(calculate_expensive_stats())""",
                fixed_code=f"""# {finding.file}:{finding.line or '?'}
# ✅ Cache expensive computations
from functools import lru_cache
from datetime import datetime, timedelta

@lru_cache(maxsize=1)
def get_cached_stats(cache_key):
    return calculate_expensive_stats()

@app.route('/api/stats')
def get_stats():
    # Cache key changes every 5 minutes
    cache_key = datetime.now().replace(second=0, microsecond=0) // timedelta(minutes=5)
    return jsonify(get_cached_stats(cache_key))""",
                explanation="Caching expensive computations dramatically improves response time and reduces server load. Invalidate cache periodically or when data changes.",
            )
        
        else:
            # Generic scalability example
            return CodeExample(
                vulnerable_code=f"""# {finding.file}:{finding.line or '?'}
# ❌ Current implementation
# {finding.finding}""",
                fixed_code=f"""# {finding.file}:{finding.line or '?'}
# ✅ Scalable implementation
# {finding.recommendation}""",
                explanation="This optimization improves scalability by reducing resource usage, enabling horizontal scaling, or improving throughput.",
            )
