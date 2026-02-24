"""Analyzer Lambda entry point - orchestrates complete analysis pipeline."""

import asyncio
import json
import os
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from src.analysis.actions_analyzer import ActionsAnalyzer
from src.analysis.git_analyzer import clone_and_extract, parse_github_url
from src.analysis.orchestrator import AnalysisOrchestrator
from src.analysis.performance_monitor import (
    PERFORMANCE_TARGETS,
    PerformanceMonitor,
    log_performance_warning,
)
from src.models.common import AgentName, JobStatus, SubmissionStatus
from src.services.analysis_service import AnalysisService
from src.services.cost_service import CostService
from src.services.hackathon_service import HackathonService
from src.services.submission_service import SubmissionService
from src.utils.dynamo import DynamoDBHelper
from src.utils.logging import get_logger

logger = get_logger(__name__)


def handler(event: dict, context: Any) -> dict:
    """Lambda handler for analysis jobs.

    Args:
        event: Lambda event dict with job_id, hack_id, submission_ids
        context: Lambda context

    Returns:
        Response dict with job status
    """
    logger.info("analyzer_lambda_invoked", lambda_event=event)

    try:
        # Parse event
        job_id = event.get("job_id")
        hack_id = event.get("hack_id")
        submission_ids = event.get("submission_ids", [])

        if not job_id or not hack_id:
            logger.error("invalid_event", lambda_event=event)
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Missing job_id or hack_id"}),
            }

        logger.info(
            "analysis_job_started",
            job_id=job_id,
            hack_id=hack_id,
            submissions=len(submission_ids),
        )

        # Initialize services
        table_name = os.environ.get("TABLE_NAME", "VibeJudgeTable")
        db = DynamoDBHelper(table_name)

        hackathon_service = HackathonService(db)
        submission_service = SubmissionService(db)
        analysis_service = AnalysisService(db)
        cost_service = CostService(db)

        # Get hackathon config
        hackathon = hackathon_service.get_hackathon(hack_id)
        if not hackathon:
            logger.error("hackathon_not_found", hack_id=hack_id)
            return {
                "statusCode": 404,
                "body": json.dumps({"error": "Hackathon not found"}),
            }

        # Update job status to running
        analysis_service.update_job_status(
            hack_id=hack_id,
            job_id=job_id,
            status=JobStatus.RUNNING,
            started_at=datetime.now(UTC),
        )

        # Process each submission
        completed = 0
        failed = 0
        total_cost = Decimal("0.0")  # Use Decimal to match DynamoDB type

        for sub_id in submission_ids:
            try:
                logger.info("processing_submission", sub_id=sub_id)

                # Get submission
                submission = submission_service.get_submission(sub_id)
                if not submission:
                    logger.warning("submission_not_found", sub_id=sub_id)
                    failed += 1
                    continue

                # Update submission status
                submission_service.update_submission_status(
                    hack_id=hack_id,
                    sub_id=sub_id,
                    status=SubmissionStatus.ANALYZING,
                )

                # Analyze submission
                result = analyze_single_submission(
                    submission=submission,
                    hackathon=hackathon,
                    db=db,
                )

                if result["success"]:
                    # Check if submission was disqualified
                    if result.get("disqualified", False):
                        # Mark as disqualified
                        submission_service.update_submission_status(
                            hack_id=hack_id,
                            sub_id=sub_id,
                            status=SubmissionStatus.DISQUALIFIED,
                            error_message=result.get("disqualification_reason"),
                        )
                        logger.info(
                            "submission_disqualified",
                            sub_id=sub_id,
                            reason=result.get("disqualification_reason"),
                        )
                        # Count as completed (not failed) but with no score
                        completed += 1
                        continue

                    completed += 1
                    # Convert cost to Decimal to avoid type mismatch with DynamoDB
                    total_cost += Decimal(str(result["cost"]))

                    # Update submission with results
                    submission_service.update_submission_with_scores(
                        hack_id=hack_id,
                        sub_id=sub_id,
                        overall_score=result["overall_score"],
                        dimension_scores=result["dimension_scores"],
                        weighted_scores=result["weighted_scores"],
                        recommendation=result["recommendation"],
                        confidence=result["confidence"],
                        agent_scores=result["agent_scores"],
                        strengths=result["strengths"],
                        weaknesses=result["weaknesses"],
                        repo_meta=result["repo_meta"],
                        total_cost_usd=result["cost"],
                        total_tokens=result["tokens"],
                        analysis_duration_ms=result["duration_ms"],
                    )

                    # Store team analysis if available
                    if result.get("team_analysis"):
                        try:
                            team_analysis = result["team_analysis"]
                            db.put_team_analysis(
                                {
                                    "PK": f"SUB#{sub_id}",
                                    "SK": "TEAM_ANALYSIS",
                                    "entity_type": "TEAM_ANALYSIS",
                                    "sub_id": sub_id,
                                    "hack_id": hack_id,
                                    "workload_distribution": team_analysis.workload_distribution,
                                    "collaboration_patterns": [
                                        p.model_dump() for p in team_analysis.collaboration_patterns
                                    ],
                                    "red_flags": [f.model_dump() for f in team_analysis.red_flags],
                                    "individual_scorecards": [
                                        s.model_dump() for s in team_analysis.individual_scorecards
                                    ],
                                    "team_dynamics_grade": team_analysis.team_dynamics_grade,
                                    "commit_message_quality": team_analysis.commit_message_quality,
                                    "panic_push_detected": team_analysis.panic_push_detected,
                                    "duration_ms": team_analysis.duration_ms,
                                }
                            )
                            logger.info("team_analysis_stored", sub_id=sub_id)
                        except Exception as e:
                            logger.error(
                                "team_analysis_storage_failed", sub_id=sub_id, error=str(e)
                            )

                    # Store strategy analysis if available
                    if result.get("strategy_analysis"):
                        try:
                            strategy_analysis = result["strategy_analysis"]
                            db.put_strategy_analysis(
                                {
                                    "PK": f"SUB#{sub_id}",
                                    "SK": "STRATEGY_ANALYSIS",
                                    "entity_type": "STRATEGY_ANALYSIS",
                                    "sub_id": sub_id,
                                    "hack_id": hack_id,
                                    "test_strategy": strategy_analysis.test_strategy.value,
                                    "critical_path_focus": strategy_analysis.critical_path_focus,
                                    "tradeoffs": [
                                        t.model_dump() for t in strategy_analysis.tradeoffs
                                    ],
                                    "learning_journey": strategy_analysis.learning_journey.model_dump()
                                    if strategy_analysis.learning_journey
                                    else None,
                                    "maturity_level": strategy_analysis.maturity_level.value,
                                    "strategic_context": strategy_analysis.strategic_context,
                                    "duration_ms": strategy_analysis.duration_ms,
                                }
                            )
                            logger.info("strategy_analysis_stored", sub_id=sub_id)
                        except Exception as e:
                            logger.error(
                                "strategy_analysis_storage_failed", sub_id=sub_id, error=str(e)
                            )

                    # Store actionable feedback if available
                    if result.get("actionable_feedback"):
                        try:
                            actionable_feedback = result["actionable_feedback"]
                            db.put_actionable_feedback(
                                {
                                    "PK": f"SUB#{sub_id}",
                                    "SK": "ACTIONABLE_FEEDBACK",
                                    "entity_type": "ACTIONABLE_FEEDBACK",
                                    "sub_id": sub_id,
                                    "hack_id": hack_id,
                                    "feedback_items": [f.model_dump() for f in actionable_feedback],
                                    "total_count": len(actionable_feedback),
                                }
                            )
                            logger.info(
                                "actionable_feedback_stored",
                                sub_id=sub_id,
                                count=len(actionable_feedback),
                            )
                        except Exception as e:
                            logger.error(
                                "actionable_feedback_storage_failed", sub_id=sub_id, error=str(e)
                            )

                    # Record costs
                    for cost_record in result["cost_records"]:
                        agent_name_str = "unknown"
                        model_id = "unknown"
                        input_tokens = 0
                        output_tokens = 0

                        try:
                            # cost_record is a CostRecord Pydantic model
                            # Extract agent_name as string (handle both enum and string)
                            agent_name_str = (
                                cost_record.agent_name.value
                                if hasattr(cost_record.agent_name, "value")
                                else str(cost_record.agent_name)
                            )
                            model_id = cost_record.model_id
                            input_tokens = cost_record.input_tokens
                            output_tokens = cost_record.output_tokens

                            # Log diagnostic information BEFORE attempting to record cost
                            logger.info(
                                "recording_agent_cost",
                                sub_id=sub_id,
                                agent=agent_name_str,
                                model_id=model_id,
                                input_tokens=input_tokens,
                                output_tokens=output_tokens,
                                total_tokens=cost_record.total_tokens,
                            )

                            cost_service.record_agent_cost(
                                sub_id=sub_id,
                                agent_name=agent_name_str,
                                model_id=model_id,
                                input_tokens=input_tokens,
                                output_tokens=output_tokens,
                            )

                            # Log success
                            logger.info(
                                "cost_recorded_successfully",
                                sub_id=sub_id,
                                agent=agent_name_str,
                                model_id=model_id,
                            )

                        except Exception as e:
                            # Don't fail the entire analysis if cost recording fails
                            # Log detailed diagnostic information for debugging
                            logger.error(
                                "cost_recording_failed",
                                sub_id=sub_id,
                                agent=agent_name_str,
                                model_id=model_id,
                                input_tokens=input_tokens,
                                output_tokens=output_tokens,
                                tokens=input_tokens + output_tokens,
                                error=str(e),
                                error_type=type(e).__name__,
                            )

                    logger.info(
                        "submission_analyzed",
                        sub_id=sub_id,
                        score=result["overall_score"],
                        cost=result["cost"],
                    )
                else:
                    failed += 1
                    submission_service.update_submission_status(
                        hack_id=hack_id,
                        sub_id=sub_id,
                        status=SubmissionStatus.FAILED,
                        error_message=result.get("error", "Analysis failed"),
                    )
                    logger.error(
                        "submission_analysis_failed", sub_id=sub_id, error=result.get("error")
                    )

            except Exception as e:
                logger.error("submission_processing_error", sub_id=sub_id, error=str(e))
                failed += 1
                submission_service.update_submission_status(
                    hack_id=hack_id,
                    sub_id=sub_id,
                    status=SubmissionStatus.FAILED,
                    error_message=str(e),
                )

        # Update job status to completed
        analysis_service.update_job_status(
            hack_id=hack_id,
            job_id=job_id,
            status=JobStatus.COMPLETED,
            completed_at=datetime.now(UTC),
            completed_submissions=completed,
            failed_submissions=failed,
            total_cost_usd=total_cost,
        )

        # Update hackathon cost summary
        cost_service.update_hackathon_cost_summary(hack_id)

        logger.info(
            "analysis_job_completed",
            job_id=job_id,
            completed=completed,
            failed=failed,
            total_cost=float(total_cost),  # Convert to float for logging
        )

        return {
            "statusCode": 200,
            "body": json.dumps(
                {
                    "job_id": job_id,
                    "status": "completed",
                    "completed": completed,
                    "failed": failed,
                    "total_cost_usd": float(total_cost),  # Convert to float for JSON
                }
            ),
        }

    except Exception as e:
        logger.error("analyzer_lambda_error", error=str(e), lambda_event=event)

        # Try to update job status to failed
        if "job_id" in event and "hack_id" in event:
            try:
                db = DynamoDBHelper(os.environ.get("TABLE_NAME", "VibeJudgeTable"))
                analysis_service = AnalysisService(db)
                analysis_service.update_job_status(
                    hack_id=event["hack_id"],
                    job_id=event["job_id"],
                    status=JobStatus.FAILED,
                    error_message=str(e),
                )
            except Exception as update_error:
                logger.error("failed_to_update_job_status", error=str(update_error))

        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)}),
        }


def analyze_single_submission(
    submission: Any,
    hackathon: Any,
    db: DynamoDBHelper,
) -> dict:
    """Analyze a single submission.

    Args:
        submission: Submission object
        hackathon: Hackathon object
        db: DynamoDB helper

    Returns:
        Dict with analysis results or error
    """
    try:
        # Initialize performance monitor
        perf_monitor = PerformanceMonitor(submission.sub_id)

        # Extract repo data
        logger.info("extracting_repo_data", sub_id=submission.sub_id, repo=submission.repo_url)

        # Parse GitHub URL
        owner, repo_name = parse_github_url(submission.repo_url)

        # Fetch GitHub Actions data
        with perf_monitor.track("actions_analyzer"):
            actions_analyzer = ActionsAnalyzer()
            actions_data = actions_analyzer.analyze(owner, repo_name)
            actions_analyzer.close()

        # Check for disqualification
        if actions_data.get("disqualified", False):
            disqualification_reason = actions_data.get("disqualification_reason")
            logger.warning(
                "submission_disqualified",
                sub_id=submission.sub_id,
                reason=disqualification_reason,
            )
            return {
                "success": True,
                "disqualified": True,
                "disqualification_reason": disqualification_reason,
            }

        # Clone and extract repository
        with perf_monitor.track("git_clone_and_extract"):
            repo_data = clone_and_extract(
                repo_url=submission.repo_url,
                submission_id=submission.sub_id,
                workflow_runs=actions_data["workflow_runs"],
                workflow_definitions=actions_data["workflow_definitions"],
            )

        logger.info("repo_data_extracted", sub_id=submission.sub_id)

        # Check if we're at risk of timeout after git operations
        if perf_monitor.check_timeout_risk():
            logger.warning(
                "timeout_risk_after_git",
                sub_id=submission.sub_id,
                elapsed_ms=perf_monitor.get_total_duration_ms(),
            )

        # Build context for agents
        hackathon.rubric.model_dump_json(indent=2)

        # Note: We don't use build_context here because agents build their own context
        # The orchestrator passes repo_data directly to agents

        # Run orchestrator
        logger.info("running_orchestrator", sub_id=submission.sub_id)
        orchestrator = AnalysisOrchestrator()

        # Convert agent names from strings to AgentName enums
        agents_enabled = []
        for agent in hackathon.agents_enabled:
            if isinstance(agent, str):
                agents_enabled.append(AgentName(agent))
            else:
                agents_enabled.append(agent)

        # Run analysis (async) with performance tracking
        with perf_monitor.track("orchestrator_analysis"):
            result = asyncio.run(
                orchestrator.analyze_submission(
                    repo_data=repo_data,
                    hackathon_name=hackathon.name,
                    team_name=submission.team_name,
                    hack_id=hackathon.hack_id,
                    sub_id=submission.sub_id,
                    rubric=hackathon.rubric,
                    agents_enabled=agents_enabled,
                    ai_policy_mode=hackathon.ai_policy_mode.value
                    if hasattr(hackathon.ai_policy_mode, "value")
                    else str(hackathon.ai_policy_mode),
                )
            )

        logger.info(
            "orchestrator_complete", sub_id=submission.sub_id, score=result["overall_score"]
        )

        # Log performance summary
        perf_summary = perf_monitor.get_summary()
        logger.info(
            "performance_summary",
            sub_id=submission.sub_id,
            **perf_summary,
        )

        # Check individual component performance against targets
        for component, duration_ms in perf_monitor.timings.items():
            if component in PERFORMANCE_TARGETS:
                log_performance_warning(
                    component=component,
                    duration_ms=duration_ms,
                    target_ms=PERFORMANCE_TARGETS[component],
                )

        # Build agent_scores dict for storage
        agent_scores = {}
        for agent_name, response in result["agent_responses"].items():
            agent_key = agent_name.value if hasattr(agent_name, "value") else str(agent_name)
            agent_scores[agent_key] = response.model_dump()

        # Build dimension_scores dict
        dimension_scores = {}
        for dim_name, weighted_score in result["weighted_scores"].items():
            dimension_scores[dim_name] = weighted_score.weighted

        return {
            "success": True,
            "overall_score": result["overall_score"],
            "dimension_scores": dimension_scores,
            "weighted_scores": result["weighted_scores"],
            "recommendation": result["recommendation"],
            "confidence": result["confidence"],
            "agent_scores": agent_scores,
            "strengths": result["strengths"],
            "weaknesses": result["weaknesses"],
            "repo_meta": repo_data.meta.model_dump(),
            "cost": result["total_cost_usd"],
            "tokens": result["total_tokens"],
            "duration_ms": result["analysis_duration_ms"],
            "cost_records": result["cost_records"],
        }

    except Exception as e:
        logger.error("submission_analysis_error", sub_id=submission.sub_id, error=str(e))
        return {
            "success": False,
            "error": str(e),
        }
