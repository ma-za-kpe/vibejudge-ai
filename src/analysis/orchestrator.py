"""Multi-agent orchestration with parallel execution."""

import asyncio
from datetime import UTC, datetime
from typing import Any

from src.agents.ai_detection import AIDetectionAgent
from src.agents.bug_hunter import BugHunterAgent
from src.agents.innovation import InnovationScorerAgent
from src.agents.performance import PerformanceAnalyzerAgent
from src.analysis.actions_analyzer import ActionsAnalyzer
from src.analysis.brand_voice_transformer import BrandVoiceTransformer
from src.analysis.cost_tracker import CostTracker
from src.analysis.strategy_detector import StrategyDetector
from src.analysis.team_analyzer import TeamAnalyzer
from src.constants import RECOMMENDATION_THRESHOLDS
from src.models.analysis import RepoData
from src.models.common import AgentName, Recommendation
from src.models.hackathon import RubricConfig
from src.models.scores import BaseAgentResponse
from src.models.submission import WeightedDimensionScore
from src.utils.bedrock import BedrockClient
from src.utils.logging import get_logger

logger = get_logger(__name__)


class AnalysisOrchestrator:
    """Orchestrate multi-agent analysis with parallel execution."""

    def __init__(self, bedrock_client: BedrockClient | None = None):
        """Initialize orchestrator.

        Args:
            bedrock_client: Optional shared Bedrock client
        """
        self.bedrock = bedrock_client or BedrockClient()
        self.cost_tracker = CostTracker()

        # Initialize agents
        self.agents = {
            AgentName.BUG_HUNTER: BugHunterAgent(self.bedrock),
            AgentName.PERFORMANCE: PerformanceAnalyzerAgent(self.bedrock),
            AgentName.INNOVATION: InnovationScorerAgent(self.bedrock),
            AgentName.AI_DETECTION: AIDetectionAgent(self.bedrock),
        }

        # Initialize new intelligence components
        self.team_analyzer = TeamAnalyzer()
        self.strategy_detector = StrategyDetector()
        self.brand_voice_transformer = BrandVoiceTransformer()

    async def analyze_submission(
        self,
        repo_data: RepoData,
        hackathon_name: str,
        team_name: str,
        hack_id: str,
        sub_id: str,
        rubric: RubricConfig,
        agents_enabled: list[AgentName],
        ai_policy_mode: str = "ai_assisted",
        github_token: str | None = None,
    ) -> dict[str, Any]:
        """Analyze a submission with multiple agents in parallel.

        Args:
            repo_data: Extracted repository data
            hackathon_name: Name of the hackathon
            team_name: Name of the team
            hack_id: Hackathon ID
            sub_id: Submission ID
            rubric: Rubric configuration
            agents_enabled: List of enabled agents
            ai_policy_mode: AI policy mode
            github_token: Optional GitHub token for CI/CD analysis

        Returns:
            Dict with:
                - agent_responses: Dict of agent responses
                - overall_score: Weighted aggregate score
                - weighted_scores: Per-dimension weighted scores
                - recommendation: Classification
                - confidence: Minimum confidence across agents
                - cost_records: List of cost records
                - total_cost_usd: Total cost
                - analysis_duration_ms: Total duration
                - team_analysis: Team dynamics analysis result
                - strategy_analysis: Strategy detection result
                - actionable_feedback: Transformed feedback items
        """
        start_time = datetime.now(UTC)

        logger.info(
            "orchestrator_analysis_started",
            sub_id=sub_id,
            team=team_name,
            agents=len(agents_enabled),
        )

        # Step 1: Parse CI/CD logs for static findings and test results
        cicd_findings = None
        test_results_from_logs = None
        cicd_start = datetime.now(UTC)

        if github_token and repo_data.repo_url:
            try:
                # Extract owner/repo from URL
                parts = repo_data.repo_url.rstrip("/").split("/")
                if len(parts) >= 2:
                    owner, repo = parts[-2], parts[-1]

                    logger.info(
                        "parsing_cicd_logs",
                        sub_id=sub_id,
                        owner=owner,
                        repo=repo,
                    )

                    actions_analyzer = ActionsAnalyzer(github_token)
                    cicd_analysis = actions_analyzer.analyze(owner, repo)
                    actions_analyzer.close()

                    cicd_findings = cicd_analysis.get("linter_findings", [])
                    test_results_from_logs = cicd_analysis.get("test_results")

                    # Track component performance
                    cicd_duration_ms = int((datetime.now(UTC) - cicd_start).total_seconds() * 1000)
                    self.cost_tracker.record_component_performance(
                        sub_id=sub_id,
                        hack_id=hack_id,
                        component_name="actions_analyzer",
                        duration_ms=cicd_duration_ms,
                        findings_count=len(cicd_findings) if cicd_findings else 0,
                        success=True,
                    )

                    logger.info(
                        "cicd_logs_parsed",
                        sub_id=sub_id,
                        findings_count=len(cicd_findings) if cicd_findings else 0,
                        test_results_found=test_results_from_logs is not None,
                        duration_ms=cicd_duration_ms,
                    )
            except Exception as e:
                cicd_duration_ms = int((datetime.now(UTC) - cicd_start).total_seconds() * 1000)
                self.cost_tracker.record_component_performance(
                    sub_id=sub_id,
                    hack_id=hack_id,
                    component_name="actions_analyzer",
                    duration_ms=cicd_duration_ms,
                    findings_count=0,
                    success=False,
                    error_message=str(e),
                )
                logger.warning(
                    "cicd_parsing_failed",
                    sub_id=sub_id,
                    error=str(e),
                )

        # Step 2: Run team dynamics analysis
        team_analysis = None
        team_start = datetime.now(UTC)
        try:
            logger.info("running_team_analysis", sub_id=sub_id)
            team_analysis = self.team_analyzer.analyze(repo_data)

            # Track component performance
            team_duration_ms = int((datetime.now(UTC) - team_start).total_seconds() * 1000)
            self.cost_tracker.record_component_performance(
                sub_id=sub_id,
                hack_id=hack_id,
                component_name="team_analyzer",
                duration_ms=team_duration_ms,
                findings_count=len(team_analysis.individual_scorecards)
                + len(team_analysis.red_flags),
                success=True,
            )

            logger.info(
                "team_analysis_completed",
                sub_id=sub_id,
                grade=team_analysis.team_dynamics_grade,
                red_flags=len(team_analysis.red_flags),
                duration_ms=team_duration_ms,
            )
        except Exception as e:
            team_duration_ms = int((datetime.now(UTC) - team_start).total_seconds() * 1000)
            self.cost_tracker.record_component_performance(
                sub_id=sub_id,
                hack_id=hack_id,
                component_name="team_analyzer",
                duration_ms=team_duration_ms,
                findings_count=0,
                success=False,
                error_message=str(e),
            )
            logger.error(
                "team_analysis_failed",
                sub_id=sub_id,
                error=str(e),
            )

        # Step 3: Run strategy detection
        strategy_analysis = None
        strategy_start = datetime.now(UTC)
        try:
            logger.info("running_strategy_detection", sub_id=sub_id)
            strategy_analysis = self.strategy_detector.analyze(
                repo_data=repo_data,
                test_results=test_results_from_logs,
                static_findings=cicd_findings,
            )

            # Track component performance
            strategy_duration_ms = int((datetime.now(UTC) - strategy_start).total_seconds() * 1000)
            self.cost_tracker.record_component_performance(
                sub_id=sub_id,
                hack_id=hack_id,
                component_name="strategy_detector",
                duration_ms=strategy_duration_ms,
                findings_count=len(strategy_analysis.tradeoffs),
                success=True,
            )

            logger.info(
                "strategy_detection_completed",
                sub_id=sub_id,
                test_strategy=strategy_analysis.test_strategy,
                maturity_level=strategy_analysis.maturity_level,
                duration_ms=strategy_duration_ms,
            )
        except Exception as e:
            strategy_duration_ms = int((datetime.now(UTC) - strategy_start).total_seconds() * 1000)
            self.cost_tracker.record_component_performance(
                sub_id=sub_id,
                hack_id=hack_id,
                component_name="strategy_detector",
                duration_ms=strategy_duration_ms,
                findings_count=0,
                success=False,
                error_message=str(e),
            )
            logger.error(
                "strategy_detection_failed",
                sub_id=sub_id,
                error=str(e),
            )

        # Step 4: Run agents in parallel (with static context)
        tasks = []
        for agent_name in agents_enabled:
            if agent_name not in self.agents:
                logger.warning("agent_not_found", agent=agent_name)
                continue

            task = self._run_agent_async(
                agent_name=agent_name,
                repo_data=repo_data,
                hackathon_name=hackathon_name,
                team_name=team_name,
                hack_id=hack_id,
                sub_id=sub_id,
                ai_policy_mode=ai_policy_mode,
                static_findings=cicd_findings,
            )
            tasks.append(task)

        # Wait for all agents to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        agent_responses = {}
        failed_agents = []

        for i, result in enumerate(results):
            agent_name = agents_enabled[i]

            if isinstance(result, Exception):
                logger.error(
                    "agent_failed",
                    agent=agent_name,
                    error=str(result),
                )
                failed_agents.append(agent_name)
            else:
                agent_responses[agent_name] = result

        # Check if we have enough successful agents
        if len(agent_responses) == 0:
            raise ValueError("All agents failed - cannot complete analysis")

        if len(failed_agents) > 0:
            logger.warning(
                "partial_analysis",
                failed_agents=failed_agents,
                successful=len(agent_responses),
            )

        # Aggregate scores
        aggregation = self._aggregate_scores(
            agent_responses=agent_responses,
            rubric=rubric,
        )

        # Step 5: Transform feedback with brand voice
        actionable_feedback = []
        feedback_start = datetime.now(UTC)
        try:
            if agent_responses:
                logger.info("transforming_feedback", sub_id=sub_id)

                # Collect all findings from agents
                all_findings = []
                for _agent_name, response in agent_responses.items():
                    if hasattr(response, "evidence") and response.evidence:
                        all_findings.extend(response.evidence)

                # Transform findings with brand voice
                actionable_feedback = self.brand_voice_transformer.transform_findings(
                    findings=all_findings,
                    strategy_context=strategy_analysis,
                )

                # Track component performance
                feedback_duration_ms = int(
                    (datetime.now(UTC) - feedback_start).total_seconds() * 1000
                )
                self.cost_tracker.record_component_performance(
                    sub_id=sub_id,
                    hack_id=hack_id,
                    component_name="brand_voice_transformer",
                    duration_ms=feedback_duration_ms,
                    findings_count=len(actionable_feedback),
                    success=True,
                )

                logger.info(
                    "feedback_transformed",
                    sub_id=sub_id,
                    feedback_items=len(actionable_feedback),
                    duration_ms=feedback_duration_ms,
                )
        except Exception as e:
            feedback_duration_ms = int((datetime.now(UTC) - feedback_start).total_seconds() * 1000)
            self.cost_tracker.record_component_performance(
                sub_id=sub_id,
                hack_id=hack_id,
                component_name="brand_voice_transformer",
                duration_ms=feedback_duration_ms,
                findings_count=0,
                success=False,
                error_message=str(e),
            )
            logger.error(
                "feedback_transformation_failed",
                sub_id=sub_id,
                error=str(e),
            )

        # Calculate duration
        duration_ms = int((datetime.now(UTC) - start_time).total_seconds() * 1000)

        result = {
            "agent_responses": agent_responses,
            "overall_score": aggregation["overall_score"],
            "weighted_scores": aggregation["weighted_scores"],
            "recommendation": aggregation["recommendation"],
            "confidence": aggregation["confidence"],
            "strengths": aggregation["strengths"],
            "weaknesses": aggregation["weaknesses"],
            "cost_records": self.cost_tracker.get_records(),
            "component_performance": self.cost_tracker.get_component_records(),
            "total_cost_usd": self.cost_tracker.get_total_cost(),
            "total_tokens": self.cost_tracker.get_total_tokens(),
            "total_component_duration_ms": self.cost_tracker.get_total_component_duration_ms(),
            "analysis_duration_ms": duration_ms,
            "failed_agents": failed_agents,
            # New intelligence layer results
            "team_analysis": team_analysis,
            "strategy_analysis": strategy_analysis,
            "actionable_feedback": actionable_feedback,
            "cicd_findings_count": len(cicd_findings) if cicd_findings else 0,
        }

        logger.info(
            "orchestrator_analysis_completed",
            sub_id=sub_id,
            overall_score=result["overall_score"],
            cost_usd=result["total_cost_usd"],
            duration_ms=duration_ms,
            team_grade=team_analysis.team_dynamics_grade if team_analysis else None,
            feedback_items=len(actionable_feedback),
        )

        return result

    async def _run_agent_async(
        self,
        agent_name: AgentName,
        repo_data: RepoData,
        hackathon_name: str,
        team_name: str,
        hack_id: str,
        sub_id: str,
        ai_policy_mode: str,
        static_findings: list | None = None,
    ) -> BaseAgentResponse:
        """Run a single agent asynchronously.

        Args:
            agent_name: Agent to run
            repo_data: Repository data
            hackathon_name: Hackathon name
            team_name: Team name
            hack_id: Hackathon ID
            sub_id: Submission ID
            ai_policy_mode: AI policy mode
            static_findings: Optional static analysis findings from CI/CD logs

        Returns:
            Agent response
        """
        # Run agent in thread pool (Bedrock SDK is synchronous)
        loop = asyncio.get_event_loop()
        agent = self.agents[agent_name]

        # Build kwargs for agent
        kwargs = {}
        if agent_name == AgentName.AI_DETECTION:
            kwargs["ai_policy_mode"] = ai_policy_mode

        # Pass static findings to reduce agent scope (avoid duplicate work)
        if static_findings:
            kwargs["static_context"] = {
                "findings_count": len(static_findings),
                "findings": static_findings[:20],  # Top 20 to stay within token budget
            }

        # Use lambda to pass kwargs to analyze
        response, usage = await loop.run_in_executor(
            None,
            lambda: agent.analyze(repo_data, hackathon_name, team_name, **kwargs),
        )

        # Record cost
        self.cost_tracker.record_agent_cost(
            sub_id=sub_id,
            hack_id=hack_id,
            agent_name=agent_name,
            model_id=agent.model_id,
            input_tokens=usage["input_tokens"],
            output_tokens=usage["output_tokens"],
            latency_ms=usage["latency_ms"],
        )

        return response

    def _aggregate_scores(
        self,
        agent_responses: dict[AgentName, BaseAgentResponse],
        rubric: RubricConfig,
    ) -> dict[str, Any]:
        """Aggregate agent scores using rubric weights.

        Args:
            agent_responses: Dict of agent responses
            rubric: Rubric configuration

        Returns:
            Dict with overall_score, weighted_scores, recommendation, confidence
        """
        weighted_scores = {}
        weighted_total = 0.0
        min_confidence = 1.0

        # Calculate weighted scores per dimension
        for dimension in rubric.dimensions:
            agent_name = dimension.agent

            if agent_name not in agent_responses:
                # Agent failed - skip this dimension
                logger.warning(
                    "dimension_skipped_agent_failed",
                    dimension=dimension.name,
                    agent=agent_name,
                )
                continue

            agent_response = agent_responses[agent_name]
            raw_score = agent_response.overall_score
            weight = dimension.weight
            weighted = raw_score * weight * 10  # Scale to 0-100

            weighted_scores[dimension.name] = WeightedDimensionScore(
                raw=raw_score,
                weight=weight,
                weighted=round(weighted, 2),
            )

            weighted_total += weighted
            min_confidence = min(min_confidence, agent_response.confidence)

        # Calculate overall score (0-100 scale)
        overall_score = round(weighted_total, 2)

        # Determine recommendation
        recommendation = self._classify_score(overall_score)

        # Collect strengths and weaknesses
        strengths = []
        weaknesses = []

        for agent_response in agent_responses.values():
            if hasattr(agent_response, "strengths"):
                strengths.extend(agent_response.strengths[:2])
            if hasattr(agent_response, "improvements"):
                weaknesses.extend(agent_response.improvements[:2])

        # Deduplicate and limit
        strengths = list(dict.fromkeys(strengths))[:5]
        weaknesses = list(dict.fromkeys(weaknesses))[:5]

        return {
            "overall_score": overall_score,
            "weighted_scores": weighted_scores,
            "recommendation": recommendation,
            "confidence": round(min_confidence, 2),
            "strengths": strengths,
            "weaknesses": weaknesses,
        }

    def _classify_score(self, score: float) -> Recommendation:
        """Classify score into recommendation category.

        Args:
            score: Overall score (0-100)

        Returns:
            Recommendation enum
        """
        score_0_10 = score / 10  # Convert to 0-10 scale for thresholds

        if score_0_10 >= RECOMMENDATION_THRESHOLDS["strong_contender"]:
            return Recommendation.STRONG_CONTENDER
        elif score_0_10 >= RECOMMENDATION_THRESHOLDS["solid_submission"]:
            return Recommendation.SOLID_SUBMISSION
        elif score_0_10 >= RECOMMENDATION_THRESHOLDS["needs_improvement"]:
            return Recommendation.NEEDS_IMPROVEMENT
        else:
            return Recommendation.CONCERNS_FLAGGED
