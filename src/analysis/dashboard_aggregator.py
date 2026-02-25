"""Dashboard aggregator for organizer intelligence."""

from collections import Counter, defaultdict

import structlog

from src.models.dashboard import (
    CommonIssue,
    HiringIntelligence,
    OrganizerDashboard,
    PrizeRecommendation,
    TechnologyTrends,
    TopPerformer,
)
from src.models.strategy import StrategyAnalysisResult
from src.models.submission import SubmissionResponse
from src.models.team_dynamics import ContributorRole, IndividualScorecard, TeamAnalysisResult

logger = structlog.get_logger()


class DashboardAggregator:
    """Generates organizer intelligence dashboard from all submissions."""

    def __init__(self) -> None:
        """Initialize dashboard aggregator."""
        self.logger = logger.bind(component="dashboard_aggregator")

    def generate_dashboard(
        self,
        hack_id: str,
        hackathon_name: str,
        submissions: list[SubmissionResponse],
        team_analyses: dict[str, TeamAnalysisResult],
        strategy_analyses: dict[str, StrategyAnalysisResult],
    ) -> OrganizerDashboard:
        """Generate intelligence dashboard for hackathon.

        Args:
            hack_id: Hackathon ID
            hackathon_name: Hackathon name
            submissions: All submissions for the hackathon
            team_analyses: Team analysis results by sub_id
            strategy_analyses: Strategy analysis results by sub_id

        Returns:
            OrganizerDashboard with aggregated insights
        """
        self.logger.info(
            "generating_dashboard",
            hack_id=hack_id,
            total_submissions=len(submissions),
        )

        # Filter to analyzed submissions only
        analyzed_submissions = [s for s in submissions if s.overall_score is not None]

        # Aggregate all individual scorecards
        all_scorecards: list[IndividualScorecard] = []
        for _sub_id, team_analysis in team_analyses.items():
            all_scorecards.extend(team_analysis.individual_scorecards)

        # Generate dashboard components
        top_performers = self._aggregate_top_performers(analyzed_submissions)
        hiring_intelligence = self._generate_hiring_intelligence(all_scorecards)
        technology_trends = self._analyze_technology_trends(analyzed_submissions)
        common_issues = self._identify_common_issues(submissions, team_analyses)
        prize_recommendations = self._generate_prize_recommendations(
            analyzed_submissions, team_analyses, strategy_analyses
        )

        # Generate recommendations
        standout_moments = self._identify_standout_moments(
            analyzed_submissions, team_analyses, strategy_analyses
        )
        next_hackathon_recommendations = self._generate_next_hackathon_recommendations(
            common_issues, technology_trends
        )
        sponsor_follow_up_actions = self._generate_sponsor_follow_up_actions(
            hiring_intelligence, technology_trends
        )

        dashboard = OrganizerDashboard(
            hack_id=hack_id,
            hackathon_name=hackathon_name,
            total_submissions=len(submissions),
            top_performers=top_performers,
            hiring_intelligence=hiring_intelligence,
            technology_trends=technology_trends,
            common_issues=common_issues,
            standout_moments=standout_moments,
            prize_recommendations=prize_recommendations,
            next_hackathon_recommendations=next_hackathon_recommendations,
            sponsor_follow_up_actions=sponsor_follow_up_actions,
        )

        self.logger.info(
            "dashboard_generated",
            hack_id=hack_id,
            top_performers_count=len(top_performers),
            total_candidates=len(all_scorecards),
            must_interview_count=len(hiring_intelligence.must_interview),
        )

        return dashboard

    def _aggregate_top_performers(
        self, submissions: list[SubmissionResponse]
    ) -> list[TopPerformer]:
        """Identify top teams with key strengths.

        Args:
            submissions: Analyzed submissions

        Returns:
            List of top performers (top 10 by score)
        """
        # Sort by overall score descending
        sorted_submissions = sorted(
            submissions,
            key=lambda s: s.overall_score or 0,
            reverse=True,
        )

        top_performers = []
        for submission in sorted_submissions[:10]:
            # Extract key strengths from submission
            key_strengths = submission.strengths[:3] if submission.strengths else []

            # Identify sponsor interest flags based on repo metadata
            sponsor_flags = []
            if submission.repo_meta is not None:
                if submission.repo_meta.has_ci:
                    sponsor_flags.append("ci_cd_sophistication")
                if submission.repo_meta.has_dockerfile:
                    sponsor_flags.append("containerization")
                if submission.repo_meta.workflow_success_rate > 0.9:
                    sponsor_flags.append("high_quality_automation")

            top_performers.append(
                TopPerformer(
                    team_name=submission.team_name,
                    sub_id=submission.sub_id,
                    overall_score=submission.overall_score or 0,
                    key_strengths=key_strengths,
                    sponsor_interest_flags=sponsor_flags,
                )
            )

        return top_performers

    def _generate_hiring_intelligence(
        self, scorecards: list[IndividualScorecard]
    ) -> HiringIntelligence:
        """Categorize candidates by role and seniority.

        Args:
            scorecards: All individual scorecards

        Returns:
            HiringIntelligence with categorized candidates
        """
        # Categorize by role
        backend_candidates = []
        frontend_candidates = []
        devops_candidates = []
        full_stack_candidates = []
        must_interview = []

        for scorecard in scorecards:
            # Add to role-specific lists
            if scorecard.role == ContributorRole.BACKEND:
                backend_candidates.append(scorecard)
            elif scorecard.role == ContributorRole.FRONTEND:
                frontend_candidates.append(scorecard)
            elif scorecard.role == ContributorRole.DEVOPS:
                devops_candidates.append(scorecard)
            elif scorecard.role == ContributorRole.FULL_STACK:
                full_stack_candidates.append(scorecard)

            # Add to must-interview if flagged
            if scorecard.hiring_signals.must_interview:
                must_interview.append(scorecard)

        # Sort each category by seniority (senior first)
        seniority_order = {"senior": 0, "mid": 1, "junior": 2}

        def sort_key(sc: IndividualScorecard) -> int:
            return seniority_order.get(sc.hiring_signals.seniority_level.lower(), 3)

        backend_candidates.sort(key=sort_key)
        frontend_candidates.sort(key=sort_key)
        devops_candidates.sort(key=sort_key)
        full_stack_candidates.sort(key=sort_key)
        must_interview.sort(key=sort_key)

        return HiringIntelligence(
            backend_candidates=backend_candidates,
            frontend_candidates=frontend_candidates,
            devops_candidates=devops_candidates,
            full_stack_candidates=full_stack_candidates,
            must_interview=must_interview,
        )

    def _analyze_technology_trends(self, submissions: list[SubmissionResponse]) -> TechnologyTrends:
        """Identify popular stacks and emerging tech.

        Detects:
        - Primary languages from repo metadata
        - Frameworks from package files (package.json, requirements.txt, etc.)
        - Popular stack combinations
        - Emerging technologies (used by 2-5 teams)

        Args:
            submissions: All submissions

        Returns:
            TechnologyTrends with usage statistics
        """
        # Count primary languages
        language_counter: Counter[str] = Counter()
        framework_counter: Counter[str] = Counter()
        stack_counter: Counter[str] = Counter()

        for submission in submissions:
            if not submission.repo_meta:
                continue

            # Count primary language
            if submission.repo_meta.primary_language:
                language_counter[submission.repo_meta.primary_language] += 1

            # Detect frameworks from repo characteristics
            frameworks = self._detect_frameworks(submission)
            for framework in frameworks:
                framework_counter[framework] += 1

            # Create stack combination from languages
            if submission.repo_meta.languages:
                # Get top 3 languages
                top_langs = sorted(
                    submission.repo_meta.languages.items(),
                    key=lambda x: x[1],
                    reverse=True,
                )[:3]
                stack = " + ".join([lang for lang, _ in top_langs])
                stack_counter[stack] += 1

        # Combine languages and frameworks for "most used"
        combined_counter = language_counter + framework_counter

        # Most used technologies (top 10)
        most_used = combined_counter.most_common(10)

        # Emerging technologies (used by 2-5 teams, indicating new adoption)
        emerging = [tech for tech, count in combined_counter.items() if 2 <= count <= 5]

        # Popular stacks (top 5)
        popular_stacks = stack_counter.most_common(5)

        return TechnologyTrends(
            most_used=most_used,
            emerging=emerging,
            popular_stacks=popular_stacks,
        )

    def _detect_frameworks(self, submission: SubmissionResponse) -> list[str]:
        """Detect frameworks from repository metadata.

        Looks for indicators in:
        - Has Docker (containerization)
        - Has CI/CD (GitHub Actions)
        - Language-specific frameworks (future enhancement)

        Args:
            submission: Submission to analyze

        Returns:
            List of detected framework names
        """
        frameworks: list[str] = []
        repo_meta = submission.repo_meta

        if not repo_meta:
            return frameworks

        # Docker/containerization
        if repo_meta.has_dockerfile:
            frameworks.append("Docker")

        # CI/CD
        if repo_meta.has_ci:
            frameworks.append("GitHub Actions")

        # Language-specific framework detection
        primary_lang = repo_meta.primary_language

        if primary_lang == "Python":
            # Common Python frameworks (heuristic-based)
            # In a real implementation, we'd parse requirements.txt
            # For now, we use common patterns
            frameworks.extend(self._detect_python_frameworks(submission))

        elif primary_lang in ["JavaScript", "TypeScript"]:
            # Common JS/TS frameworks
            frameworks.extend(self._detect_javascript_frameworks(submission))

        # Note: We don't add Go/Rust here as they're already counted as languages
        # This avoids double-counting in the technology trends

        return frameworks

    def _detect_python_frameworks(self, submission: SubmissionResponse) -> list[str]:
        """Detect Python frameworks from submission data.

        Args:
            submission: Submission to analyze

        Returns:
            List of detected Python frameworks
        """
        # In a full implementation, we'd parse requirements.txt or pyproject.toml
        # For MVP, we return empty list since we don't have file content access here
        # This would be enhanced in Phase 2 with file content analysis
        return []

    def _detect_javascript_frameworks(self, submission: SubmissionResponse) -> list[str]:
        """Detect JavaScript/TypeScript frameworks from submission data.

        Args:
            submission: Submission to analyze

        Returns:
            List of detected JS/TS frameworks
        """
        # In a full implementation, we'd parse package.json
        # For MVP, we return empty list since we don't have file content access here
        # This would be enhanced in Phase 2 with file content analysis
        return []

    def _identify_common_issues(
        self,
        submissions: list[SubmissionResponse],
        team_analyses: dict[str, TeamAnalysisResult],
    ) -> list[CommonIssue]:
        """Find patterns across submissions.

        Args:
            submissions: All submissions
            team_analyses: Team analysis results by sub_id

        Returns:
            List of common issues with workshop recommendations
        """
        total_submissions = len(submissions)
        if total_submissions == 0:
            return []

        # Track issue types
        issue_counter: dict[str, list[str]] = defaultdict(list)

        # Analyze weaknesses from submissions
        for submission in submissions:
            for weakness in submission.weaknesses:
                # Categorize weakness into issue type
                issue_type = self._categorize_weakness(weakness)
                issue_counter[issue_type].append(submission.team_name)

        # Analyze red flags from team analyses
        for sub_id, team_analysis in team_analyses.items():
            sub: SubmissionResponse | None = next(
                (s for s in submissions if s.sub_id == sub_id), None
            )
            if sub is None:
                continue

            for red_flag in team_analysis.red_flags:
                issue_counter[red_flag.flag_type].append(submission.team_name)

        # Create common issues (affecting >20% of teams)
        common_issues = []
        threshold = total_submissions * 0.2

        for issue_type, affected_teams in issue_counter.items():
            if len(affected_teams) >= threshold:
                percentage = (len(affected_teams) / total_submissions) * 100
                workshop = self._recommend_workshop(issue_type)

                common_issues.append(
                    CommonIssue(
                        issue_type=issue_type,
                        percentage_affected=percentage,
                        workshop_recommendation=workshop,
                        example_teams=affected_teams[:3],  # Show first 3 examples
                    )
                )

        # Sort by percentage affected (descending) and limit to top 10
        common_issues.sort(key=lambda x: x.percentage_affected, reverse=True)

        return common_issues[:10]  # Return top 10 most common issues

    def _categorize_weakness(self, weakness: str) -> str:
        """Categorize a weakness into an issue type.

        Args:
            weakness: Weakness description

        Returns:
            Issue type category
        """
        weakness_lower = weakness.lower()

        if any(keyword in weakness_lower for keyword in ["test", "testing", "coverage"]):
            return "insufficient_testing"
        elif any(
            keyword in weakness_lower for keyword in ["security", "vulnerability", "injection"]
        ):
            return "security_vulnerabilities"
        elif any(keyword in weakness_lower for keyword in ["documentation", "readme"]):
            return "poor_documentation"
        elif any(keyword in weakness_lower for keyword in ["error handling", "exception"]):
            return "weak_error_handling"
        elif any(keyword in weakness_lower for keyword in ["performance", "optimization"]):
            return "performance_issues"
        else:
            return "general_code_quality"

    def _recommend_workshop(self, issue_type: str) -> str:
        """Recommend workshop based on issue type.

        Args:
            issue_type: Type of common issue

        Returns:
            Workshop recommendation
        """
        workshops = {
            "insufficient_testing": "Workshop: Test-Driven Development for Hackathons",
            "security_vulnerabilities": "Workshop: Secure Coding Practices & OWASP Top 10",
            "poor_documentation": "Workshop: Technical Writing & Documentation Best Practices",
            "weak_error_handling": "Workshop: Defensive Programming & Error Handling",
            "performance_issues": "Workshop: Performance Optimization Fundamentals",
            "extreme_imbalance": "Workshop: Effective Team Collaboration & Git Workflows",
            "ghost_contributor": "Workshop: Team Dynamics & Inclusive Collaboration",
            "general_code_quality": "Workshop: Clean Code Principles",
        }
        return workshops.get(issue_type, "Workshop: Software Engineering Best Practices")

    def _generate_prize_recommendations(
        self,
        submissions: list[SubmissionResponse],
        team_analyses: dict[str, TeamAnalysisResult],
        strategy_analyses: dict[str, StrategyAnalysisResult],
    ) -> list[PrizeRecommendation]:
        """Recommend prize winners with evidence.

        Args:
            submissions: All analyzed submissions
            team_analyses: Team analysis results
            strategy_analyses: Strategy analysis results

        Returns:
            List of prize recommendations
        """
        recommendations = []

        # Best Team Dynamics
        best_team_dynamics = self._find_best_team_dynamics(submissions, team_analyses)
        if best_team_dynamics:
            recommendations.append(best_team_dynamics)

        # Most Improved / Best Learning Journey
        best_learning = self._find_best_learning_journey(submissions, strategy_analyses)
        if best_learning:
            recommendations.append(best_learning)

        # Best CI/CD Practices
        best_cicd = self._find_best_cicd(submissions)
        if best_cicd:
            recommendations.append(best_cicd)

        return recommendations

    def _find_best_team_dynamics(
        self,
        submissions: list[SubmissionResponse],
        team_analyses: dict[str, TeamAnalysisResult],
    ) -> PrizeRecommendation | None:
        """Find team with best dynamics.

        Args:
            submissions: All submissions
            team_analyses: Team analysis results

        Returns:
            Prize recommendation or None
        """
        best_team = None
        best_grade = ""

        grade_order = {"A": 0, "B": 1, "C": 2, "D": 3, "F": 4}

        for sub_id, team_analysis in team_analyses.items():
            grade = team_analysis.team_dynamics_grade
            if not best_team or grade_order.get(grade, 5) < grade_order.get(best_grade, 5):
                best_team = sub_id
                best_grade = grade

        if not best_team:
            return None

        submission = next((s for s in submissions if s.sub_id == best_team), None)
        if not submission:
            return None

        team_analysis = team_analyses[best_team]
        evidence = [
            f"Team dynamics grade: {team_analysis.team_dynamics_grade}",
            "Balanced workload distribution",
            f"{len(team_analysis.collaboration_patterns)} positive collaboration patterns",
        ]

        return PrizeRecommendation(
            prize_category="Best Team Dynamics",
            recommended_team=submission.team_name,
            sub_id=best_team,
            justification=f"Exceptional team collaboration with grade {best_grade}",
            evidence=evidence,
        )

    def _find_best_learning_journey(
        self,
        submissions: list[SubmissionResponse],
        strategy_analyses: dict[str, StrategyAnalysisResult],
    ) -> PrizeRecommendation | None:
        """Find team with best learning journey.

        Args:
            submissions: All submissions
            strategy_analyses: Strategy analysis results

        Returns:
            Prize recommendation or None
        """
        best_team = None
        best_journey = None

        for sub_id, strategy_analysis in strategy_analyses.items():
            if (
                strategy_analysis.learning_journey
                and strategy_analysis.learning_journey.impressive
                and (
                    not best_journey
                    or len(strategy_analysis.learning_journey.evidence) > len(best_journey.evidence)
                )
            ):
                best_team = sub_id
                best_journey = strategy_analysis.learning_journey

        if not best_team or not best_journey:
            return None

        submission = next((s for s in submissions if s.sub_id == best_team), None)
        if not submission:
            return None

        evidence = [
            f"Learned {best_journey.technology} during hackathon",
            f"Progression: {best_journey.progression}",
        ] + best_journey.evidence[:3]

        return PrizeRecommendation(
            prize_category="Most Improved / Best Learning Journey",
            recommended_team=submission.team_name,
            sub_id=best_team,
            justification=f"Impressive learning journey with {best_journey.technology}",
            evidence=evidence,
        )

    def _find_best_cicd(self, submissions: list[SubmissionResponse]) -> PrizeRecommendation | None:
        """Find team with best CI/CD practices.

        Args:
            submissions: All submissions

        Returns:
            Prize recommendation or None
        """
        best_team = None
        best_score = 0.0

        for submission in submissions:
            if not submission.repo_meta:
                continue

            # Calculate CI/CD score
            score = 0.0
            if submission.repo_meta and submission.repo_meta.has_ci:
                score += 30
            if submission.repo_meta.workflow_success_rate > 0:
                score += submission.repo_meta.workflow_success_rate * 40
            if submission.repo_meta.workflow_run_count > 0:
                score += min(submission.repo_meta.workflow_run_count * 2, 30)

            if score > best_score:
                best_score = score
                best_team = submission

        if not best_team or best_score < 50:
            return None

        evidence = [
            f"CI/CD enabled: {best_team.repo_meta.has_ci if best_team.repo_meta else False}",
            f"Workflow success rate: {(best_team.repo_meta.workflow_success_rate if best_team.repo_meta else 0.0):.1%}",
            f"Total workflow runs: {best_team.repo_meta.workflow_run_count if best_team.repo_meta else 0}",
        ]

        return PrizeRecommendation(
            prize_category="Best CI/CD Practices",
            recommended_team=best_team.team_name,
            sub_id=best_team.sub_id,
            justification="Outstanding CI/CD sophistication and automation",
            evidence=evidence,
        )

    def _identify_standout_moments(
        self,
        submissions: list[SubmissionResponse],
        team_analyses: dict[str, TeamAnalysisResult],
        strategy_analyses: dict[str, StrategyAnalysisResult],
    ) -> list[str]:
        """Highlight standout moments from the hackathon.

        Args:
            submissions: All submissions
            team_analyses: Team analysis results
            strategy_analyses: Strategy analysis results

        Returns:
            List of standout moment descriptions
        """
        moments = []

        # Find highest scoring team
        if submissions:
            top_submission = max(submissions, key=lambda s: s.overall_score or 0)
            moments.append(
                f"{top_submission.team_name} achieved highest score: {top_submission.overall_score:.1f}/100"
            )

        # Find most collaborative team
        for sub_id, team_analysis in team_analyses.items():
            if len(team_analysis.collaboration_patterns) >= 3:
                submission = next((s for s in submissions if s.sub_id == sub_id), None)
                if submission:
                    moments.append(
                        f"{submission.team_name} demonstrated exceptional collaboration with {len(team_analysis.collaboration_patterns)} positive patterns"
                    )
                    break

        # Find most innovative technology adoption
        for sub_id, strategy_analysis in strategy_analyses.items():
            if strategy_analysis.learning_journey and strategy_analysis.learning_journey.impressive:
                submission = next((s for s in submissions if s.sub_id == sub_id), None)
                if submission:
                    moments.append(
                        f"{submission.team_name} learned {strategy_analysis.learning_journey.technology} during the hackathon"
                    )
                    break

        return moments[:5]  # Return top 5 standout moments

    def _generate_next_hackathon_recommendations(
        self, common_issues: list[CommonIssue], technology_trends: TechnologyTrends
    ) -> list[str]:
        """Generate recommendations for next hackathon.

        Args:
            common_issues: Common issues identified
            technology_trends: Technology trends

        Returns:
            List of recommendations
        """
        recommendations = []

        # Recommend workshops based on common issues
        if common_issues:
            top_issue = common_issues[0]
            recommendations.append(
                f"Host pre-hackathon workshop: {top_issue.workshop_recommendation}"
            )

        # Recommend technology focus
        if technology_trends.most_used:
            top_tech = technology_trends.most_used[0][0]
            recommendations.append(f"Consider {top_tech}-focused track or prizes")

        # Recommend emerging tech support
        if technology_trends.emerging:
            recommendations.append(
                f"Provide mentorship for emerging technologies: {', '.join(technology_trends.emerging[:3])}"
            )

        # General recommendations
        recommendations.append("Encourage teams to set up CI/CD early in the hackathon")
        recommendations.append("Provide git collaboration best practices guide")

        return recommendations

    def _generate_sponsor_follow_up_actions(
        self,
        hiring_intelligence: HiringIntelligence,
        technology_trends: TechnologyTrends,
    ) -> list[str]:
        """Generate sponsor follow-up actions.

        Args:
            hiring_intelligence: Hiring intelligence data
            technology_trends: Technology trends

        Returns:
            List of follow-up actions
        """
        actions = []

        # Hiring leads
        must_interview_count = len(hiring_intelligence.must_interview)
        if must_interview_count > 0:
            actions.append(
                f"Share {must_interview_count} must-interview candidates with hiring sponsors"
            )

        # Technology insights
        if technology_trends.most_used:
            top_tech = technology_trends.most_used[0][0]
            actions.append(f"Highlight {top_tech} expertise in candidate pool")

        # Role-specific insights
        backend_count = len(hiring_intelligence.backend_candidates)
        frontend_count = len(hiring_intelligence.frontend_candidates)
        fullstack_count = len(hiring_intelligence.full_stack_candidates)

        actions.append(
            f"Candidate breakdown: {backend_count} backend, {frontend_count} frontend, {fullstack_count} full-stack"
        )

        return actions
