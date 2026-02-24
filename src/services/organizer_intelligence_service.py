"""Organizer intelligence dashboard service."""

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
from src.models.team_dynamics import ContributorRole
from src.services.hackathon_service import HackathonService
from src.services.submission_service import SubmissionService
from src.utils.dynamo import DynamoDBHelper

logger = structlog.get_logger()


class OrganizerIntelligenceService:
    """Generates organizer intelligence dashboard."""

    def __init__(
        self,
        db: DynamoDBHelper,
        hackathon_service: HackathonService,
        submission_service: SubmissionService,
    ):
        """Initialize service.

        Args:
            db: DynamoDB helper instance
            hackathon_service: Hackathon service instance
            submission_service: Submission service instance
        """
        self.db = db
        self.hackathon_service = hackathon_service
        self.submission_service = submission_service

    def generate_dashboard(self, hack_id: str) -> OrganizerDashboard:
        """Generate intelligence dashboard for hackathon.

        Args:
            hack_id: Hackathon ID

        Returns:
            OrganizerDashboard with aggregated insights

        Raises:
            ValueError: If hackathon not found
        """
        logger.info("generating_organizer_dashboard", hack_id=hack_id)

        # Get hackathon details
        hackathon = self.hackathon_service.get_hackathon(hack_id)
        if not hackathon:
            raise ValueError(f"Hackathon not found: {hack_id}")

        # Get all submissions
        submissions_response = self.submission_service.list_submissions(hack_id)
        submissions = submissions_response.submissions

        # Filter to analyzed submissions only
        analyzed_submissions = [s for s in submissions if s.overall_score is not None]

        logger.info(
            "dashboard_data_loaded",
            hack_id=hack_id,
            total_submissions=len(submissions),
            analyzed_submissions=len(analyzed_submissions),
        )

        # Generate dashboard components
        top_performers = self._aggregate_top_performers(analyzed_submissions)
        hiring_intelligence = self._generate_hiring_intelligence(analyzed_submissions)
        technology_trends = self._analyze_technology_trends(analyzed_submissions)
        common_issues = self._identify_common_issues(analyzed_submissions)
        prize_recommendations = self._recommend_prizes(analyzed_submissions)
        standout_moments = self._identify_standout_moments(analyzed_submissions)
        next_hackathon_recommendations = self._generate_next_hackathon_recommendations(
            common_issues, technology_trends
        )
        sponsor_follow_up_actions = self._generate_sponsor_follow_up_actions(
            analyzed_submissions, technology_trends
        )

        dashboard = OrganizerDashboard(
            hack_id=hack_id,
            hackathon_name=hackathon.name,
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

        logger.info("dashboard_generated", hack_id=hack_id)
        return dashboard

    def _aggregate_top_performers(self, submissions: list) -> list[TopPerformer]:
        """Identify top teams with key strengths.

        Args:
            submissions: List of analyzed submissions

        Returns:
            List of top performers (top 10)
        """
        if not submissions:
            return []

        # Sort by overall score
        sorted_submissions = sorted(submissions, key=lambda x: x.overall_score or 0, reverse=True)

        top_performers = []
        for submission in sorted_submissions[:10]:  # Top 10
            # Extract key strengths from scorecard if available
            key_strengths = []
            sponsor_interest_flags = []

            # Try to get full submission details for more context
            full_submission = self.submission_service.get_submission(submission.sub_id)
            if full_submission and full_submission.team_analysis:
                # Extract strengths from team analysis if available
                team_analysis = full_submission.team_analysis
                if hasattr(team_analysis, "key_strengths"):
                    key_strengths = team_analysis.key_strengths[:3]  # Top 3 strengths

            # Default strengths based on scores
            if not key_strengths:
                key_strengths = [f"Overall Score: {submission.overall_score:.1f}"]

            top_performers.append(
                TopPerformer(
                    team_name=submission.team_name,
                    sub_id=submission.sub_id,
                    overall_score=submission.overall_score or 0.0,
                    key_strengths=key_strengths,
                    sponsor_interest_flags=sponsor_interest_flags,
                )
            )

        return top_performers

    def _generate_hiring_intelligence(self, submissions: list) -> HiringIntelligence:
        """Categorize candidates by role and seniority.

        Args:
            submissions: List of analyzed submissions

        Returns:
            HiringIntelligence with categorized candidates
        """
        backend_candidates = []
        frontend_candidates = []
        devops_candidates = []
        full_stack_candidates = []
        must_interview = []

        for submission in submissions:
            # Try to get individual scorecards from full submission
            full_submission = self.submission_service.get_submission(submission.sub_id)
            if not full_submission or not full_submission.team_analysis:
                continue

            team_analysis = full_submission.team_analysis
            if not hasattr(team_analysis, "individual_scorecards"):
                continue

            for scorecard in team_analysis.individual_scorecards:
                # Categorize by role
                if scorecard.role == ContributorRole.BACKEND:
                    backend_candidates.append(scorecard)
                elif scorecard.role == ContributorRole.FRONTEND:
                    frontend_candidates.append(scorecard)
                elif scorecard.role == ContributorRole.DEVOPS:
                    devops_candidates.append(scorecard)
                elif scorecard.role == ContributorRole.FULL_STACK:
                    full_stack_candidates.append(scorecard)

                # Check if must interview
                if (
                    hasattr(scorecard, "hiring_signals")
                    and scorecard.hiring_signals
                    and scorecard.hiring_signals.must_interview
                ):
                    must_interview.append(scorecard)

        return HiringIntelligence(
            backend_candidates=backend_candidates[:20],  # Limit to top 20 per category
            frontend_candidates=frontend_candidates[:20],
            devops_candidates=devops_candidates[:20],
            full_stack_candidates=full_stack_candidates[:20],
            must_interview=must_interview[:10],  # Top 10 must-interview
        )

    def _analyze_technology_trends(self, submissions: list) -> TechnologyTrends:
        """Identify popular stacks and emerging tech.

        Args:
            submissions: List of analyzed submissions

        Returns:
            TechnologyTrends with usage statistics
        """
        language_counter = Counter()
        Counter()
        Counter()

        for submission in submissions:
            # Try to extract technology info from repo data
            full_submission = self.submission_service.get_submission(submission.sub_id)
            if not full_submission:
                continue

            # Extract from static analysis if available
            if full_submission.static_analysis:
                language = full_submission.static_analysis.language
                if language:
                    language_counter[language] += 1

            # Extract from repo metadata if available
            if hasattr(full_submission, "repo_metadata"):
                repo_metadata = full_submission.repo_metadata
                if hasattr(repo_metadata, "primary_language"):
                    language_counter[repo_metadata.primary_language] += 1

        # Most used technologies
        most_used = language_counter.most_common(10)

        # Emerging technologies (used by 2-5 teams)
        emerging = [tech for tech, count in language_counter.items() if 2 <= count <= 5]

        # Popular stacks (for now, just language combinations)
        popular_stacks = []

        return TechnologyTrends(
            most_used=most_used,
            emerging=emerging,
            popular_stacks=popular_stacks,
        )

    def _identify_common_issues(self, submissions: list) -> list[CommonIssue]:
        """Find patterns across submissions.

        Args:
            submissions: List of analyzed submissions

        Returns:
            List of common issues with workshop recommendations
        """
        issue_counter = defaultdict(list)

        for submission in submissions:
            full_submission = self.submission_service.get_submission(submission.sub_id)
            if not full_submission or not full_submission.static_analysis:
                continue

            # Count issues by category
            static_analysis = full_submission.static_analysis
            for finding in static_analysis.findings:
                issue_counter[finding.category].append(submission.team_name)

        # Convert to CommonIssue objects
        common_issues = []
        total_submissions = len(submissions) if submissions else 1

        for issue_type, teams in issue_counter.items():
            if len(teams) >= 3:  # At least 3 teams affected
                percentage_affected = (len(teams) / total_submissions) * 100

                # Generate workshop recommendation
                workshop_recommendation = self._generate_workshop_recommendation(issue_type)

                common_issues.append(
                    CommonIssue(
                        issue_type=issue_type,
                        percentage_affected=percentage_affected,
                        workshop_recommendation=workshop_recommendation,
                        example_teams=teams[:5],  # First 5 teams as examples
                    )
                )

        # Sort by percentage affected
        common_issues.sort(key=lambda x: x.percentage_affected, reverse=True)

        return common_issues[:10]  # Top 10 common issues

    def _generate_workshop_recommendation(self, issue_type: str) -> str:
        """Generate workshop recommendation for issue type.

        Args:
            issue_type: Type of issue

        Returns:
            Workshop recommendation text
        """
        recommendations = {
            "security": "Workshop: Secure Coding Practices - OWASP Top 10",
            "testing": "Workshop: Test-Driven Development and Testing Strategies",
            "style": "Workshop: Code Quality and Style Guidelines",
            "complexity": "Workshop: Refactoring and Code Simplification",
            "import": "Workshop: Dependency Management Best Practices",
            "syntax": "Workshop: Language Fundamentals and Common Pitfalls",
        }

        return recommendations.get(issue_type, f"Workshop: Best Practices for {issue_type.title()}")

    def _recommend_prizes(self, submissions: list) -> list[PrizeRecommendation]:
        """Recommend prize winners with evidence.

        Args:
            submissions: List of analyzed submissions

        Returns:
            List of prize recommendations
        """
        if not submissions:
            return []

        recommendations = []

        # Best Overall
        best_overall = max(submissions, key=lambda x: x.overall_score or 0)
        recommendations.append(
            PrizeRecommendation(
                prize_category="Best Overall",
                recommended_team=best_overall.team_name,
                sub_id=best_overall.sub_id,
                justification=f"Highest overall score: {best_overall.overall_score:.1f}",
                evidence=[f"Overall Score: {best_overall.overall_score:.1f}"],
            )
        )

        # Best Team Dynamics (if team analysis available)
        teams_with_dynamics = []
        for submission in submissions:
            full_submission = self.submission_service.get_submission(submission.sub_id)
            if full_submission and full_submission.team_analysis:
                team_analysis = full_submission.team_analysis
                if hasattr(team_analysis, "team_dynamics_grade"):
                    teams_with_dynamics.append((submission, team_analysis))

        if teams_with_dynamics:
            best_team = max(
                teams_with_dynamics,
                key=lambda x: self._grade_to_score(x[1].team_dynamics_grade),
            )
            recommendations.append(
                PrizeRecommendation(
                    prize_category="Best Team Dynamics",
                    recommended_team=best_team[0].team_name,
                    sub_id=best_team[0].sub_id,
                    justification=f"Excellent collaboration and teamwork (Grade: {best_team[1].team_dynamics_grade})",
                    evidence=[f"Team Dynamics Grade: {best_team[1].team_dynamics_grade}"],
                )
            )

        return recommendations

    def _grade_to_score(self, grade: str) -> float:
        """Convert letter grade to numeric score.

        Args:
            grade: Letter grade (A-F)

        Returns:
            Numeric score (0-100)
        """
        grade_map = {"A": 95, "B": 85, "C": 75, "D": 65, "F": 50}
        return grade_map.get(grade, 0)

    def _identify_standout_moments(self, submissions: list) -> list[str]:
        """Identify standout moments across submissions.

        Args:
            submissions: List of analyzed submissions

        Returns:
            List of standout moment descriptions
        """
        standout_moments = []

        if not submissions:
            return standout_moments

        # Most creative API use
        # Most improved team
        # Best learning journey

        # For now, return placeholder moments
        if len(submissions) >= 3:
            standout_moments.append(
                f"{len(submissions)} teams participated with diverse technical approaches"
            )

        return standout_moments

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
            recommendations.append(f"Pre-hackathon workshop: {top_issue.workshop_recommendation}")

        # Recommend technology focus
        if technology_trends.most_used:
            top_tech = technology_trends.most_used[0][0]
            recommendations.append(f"Consider {top_tech}-focused track or prizes")

        # Recommend emerging tech support
        if technology_trends.emerging:
            recommendations.append(
                f"Provide resources for emerging technologies: {', '.join(technology_trends.emerging[:3])}"
            )

        return recommendations

    def _generate_sponsor_follow_up_actions(
        self, submissions: list, technology_trends: TechnologyTrends
    ) -> list[str]:
        """Generate sponsor follow-up actions.

        Args:
            submissions: List of analyzed submissions
            technology_trends: Technology trends

        Returns:
            List of follow-up actions
        """
        actions = []

        if submissions:
            actions.append(
                f"Share hiring intelligence report with {len(submissions)} candidate profiles"
            )

        if technology_trends.most_used:
            top_tech = technology_trends.most_used[0][0]
            actions.append(f"Highlight {top_tech} expertise in candidate pool")

        return actions
