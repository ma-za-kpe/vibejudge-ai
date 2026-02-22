"""Analysis service — Orchestrate repo analysis and scoring."""

import json
import os
from datetime import UTC, datetime

import boto3

from src.models.analysis import AnalysisJobResponse
from src.models.common import JobStatus, SubmissionStatus
from src.utils.dynamo import DynamoDBHelper
from src.utils.id_gen import generate_job_id
from src.utils.logging import get_logger

logger = get_logger(__name__)


class AnalysisService:
    """Service for analysis orchestration."""

    def __init__(self, db: DynamoDBHelper):
        """Initialize analysis service.
        
        Args:
            db: DynamoDB helper instance
        """
        self.db = db
        self._lambda_client = None

    @property
    def lambda_client(self):
        """Lazy-load Lambda client."""
        if self._lambda_client is None:
            region = os.environ.get("AWS_REGION", "us-east-1")
            self._lambda_client = boto3.client("lambda", region_name=region)
        return self._lambda_client

    def trigger_analysis(
        self,
        hack_id: str,
        submission_ids: list[str] | None = None,
    ) -> AnalysisJobResponse:
        """Trigger analysis for submissions.
        
        Args:
            hack_id: Hackathon ID
            submission_ids: Optional list of submission IDs (None = all pending)
            
        Returns:
            Analysis job response
        """
        job_id = generate_job_id()
        now = datetime.now(UTC)

        # Get submissions to analyze
        if submission_ids is None:
            # Get all pending submissions
            all_subs = self.db.list_submissions(hack_id)
            submission_ids = [
                s["sub_id"]
                for s in all_subs
                if s.get("status") == SubmissionStatus.PENDING.value
            ]

        # Create analysis job record
        job_record = {
            "PK": f"HACK#{hack_id}",
            "SK": f"JOB#{job_id}",
            "entity_type": "ANALYSIS_JOB",
            "job_id": job_id,
            "hack_id": hack_id,
            "status": JobStatus.QUEUED.value,
            "submission_ids": submission_ids,
            "total_submissions": len(submission_ids),
            "completed_submissions": 0,
            "failed_submissions": 0,
            "total_cost_usd": 0.0,
            "started_at": None,
            "completed_at": None,
            "error_message": None,
            "GSI2PK": f"JOB_STATUS#{JobStatus.QUEUED.value}",
            "GSI2SK": now.isoformat(),
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }

        success = self.db.put_analysis_job(job_record)
        if not success:
            logger.error("analysis_job_creation_failed", job_id=job_id)
            raise RuntimeError("Failed to create analysis job")

        logger.info(
            "analysis_job_created",
            job_id=job_id,
            hack_id=hack_id,
            submission_count=len(submission_ids),
        )

        # Invoke Analyzer Lambda asynchronously
        lambda_function_name = os.environ.get("ANALYZER_LAMBDA_FUNCTION_NAME")

        if lambda_function_name:
            try:
                payload = {
                    "job_id": job_id,
                    "hack_id": hack_id,
                    "submission_ids": submission_ids,
                }

                response = self.lambda_client.invoke(
                    FunctionName=lambda_function_name,
                    InvocationType="Event",  # Async invocation
                    Payload=json.dumps(payload),
                )

                logger.info(
                    "analyzer_lambda_invoked",
                    job_id=job_id,
                    status_code=response["StatusCode"],
                )
            except Exception as e:
                logger.error(
                    "analyzer_lambda_invocation_failed",
                    job_id=job_id,
                    error=str(e),
                )
                # Don't fail the request - job is created, can be retried
        else:
            logger.warning(
                "analyzer_lambda_not_configured",
                job_id=job_id,
                message="Set ANALYZER_LAMBDA_FUNCTION_NAME env var to enable Lambda invocation",
            )

        return AnalysisJobResponse(
            job_id=job_id,
            hack_id=hack_id,
            status=JobStatus.QUEUED,
            total_submissions=len(submission_ids),
            completed_submissions=0,
            failed_submissions=0,
            total_cost_usd=0.0,
            started_at=None,
            completed_at=None,
            error_message=None,
            created_at=now,
            updated_at=now,
        )

    def get_analysis_status(self, hack_id: str, job_id: str) -> AnalysisJobResponse | None:
        """Get analysis job status.
        
        Args:
            hack_id: Hackathon ID
            job_id: Job ID
            
        Returns:
            Analysis job response or None if not found
        """
        # Query for job record
        jobs = self.db.list_analysis_jobs(hack_id)
        job_record = next(
            (j for j in jobs if j.get("job_id") == job_id),
            None,
        )

        if not job_record:
            return None

        return AnalysisJobResponse(
            job_id=job_record["job_id"],
            hack_id=job_record["hack_id"],
            status=JobStatus(job_record["status"]),
            total_submissions=job_record["total_submissions"],
            completed_submissions=job_record.get("completed_submissions", 0),
            failed_submissions=job_record.get("failed_submissions", 0),
            total_cost_usd=job_record.get("total_cost_usd", 0.0),
            started_at=datetime.fromisoformat(job_record["started_at"]) if job_record.get("started_at") else None,
            completed_at=datetime.fromisoformat(job_record["completed_at"]) if job_record.get("completed_at") else None,
            error_message=job_record.get("error_message"),
            created_at=datetime.fromisoformat(job_record["created_at"]),
            updated_at=datetime.fromisoformat(job_record["updated_at"]),
        )

    def list_analysis_jobs(self, hack_id: str) -> list[AnalysisJobResponse]:
        """List analysis jobs for hackathon.
        
        Args:
            hack_id: Hackathon ID
            
        Returns:
            List of analysis job responses
        """
        records = self.db.list_analysis_jobs(hack_id)

        return [
            AnalysisJobResponse(
                job_id=r["job_id"],
                hack_id=r["hack_id"],
                status=JobStatus(r["status"]),
                total_submissions=r["total_submissions"],
                completed_submissions=r.get("completed_submissions", 0),
                failed_submissions=r.get("failed_submissions", 0),
                total_cost_usd=r.get("total_cost_usd", 0.0),
                started_at=datetime.fromisoformat(r["started_at"]) if r.get("started_at") else None,
                completed_at=datetime.fromisoformat(r["completed_at"]) if r.get("completed_at") else None,
                error_message=r.get("error_message"),
                created_at=datetime.fromisoformat(r["created_at"]),
                updated_at=datetime.fromisoformat(r["updated_at"]),
            )
            for r in records
        ]

    def update_job_status(
        self,
        hack_id: str,
        job_id: str,
        status: JobStatus,
        **kwargs,
    ) -> bool:
        """Update analysis job status.
        
        Args:
            hack_id: Hackathon ID
            job_id: Job ID
            status: New status
            **kwargs: Additional fields to update
            
        Returns:
            True if successful
        """
        jobs = self.db.list_analysis_jobs(hack_id)
        job_record = next(
            (j for j in jobs if j.get("job_id") == job_id),
            None,
        )

        if not job_record:
            return False

        job_record["status"] = status.value
        job_record["updated_at"] = datetime.now(UTC).isoformat()
        job_record["GSI2PK"] = f"JOB_STATUS#{status.value}"

        for key, value in kwargs.items():
            if value is not None:
                if isinstance(value, datetime):
                    job_record[key] = value.isoformat()
                else:
                    job_record[key] = value

        return self.db.put_analysis_job(job_record)
