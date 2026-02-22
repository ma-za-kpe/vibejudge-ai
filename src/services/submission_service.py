"""Submission service — Submission management."""

from datetime import datetime, timezone
from decimal import Decimal

from src.models.common import SubmissionStatus
from src.models.submission import (
    SubmissionInput,
    SubmissionBatchCreate,
    SubmissionResponse,
    SubmissionListItem,
    SubmissionListResponse,
    SubmissionBatchCreateResponse,
    RepoMeta,
    WeightedDimensionScore,
)
from src.utils.dynamo import DynamoDBHelper
from src.utils.id_gen import generate_sub_id
from src.utils.logging import get_logger

logger = get_logger(__name__)


class SubmissionService:
    """Service for submission operations."""
    
    def __init__(self, db: DynamoDBHelper):
        """Initialize submission service.
        
        Args:
            db: DynamoDB helper instance
        """
        self.db = db
    
    def create_submissions(
        self,
        hack_id: str,
        data: SubmissionBatchCreate,
    ) -> SubmissionBatchCreateResponse:
        """Create multiple submissions.
        
        Args:
            hack_id: Hackathon ID
            data: Batch submission data
            
        Returns:
            Batch creation response
        """
        now = datetime.now(timezone.utc)
        created_items = []
        
        for sub_input in data.submissions:
            sub_id = generate_sub_id()
            
            # Create submission record
            record = {
                "PK": f"HACK#{hack_id}",
                "SK": f"SUB#{sub_id}",
                "entity_type": "SUBMISSION",
                "sub_id": sub_id,
                "hack_id": hack_id,
                "team_name": sub_input.team_name,
                "repo_url": sub_input.repo_url,
                "status": SubmissionStatus.PENDING.value,
                "overall_score": None,
                "rank": None,
                "recommendation": None,
                "repo_meta": None,
                "weighted_scores": None,
                "strengths": [],
                "weaknesses": [],
                "agent_scores": {},
                "total_cost_usd": None,
                "total_tokens": None,
                "analysis_duration_ms": None,
                "analyzed_at": None,
                "GSI1PK": f"SUB#{sub_id}",
                "GSI1SK": f"HACK#{hack_id}",
                "created_at": now.isoformat(),
                "updated_at": now.isoformat(),
            }
            
            success = self.db.put_submission(record)
            if success:
                created_items.append(
                    SubmissionListItem(
                        sub_id=sub_id,
                        team_name=sub_input.team_name,
                        repo_url=sub_input.repo_url,
                        status=SubmissionStatus.PENDING,
                        overall_score=None,
                        rank=None,
                        total_cost_usd=None,
                        created_at=now,
                    )
                )
                logger.info(
                    "submission_created",
                    sub_id=sub_id,
                    hack_id=hack_id,
                    team=sub_input.team_name,
                )
        
        # Get updated hackathon submission count
        hackathon = self.db.get_hackathon(hack_id)
        submission_count = hackathon.get("submission_count", 0) if hackathon else 0
        
        return SubmissionBatchCreateResponse(
            created=len(created_items),
            submissions=created_items,
            hackathon_submission_count=submission_count + len(created_items),
        )
    
    def get_submission(self, sub_id: str) -> SubmissionResponse | None:
        """Get submission by ID.
        
        Args:
            sub_id: Submission ID
            
        Returns:
            Submission response or None if not found
        """
        record = self.db.get_submission_by_id(sub_id)
        if not record:
            return None
        
        # Parse repo_meta if present
        repo_meta = None
        if record.get("repo_meta"):
            repo_meta = RepoMeta(**record["repo_meta"])
        
        # Parse weighted_scores if present
        weighted_scores = None
        if record.get("weighted_scores"):
            weighted_scores = {
                k: WeightedDimensionScore(**v)
                for k, v in record["weighted_scores"].items()
            }
        
        return SubmissionResponse(
            sub_id=record["sub_id"],
            hack_id=record["hack_id"],
            team_name=record["team_name"],
            repo_url=record["repo_url"],
            status=SubmissionStatus(record["status"]),
            overall_score=record.get("overall_score"),
            rank=record.get("rank"),
            recommendation=record.get("recommendation"),
            repo_meta=repo_meta,
            weighted_scores=weighted_scores,
            strengths=record.get("strengths", []),
            weaknesses=record.get("weaknesses", []),
            agent_scores=record.get("agent_scores", {}),
            total_cost_usd=record.get("total_cost_usd"),
            total_tokens=record.get("total_tokens"),
            analysis_duration_ms=record.get("analysis_duration_ms"),
            analyzed_at=datetime.fromisoformat(record["analyzed_at"]) if record.get("analyzed_at") else None,
            created_at=datetime.fromisoformat(record["created_at"]),
            updated_at=datetime.fromisoformat(record["updated_at"]),
        )
    
    def list_submissions(self, hack_id: str) -> SubmissionListResponse:
        """List submissions for hackathon.
        
        Args:
            hack_id: Hackathon ID
            
        Returns:
            List of submissions
        """
        records = self.db.list_submissions(hack_id)
        
        items = [
            SubmissionListItem(
                sub_id=r["sub_id"],
                team_name=r["team_name"],
                repo_url=r["repo_url"],
                status=SubmissionStatus(r["status"]),
                overall_score=r.get("overall_score"),
                rank=r.get("rank"),
                total_cost_usd=r.get("total_cost_usd"),
                created_at=datetime.fromisoformat(r["created_at"]),
            )
            for r in records
        ]
        
        return SubmissionListResponse(
            submissions=items,
            next_cursor=None,
            has_more=False,
        )
    
    def update_submission_status(
        self,
        hack_id: str,
        sub_id: str,
        status: SubmissionStatus,
        **kwargs,
    ) -> bool:
        """Update submission status and optional fields.
        
        Args:
            hack_id: Hackathon ID
            sub_id: Submission ID
            status: New status
            **kwargs: Additional fields to update
            
        Returns:
            True if successful
        """
        now = datetime.now(timezone.utc)
        return self.db.update_submission_status(
            hack_id=hack_id,
            sub_id=sub_id,
            status=status.value,
            updated_at=now.isoformat(),
            **kwargs,
        )
    
    def update_submission_results(
        self,
        hack_id: str,
        sub_id: str,
        overall_score: float,
        weighted_scores: dict,
        agent_scores: dict,
        strengths: list[str],
        weaknesses: list[str],
        recommendation: str,
        repo_meta: dict,
        total_cost_usd: float,
        total_tokens: int,
        analysis_duration_ms: int,
    ) -> bool:
        """Update submission with analysis results.
        
        Args:
            hack_id: Hackathon ID
            sub_id: Submission ID
            overall_score: Overall weighted score
            weighted_scores: Dimension scores
            agent_scores: Agent raw scores
            strengths: List of strengths
            weaknesses: List of weaknesses
            recommendation: Recommendation category
            repo_meta: Repository metadata
            total_cost_usd: Total analysis cost
            total_tokens: Total tokens used
            analysis_duration_ms: Analysis duration
            
        Returns:
            True if successful
        """
        now = datetime.now(timezone.utc)
        
        return self.update_submission_status(
            hack_id=hack_id,
            sub_id=sub_id,
            status=SubmissionStatus.COMPLETED,
            overall_score=overall_score,
            weighted_scores=weighted_scores,
            agent_scores=agent_scores,
            strengths=strengths,
            weaknesses=weaknesses,
            recommendation=recommendation,
            repo_meta=repo_meta,
            total_cost_usd=total_cost_usd,
            total_tokens=total_tokens,
            analysis_duration_ms=analysis_duration_ms,
            analyzed_at=now.isoformat(),
        )
    
    def update_submission_with_scores(
        self,
        hack_id: str,
        sub_id: str,
        overall_score: float,
        dimension_scores: dict,
        weighted_scores: dict,
        recommendation: str,
        confidence: float,
        agent_scores: dict,
        strengths: list[str],
        weaknesses: list[str],
        repo_meta: dict,
        total_cost_usd: float,
        total_tokens: int,
        analysis_duration_ms: int,
    ) -> bool:
        """Update submission with analysis scores (alias for update_submission_results).
        
        This method is called by the analyzer Lambda and includes additional
        parameters like dimension_scores and confidence that are logged but
        not stored in the main submission record.
        
        Args:
            hack_id: Hackathon ID
            sub_id: Submission ID
            overall_score: Overall weighted score
            dimension_scores: Individual dimension scores (not stored)
            weighted_scores: Weighted dimension scores
            recommendation: Recommendation category
            confidence: Overall confidence score (not stored)
            agent_scores: Agent raw scores
            strengths: List of strengths
            weaknesses: List of weaknesses
            repo_meta: Repository metadata
            total_cost_usd: Total analysis cost
            total_tokens: Total tokens used
            analysis_duration_ms: Analysis duration
            
        Returns:
            True if successful
        """
        logger.info(
            "submission_scores_update",
            sub_id=sub_id,
            overall_score=overall_score,
            confidence=confidence,
            cost_usd=total_cost_usd,
        )
        
        # Convert floats to Decimals and datetimes to ISO strings for DynamoDB
        def convert_to_decimal(obj):
            """Recursively convert floats to Decimals and datetimes to ISO strings for DynamoDB."""
            from datetime import datetime
            
            if isinstance(obj, float):
                return Decimal(str(obj))
            elif isinstance(obj, datetime):
                return obj.isoformat()
            elif isinstance(obj, dict):
                return {k: convert_to_decimal(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_to_decimal(item) for item in obj]
            elif hasattr(obj, 'model_dump'):
                # Handle Pydantic models - use mode='json' to serialize datetimes
                return convert_to_decimal(obj.model_dump(mode='json'))
            return obj
        
        # Call the main update method (dimension_scores and confidence not stored)
        return self.update_submission_results(
            hack_id=hack_id,
            sub_id=sub_id,
            overall_score=Decimal(str(overall_score)),
            weighted_scores=convert_to_decimal(weighted_scores),
            agent_scores=convert_to_decimal(agent_scores),
            strengths=strengths,
            weaknesses=weaknesses,
            recommendation=recommendation,
            repo_meta=convert_to_decimal(repo_meta),
            total_cost_usd=Decimal(str(total_cost_usd)),
            total_tokens=total_tokens,
            analysis_duration_ms=analysis_duration_ms,
        )
    
    def delete_submission(self, hack_id: str, sub_id: str) -> bool:
        """Delete submission (soft delete by status).
        
        Args:
            hack_id: Hackathon ID
            sub_id: Submission ID
            
        Returns:
            True if successful
        """
        return self.update_submission_status(
            hack_id=hack_id,
            sub_id=sub_id,
            status=SubmissionStatus.DELETED,
        )
