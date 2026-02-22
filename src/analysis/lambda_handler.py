"""Analyzer Lambda entry point - orchestrates complete analysis pipeline."""

import asyncio
import json
import os
from datetime import UTC, datetime
from typing import Any

from src.analysis.actions_analyzer import ActionsAnalyzer
from src.analysis.git_analyzer import clone_and_extract, parse_github_url
from src.analysis.orchestrator import AnalysisOrchestrator
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
        total_cost = 0.0

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
                    completed += 1
                    total_cost += float(result["cost"])  # Convert to float to avoid Decimal issues

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

                    # Record costs
                    for cost_record in result["cost_records"]:
                        # cost_record is a CostRecord Pydantic model, not a dict
                        cost_service.record_agent_cost(
                            sub_id=sub_id,
                            agent_name=cost_record.agent_name.value if hasattr(cost_record.agent_name, 'value') else str(cost_record.agent_name),
                            model_id=cost_record.model_id,
                            input_tokens=cost_record.input_tokens,
                            output_tokens=cost_record.output_tokens,
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
                    logger.error("submission_analysis_failed", sub_id=sub_id, error=result.get("error"))

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
            total_cost=total_cost,
        )

        return {
            "statusCode": 200,
            "body": json.dumps({
                "job_id": job_id,
                "status": "completed",
                "completed": completed,
                "failed": failed,
                "total_cost_usd": total_cost,
            }),
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
        # Extract repo data
        logger.info("extracting_repo_data", sub_id=submission.sub_id, repo=submission.repo_url)

        # Parse GitHub URL
        owner, repo_name = parse_github_url(submission.repo_url)

        # Fetch GitHub Actions data
        actions_analyzer = ActionsAnalyzer()
        actions_data = actions_analyzer.analyze(owner, repo_name)
        actions_analyzer.close()

        # Clone and extract repository
        repo_data = clone_and_extract(
            repo_url=submission.repo_url,
            submission_id=submission.sub_id,
            workflow_runs=actions_data["workflow_runs"],
            workflow_definitions=actions_data["workflow_definitions"],
        )

        logger.info("repo_data_extracted", sub_id=submission.sub_id)

        # Build context for agents
        rubric_json = hackathon.rubric.model_dump_json(indent=2)

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

        # Run analysis (async)
        result = asyncio.run(
            orchestrator.analyze_submission(
                repo_data=repo_data,
                hackathon_name=hackathon.name,
                team_name=submission.team_name,
                hack_id=hackathon.hack_id,
                sub_id=submission.sub_id,
                rubric=hackathon.rubric,
                agents_enabled=agents_enabled,
                ai_policy_mode=hackathon.ai_policy_mode.value if hasattr(hackathon.ai_policy_mode, 'value') else str(hackathon.ai_policy_mode),
            )
        )

        logger.info("orchestrator_complete", sub_id=submission.sub_id, score=result["overall_score"])

        # Build agent_scores dict for storage
        agent_scores = {}
        for agent_name, response in result["agent_responses"].items():
            agent_key = agent_name.value if hasattr(agent_name, 'value') else str(agent_name)
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
