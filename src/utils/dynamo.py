"""DynamoDB helper with all 16 access patterns."""

from typing import Any, Optional

import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

from src.utils.logging import get_logger

logger = get_logger(__name__)


class DynamoDBHelper:
    """Helper class for DynamoDB operations with all access patterns."""
    
    def __init__(self, table_name: str):
        """Initialize DynamoDB helper.
        
        Args:
            table_name: Name of the DynamoDB table
        """
        import os
        endpoint_url = os.environ.get("DYNAMODB_ENDPOINT_URL")
        region = os.environ.get("AWS_REGION", "us-east-1")
        
        if endpoint_url:
            # Local DynamoDB
            dynamodb = boto3.resource("dynamodb", endpoint_url=endpoint_url, region_name=region)
        else:
            # AWS DynamoDB
            dynamodb = boto3.resource("dynamodb", region_name=region)
        
        self.table = dynamodb.Table(table_name)
        self.table_name = table_name
    
    # ============================================================
    # ORGANIZER ACCESS PATTERNS
    # ============================================================
    
    def get_organizer(self, org_id: str) -> Optional[dict]:
        """AP1: Get organizer by ID.
        
        Args:
            org_id: Organizer ID
            
        Returns:
            Organizer record or None
        """
        try:
            response = self.table.get_item(
                Key={"PK": f"ORG#{org_id}", "SK": "PROFILE"}
            )
            return response.get("Item")
        except ClientError as e:
            logger.error("get_organizer_failed", org_id=org_id, error=str(e))
            return None
    
    def get_organizer_by_email(self, email: str) -> Optional[dict]:
        """AP2: Get organizer by email.
        
        Args:
            email: Organizer email
            
        Returns:
            Organizer record or None
        """
        try:
            response = self.table.query(
                IndexName="GSI1",
                KeyConditionExpression=Key("GSI1PK").eq(f"EMAIL#{email}")
            )
            items = response.get("Items", [])
            return items[0] if items else None
        except ClientError as e:
            logger.error("get_organizer_by_email_failed", email=email, error=str(e))
            return None
    
    def put_organizer(self, organizer: dict) -> bool:
        """Create or update organizer record.
        
        Args:
            organizer: Organizer record dict
            
        Returns:
            True if successful
        """
        try:
            # Convert datetime objects to ISO strings for DynamoDB
            item = self._serialize_item(organizer)
            self.table.put_item(Item=item)
            logger.info("organizer_created", org_id=organizer.get("org_id"))
            return True
        except ClientError as e:
            logger.error("put_organizer_failed", error=str(e))
            return False
    
    def _serialize_item(self, item: dict) -> dict:
        """Convert datetime objects to ISO strings and floats to Decimal for DynamoDB.
        
        Args:
            item: Dictionary that may contain datetime objects or floats
            
        Returns:
            Dictionary with datetime objects converted to ISO strings and floats to Decimal
        """
        from datetime import datetime
        from decimal import Decimal
        
        serialized = {}
        for key, value in item.items():
            if isinstance(value, datetime):
                serialized[key] = value.isoformat()
            elif isinstance(value, float):
                serialized[key] = Decimal(str(value))
            elif isinstance(value, dict):
                serialized[key] = self._serialize_item(value)
            elif isinstance(value, list):
                serialized[key] = [
                    self._serialize_item(v) if isinstance(v, dict) else
                    v.isoformat() if isinstance(v, datetime) else
                    Decimal(str(v)) if isinstance(v, float) else v
                    for v in value
                ]
            else:
                serialized[key] = value
        return serialized
    
    # ============================================================
    # HACKATHON ACCESS PATTERNS
    # ============================================================
    
    def list_organizer_hackathons(self, org_id: str) -> list[dict]:
        """AP3: List hackathons for organizer.
        
        Args:
            org_id: Organizer ID
            
        Returns:
            List of hackathon records
        """
        try:
            response = self.table.query(
                KeyConditionExpression=(
                    Key("PK").eq(f"ORG#{org_id}") &
                    Key("SK").begins_with("HACK#")
                )
            )
            return response.get("Items", [])
        except ClientError as e:
            logger.error("list_organizer_hackathons_failed", org_id=org_id, error=str(e))
            return []
    
    def get_hackathon(self, hack_id: str) -> Optional[dict]:
        """AP4: Get hackathon config.
        
        Args:
            hack_id: Hackathon ID
            
        Returns:
            Hackathon detail record or None
        """
        try:
            response = self.table.get_item(
                Key={"PK": f"HACK#{hack_id}", "SK": "META"}
            )
            return response.get("Item")
        except ClientError as e:
            logger.error("get_hackathon_failed", hack_id=hack_id, error=str(e))
            return None
    
    def get_hackathon_by_id(self, hack_id: str) -> Optional[dict]:
        """AP5: Get hackathon by ID (from any context).
        
        Args:
            hack_id: Hackathon ID
            
        Returns:
            Hackathon record or None
        """
        try:
            response = self.table.query(
                IndexName="GSI1",
                KeyConditionExpression=(
                    Key("GSI1PK").eq(f"HACK#{hack_id}") &
                    Key("GSI1SK").eq("META")
                )
            )
            items = response.get("Items", [])
            return items[0] if items else None
        except ClientError as e:
            logger.error("get_hackathon_by_id_failed", hack_id=hack_id, error=str(e))
            return None
    
    def put_hackathon(self, hackathon: dict) -> bool:
        """Create or update hackathon record.
        
        Args:
            hackathon: Hackathon record dict
            
        Returns:
            True if successful
        """
        try:
            item = self._serialize_item(hackathon)
            self.table.put_item(Item=item)
            logger.info("hackathon_created", hack_id=hackathon.get("hack_id"))
            return True
        except ClientError as e:
            logger.error("put_hackathon_failed", error=str(e))
            return False
    
    def put_hackathon_detail(self, detail: dict) -> bool:
        """Create or update hackathon detail record.
        
        Args:
            detail: Hackathon detail record dict
            
        Returns:
            True if successful
        """
        try:
            item = self._serialize_item(detail)
            self.table.put_item(Item=item)
            logger.info("hackathon_detail_created", hack_id=detail.get("hack_id"))
            return True
        except ClientError as e:
            logger.error("put_hackathon_detail_failed", error=str(e))
            return False
    
    # ============================================================
    # SUBMISSION ACCESS PATTERNS
    # ============================================================
    
    def list_submissions(self, hack_id: str) -> list[dict]:
        """AP6: List all submissions for hackathon.
        
        Args:
            hack_id: Hackathon ID
            
        Returns:
            List of submission records
        """
        try:
            response = self.table.query(
                KeyConditionExpression=(
                    Key("PK").eq(f"HACK#{hack_id}") &
                    Key("SK").begins_with("SUB#")
                )
            )
            return response.get("Items", [])
        except ClientError as e:
            logger.error("list_submissions_failed", hack_id=hack_id, error=str(e))
            return []
    
    def get_submission(self, hack_id: str, sub_id: str) -> Optional[dict]:
        """AP7: Get single submission.
        
        Args:
            hack_id: Hackathon ID
            sub_id: Submission ID
            
        Returns:
            Submission record or None
        """
        try:
            response = self.table.get_item(
                Key={"PK": f"HACK#{hack_id}", "SK": f"SUB#{sub_id}"}
            )
            return response.get("Item")
        except ClientError as e:
            logger.error("get_submission_failed", sub_id=sub_id, error=str(e))
            return None
    
    def get_submission_by_id(self, sub_id: str) -> Optional[dict]:
        """AP8: Get submission by ID (from any context).
        
        Args:
            sub_id: Submission ID
            
        Returns:
            Submission record or None
        """
        try:
            response = self.table.query(
                IndexName="GSI1",
                KeyConditionExpression=Key("GSI1PK").eq(f"SUB#{sub_id}")
            )
            items = response.get("Items", [])
            return items[0] if items else None
        except ClientError as e:
            logger.error("get_submission_by_id_failed", sub_id=sub_id, error=str(e))
            return None
    
    def put_submission(self, submission: dict) -> bool:
        """Create or update submission record.
        
        Args:
            submission: Submission record dict
            
        Returns:
            True if successful
        """
        try:
            item = self._serialize_item(submission)
            self.table.put_item(Item=item)
            logger.info("submission_created", sub_id=submission.get("sub_id"))
            return True
        except ClientError as e:
            logger.error("put_submission_failed", error=str(e))
            return False
    
    def update_submission_status(
        self, hack_id: str, sub_id: str, status: str, **kwargs
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
        try:
            from datetime import datetime
            
            update_expr = "SET #status = :status, updated_at = :updated_at"
            expr_attr_names = {"#status": "status"}
            expr_attr_values = {
                ":status": status,
                ":updated_at": kwargs.get("updated_at").isoformat() if isinstance(kwargs.get("updated_at"), datetime) else kwargs.get("updated_at"),
            }
            
            # Add optional fields
            for key, value in kwargs.items():
                if key != "updated_at" and value is not None:
                    # Serialize datetime values
                    if isinstance(value, datetime):
                        value = value.isoformat()
                    update_expr += f", {key} = :{key}"
                    expr_attr_values[f":{key}"] = value
            
            self.table.update_item(
                Key={"PK": f"HACK#{hack_id}", "SK": f"SUB#{sub_id}"},
                UpdateExpression=update_expr,
                ExpressionAttributeNames=expr_attr_names,
                ExpressionAttributeValues=expr_attr_values,
            )
            logger.info("submission_status_updated", sub_id=sub_id, status=status)
            return True
        except ClientError as e:
            logger.error("update_submission_status_failed", sub_id=sub_id, error=str(e))
            return False
    
    # ============================================================
    # SCORE ACCESS PATTERNS
    # ============================================================
    
    def get_agent_scores(self, sub_id: str) -> list[dict]:
        """AP9: Get all agent scores for submission.
        
        Args:
            sub_id: Submission ID
            
        Returns:
            List of agent score records
        """
        try:
            response = self.table.query(
                KeyConditionExpression=(
                    Key("PK").eq(f"SUB#{sub_id}") &
                    Key("SK").begins_with("SCORE#")
                )
            )
            return response.get("Items", [])
        except ClientError as e:
            logger.error("get_agent_scores_failed", sub_id=sub_id, error=str(e))
            return []
    
    def get_agent_score(self, sub_id: str, agent_name: str) -> Optional[dict]:
        """AP10: Get specific agent score.
        
        Args:
            sub_id: Submission ID
            agent_name: Agent name
            
        Returns:
            Agent score record or None
        """
        try:
            response = self.table.get_item(
                Key={"PK": f"SUB#{sub_id}", "SK": f"SCORE#{agent_name}"}
            )
            return response.get("Item")
        except ClientError as e:
            logger.error("get_agent_score_failed", sub_id=sub_id, agent=agent_name, error=str(e))
            return None
    
    def put_agent_score(self, score: dict) -> bool:
        """Create or update agent score record.
        
        Args:
            score: Agent score record dict
            
        Returns:
            True if successful
        """
        try:
            item = self._serialize_item(score)
            self.table.put_item(Item=item)
            logger.info("agent_score_saved", sub_id=score.get("sub_id"), agent=score.get("agent_name"))
            return True
        except ClientError as e:
            logger.error("put_agent_score_failed", error=str(e))
            return False
    
    def get_submission_summary(self, sub_id: str) -> Optional[dict]:
        """AP11: Get submission summary.
        
        Args:
            sub_id: Submission ID
            
        Returns:
            Submission summary record or None
        """
        try:
            response = self.table.get_item(
                Key={"PK": f"SUB#{sub_id}", "SK": "SUMMARY"}
            )
            return response.get("Item")
        except ClientError as e:
            logger.error("get_submission_summary_failed", sub_id=sub_id, error=str(e))
            return None
    
    def put_submission_summary(self, summary: dict) -> bool:
        """Create or update submission summary.
        
        Args:
            summary: Submission summary record dict
            
        Returns:
            True if successful
        """
        try:
            item = self._serialize_item(summary)
            self.table.put_item(Item=item)
            logger.info("submission_summary_saved", sub_id=summary.get("sub_id"))
            return True
        except ClientError as e:
            logger.error("put_submission_summary_failed", error=str(e))
            return False
    
    # ============================================================
    # COST ACCESS PATTERNS
    # ============================================================
    
    def get_submission_costs(self, sub_id: str) -> list[dict]:
        """AP12: Get all cost records for submission.
        
        Args:
            sub_id: Submission ID
            
        Returns:
            List of cost records
        """
        try:
            response = self.table.query(
                KeyConditionExpression=(
                    Key("PK").eq(f"SUB#{sub_id}") &
                    Key("SK").begins_with("COST#")
                )
            )
            return response.get("Items", [])
        except ClientError as e:
            logger.error("get_submission_costs_failed", sub_id=sub_id, error=str(e))
            return []
    
    def put_cost_record(self, cost: dict) -> bool:
        """Create or update cost record.
        
        Args:
            cost: Cost record dict
            
        Returns:
            True if successful
        """
        try:
            item = self._serialize_item(cost)
            self.table.put_item(Item=item)
            logger.info("cost_record_saved", sub_id=cost.get("sub_id"), agent=cost.get("agent_name"))
            return True
        except ClientError as e:
            logger.error("put_cost_record_failed", error=str(e))
            return False
    
    def get_hackathon_cost_summary(self, hack_id: str) -> Optional[dict]:
        """AP13: Get hackathon cost summary.
        
        Args:
            hack_id: Hackathon ID
            
        Returns:
            Hackathon cost summary or None
        """
        try:
            response = self.table.get_item(
                Key={"PK": f"HACK#{hack_id}", "SK": "COST#SUMMARY"}
            )
            return response.get("Item")
        except ClientError as e:
            logger.error("get_hackathon_cost_summary_failed", hack_id=hack_id, error=str(e))
            return None
    
    def put_hackathon_cost_summary(self, cost_summary: dict) -> bool:
        """Create or update hackathon cost summary.
        
        Args:
            cost_summary: Hackathon cost summary dict
            
        Returns:
            True if successful
        """
        try:
            item = self._serialize_item(cost_summary)
            self.table.put_item(Item=item)
            logger.info("hackathon_cost_summary_saved", hack_id=cost_summary.get("hack_id"))
            return True
        except ClientError as e:
            logger.error("put_hackathon_cost_summary_failed", error=str(e))
            return False
    
    # ============================================================
    # ANALYSIS JOB ACCESS PATTERNS
    # ============================================================
    
    def list_analysis_jobs(self, hack_id: str) -> list[dict]:
        """AP14: List analysis jobs for hackathon.
        
        Args:
            hack_id: Hackathon ID
            
        Returns:
            List of analysis job records
        """
        try:
            response = self.table.query(
                KeyConditionExpression=(
                    Key("PK").eq(f"HACK#{hack_id}") &
                    Key("SK").begins_with("JOB#")
                )
            )
            return response.get("Items", [])
        except ClientError as e:
            logger.error("list_analysis_jobs_failed", hack_id=hack_id, error=str(e))
            return []
    
    def list_jobs_by_status(self, status: str) -> list[dict]:
        """AP15: List jobs by status.
        
        Args:
            status: Job status
            
        Returns:
            List of job records
        """
        try:
            response = self.table.query(
                IndexName="GSI2",
                KeyConditionExpression=Key("GSI2PK").eq(f"JOB_STATUS#{status}")
            )
            return response.get("Items", [])
        except ClientError as e:
            logger.error("list_jobs_by_status_failed", status=status, error=str(e))
            return []
    
    def put_analysis_job(self, job: dict) -> bool:
        """Create or update analysis job.
        
        Args:
            job: Analysis job record dict
            
        Returns:
            True if successful
        """
        try:
            item = self._serialize_item(job)
            self.table.put_item(Item=item)
            logger.info("analysis_job_created", job_id=job.get("job_id"))
            return True
        except ClientError as e:
            logger.error("put_analysis_job_failed", error=str(e))
            return False
    
    # ============================================================
    # LEADERBOARD
    # ============================================================
    
    def get_leaderboard(self, hack_id: str) -> list[dict]:
        """AP16: Get submissions sorted by score (application-side sort).
        
        Args:
            hack_id: Hackathon ID
            
        Returns:
            List of submissions sorted by overall_score descending
        """
        submissions = self.list_submissions(hack_id)
        # Filter only completed submissions with scores
        scored = [s for s in submissions if s.get("overall_score") is not None]
        # Sort by score descending
        return sorted(scored, key=lambda x: x.get("overall_score", 0), reverse=True)
    
    # ============================================================
    # BATCH OPERATIONS
    # ============================================================
    
    def batch_write(self, items: list[dict]) -> bool:
        """Batch write multiple items.
        
        Args:
            items: List of items to write
            
        Returns:
            True if successful
        """
        try:
            with self.table.batch_writer() as batch:
                for item in items:
                    serialized = self._serialize_item(item)
                    batch.put_item(Item=serialized)
            logger.info("batch_write_completed", count=len(items))
            return True
        except ClientError as e:
            logger.error("batch_write_failed", error=str(e))
            return False
