"""DynamoDB helper with all 16 access patterns."""

from typing import Any

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

    def get_organizer(self, org_id: str) -> dict | None:
        """AP1: Get organizer by ID.

        Args:
            org_id: Organizer ID

        Returns:
            Organizer record or None
        """
        try:
            response = self.table.get_item(Key={"PK": f"ORG#{org_id}", "SK": "PROFILE"})
            return response.get("Item")
        except ClientError as e:
            logger.error("get_organizer_failed", org_id=org_id, error=str(e))
            return None

    def get_organizer_by_email(self, email: str) -> dict | None:
        """AP2: Get organizer by email.

        Args:
            email: Organizer email

        Returns:
            Organizer record or None
        """
        try:
            response = self.table.query(
                IndexName="GSI1", KeyConditionExpression=Key("GSI1PK").eq(f"EMAIL#{email}")
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
        from typing import Any

        serialized: dict[str, Any] = {}
        for key, value in item.items():
            if isinstance(value, datetime):
                serialized[key] = value.isoformat()
            elif isinstance(value, float):
                serialized[key] = Decimal(str(value))
            elif isinstance(value, dict):
                serialized[key] = self._serialize_item(value)
            elif isinstance(value, list):
                serialized[key] = [
                    self._serialize_item(v)
                    if isinstance(v, dict)
                    else v.isoformat()
                    if isinstance(v, datetime)
                    else Decimal(str(v))
                    if isinstance(v, float)
                    else v
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
                    Key("PK").eq(f"ORG#{org_id}") & Key("SK").begins_with("HACK#")
                )
            )
            return response.get("Items", [])
        except ClientError as e:
            logger.error("list_organizer_hackathons_failed", org_id=org_id, error=str(e))
            return []

    def get_hackathon(self, hack_id: str) -> dict | None:
        """AP4: Get hackathon config.

        Args:
            hack_id: Hackathon ID

        Returns:
            Hackathon detail record or None
        """
        try:
            response = self.table.get_item(Key={"PK": f"HACK#{hack_id}", "SK": "META"})
            return response.get("Item")
        except ClientError as e:
            logger.error("get_hackathon_failed", hack_id=hack_id, error=str(e))
            return None

    def get_hackathon_by_id(self, hack_id: str) -> dict | None:
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
                    Key("GSI1PK").eq(f"HACK#{hack_id}") & Key("GSI1SK").eq("META")
                ),
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
                    Key("PK").eq(f"HACK#{hack_id}") & Key("SK").begins_with("SUB#")
                )
            )
            return response.get("Items", [])
        except ClientError as e:
            logger.error("list_submissions_failed", hack_id=hack_id, error=str(e))
            return []

    def get_submission(self, hack_id: str, sub_id: str) -> dict | None:
        """AP7: Get single submission.

        Args:
            hack_id: Hackathon ID
            sub_id: Submission ID

        Returns:
            Submission record or None
        """
        try:
            response = self.table.get_item(Key={"PK": f"HACK#{hack_id}", "SK": f"SUB#{sub_id}"})
            return response.get("Item")
        except ClientError as e:
            logger.error("get_submission_failed", sub_id=sub_id, error=str(e))
            return None

    def get_submission_by_id(self, sub_id: str) -> dict | None:
        """AP8: Get submission by ID (from any context).

        Args:
            sub_id: Submission ID

        Returns:
            Submission record or None
        """
        try:
            response = self.table.query(
                IndexName="GSI1", KeyConditionExpression=Key("GSI1PK").eq(f"SUB#{sub_id}")
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
        self, hack_id: str, sub_id: str, status: str, **kwargs: Any
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
            updated_at_value = kwargs.get("updated_at")
            expr_attr_values = {
                ":status": status,
                ":updated_at": updated_at_value.isoformat()
                if isinstance(updated_at_value, datetime)
                else updated_at_value,
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
                    Key("PK").eq(f"SUB#{sub_id}") & Key("SK").begins_with("SCORE#")
                )
            )
            return response.get("Items", [])
        except ClientError as e:
            logger.error("get_agent_scores_failed", sub_id=sub_id, error=str(e))
            return []

    def get_agent_score(self, sub_id: str, agent_name: str) -> dict | None:
        """AP10: Get specific agent score.

        Args:
            sub_id: Submission ID
            agent_name: Agent name

        Returns:
            Agent score record or None
        """
        try:
            response = self.table.get_item(Key={"PK": f"SUB#{sub_id}", "SK": f"SCORE#{agent_name}"})
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
            logger.info(
                "agent_score_saved", sub_id=score.get("sub_id"), agent=score.get("agent_name")
            )
            return True
        except ClientError as e:
            logger.error("put_agent_score_failed", error=str(e))
            return False

    def get_submission_summary(self, sub_id: str) -> dict | None:
        """AP11: Get submission summary.

        Args:
            sub_id: Submission ID

        Returns:
            Submission summary record or None
        """
        try:
            response = self.table.get_item(Key={"PK": f"SUB#{sub_id}", "SK": "SUMMARY"})
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
                    Key("PK").eq(f"SUB#{sub_id}") & Key("SK").begins_with("COST#")
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
            logger.info(
                "cost_record_saved", sub_id=cost.get("sub_id"), agent=cost.get("agent_name")
            )
            return True
        except ClientError as e:
            logger.error("put_cost_record_failed", error=str(e))
            return False

    def get_hackathon_cost_summary(self, hack_id: str) -> dict | None:
        """AP13: Get hackathon cost summary.

        Args:
            hack_id: Hackathon ID

        Returns:
            Hackathon cost summary or None
        """
        try:
            response = self.table.get_item(Key={"PK": f"HACK#{hack_id}", "SK": "COST#SUMMARY"})
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
                    Key("PK").eq(f"HACK#{hack_id}") & Key("SK").begins_with("JOB#")
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
                IndexName="GSI2", KeyConditionExpression=Key("GSI2PK").eq(f"JOB_STATUS#{status}")
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

    # ============================================================
    # TEAM ANALYSIS ACCESS PATTERNS
    # ============================================================

    def get_team_analysis(self, sub_id: str) -> dict | None:
        """Get team analysis for submission.

        Args:
            sub_id: Submission ID

        Returns:
            Team analysis record or None
        """
        try:
            response = self.table.get_item(Key={"PK": f"SUB#{sub_id}", "SK": "TEAM_ANALYSIS"})
            return response.get("Item")
        except ClientError as e:
            logger.error("get_team_analysis_failed", sub_id=sub_id, error=str(e))
            return None

    def put_team_analysis(self, team_analysis: dict) -> bool:
        """Create or update team analysis record.

        Args:
            team_analysis: Team analysis record dict with sub_id

        Returns:
            True if successful
        """
        try:
            item = self._serialize_item(team_analysis)
            self.table.put_item(Item=item)
            logger.info("team_analysis_saved", sub_id=team_analysis.get("sub_id"))
            return True
        except ClientError as e:
            logger.error("put_team_analysis_failed", error=str(e))
            return False

    def get_strategy_analysis(self, sub_id: str) -> dict | None:
        """Get strategy analysis for submission.

        Args:
            sub_id: Submission ID

        Returns:
            Strategy analysis record or None
        """
        try:
            response = self.table.get_item(Key={"PK": f"SUB#{sub_id}", "SK": "STRATEGY_ANALYSIS"})
            return response.get("Item")
        except ClientError as e:
            logger.error("get_strategy_analysis_failed", sub_id=sub_id, error=str(e))
            return None

    def put_strategy_analysis(self, strategy_analysis: dict) -> bool:
        """Create or update strategy analysis record.

        Args:
            strategy_analysis: Strategy analysis record dict with sub_id

        Returns:
            True if successful
        """
        try:
            item = self._serialize_item(strategy_analysis)
            self.table.put_item(Item=item)
            logger.info("strategy_analysis_saved", sub_id=strategy_analysis.get("sub_id"))
            return True
        except ClientError as e:
            logger.error("put_strategy_analysis_failed", error=str(e))
            return False

    def get_actionable_feedback(self, sub_id: str) -> dict | None:
        """Get actionable feedback for submission.

        Args:
            sub_id: Submission ID

        Returns:
            Actionable feedback record or None
        """
        try:
            response = self.table.get_item(Key={"PK": f"SUB#{sub_id}", "SK": "ACTIONABLE_FEEDBACK"})
            return response.get("Item")
        except ClientError as e:
            logger.error("get_actionable_feedback_failed", sub_id=sub_id, error=str(e))
            return None

    def put_actionable_feedback(self, actionable_feedback: dict) -> bool:
        """Create or update actionable feedback record.

        Args:
            actionable_feedback: Actionable feedback record dict with sub_id

        Returns:
            True if successful
        """
        try:
            item = self._serialize_item(actionable_feedback)
            self.table.put_item(Item=item)
            logger.info("actionable_feedback_saved", sub_id=actionable_feedback.get("sub_id"))
            return True
        except ClientError as e:
            logger.error("put_actionable_feedback_failed", error=str(e))
            return False

    # ============================================================
    # API KEY ACCESS PATTERNS
    # ============================================================

    def get_api_key_by_secret(self, api_key: str) -> dict | None:
        """Get API key by secret key value.

        Args:
            api_key: Secret API key string

        Returns:
            API key record or None
        """
        try:
            # Scan with pagination to search entire table
            # DynamoDB scan has 1MB limit per page, must paginate to find key
            # Filter by entity_type to only match API_KEY records (not RATE_LIMIT_COUNTER)
            response = self.table.scan(
                FilterExpression="api_key = :key AND entity_type = :type",
                ExpressionAttributeValues={":key": api_key, ":type": "API_KEY"}
            )
            items = response.get("Items", [])

            # Continue paginating until we find the key or exhaust all pages
            while not items and "LastEvaluatedKey" in response:
                response = self.table.scan(
                    FilterExpression="api_key = :key AND entity_type = :type",
                    ExpressionAttributeValues={":key": api_key, ":type": "API_KEY"},
                    ExclusiveStartKey=response["LastEvaluatedKey"]
                )
                items.extend(response.get("Items", []))

            logger.info(
                "get_api_key_by_secret_scan",
                item_count=len(items),
                api_key_prefix=api_key[:15] if api_key else None,
            )

            return items[0] if items else None
        except ClientError as e:
            logger.error("get_api_key_by_secret_failed", error=str(e))
            return None

    def get_api_key(self, api_key_id: str) -> dict | None:
        """Get API key by ID.

        Args:
            api_key_id: API key ID (ULID)

        Returns:
            API key record or None
        """
        try:
            response = self.table.get_item(
                Key={"PK": f"APIKEY#{api_key_id}", "SK": "METADATA"}
            )
            return response.get("Item")
        except ClientError as e:
            logger.error("get_api_key_failed", api_key_id=api_key_id, error=str(e))
            return None

    def put_api_key(self, api_key: dict) -> bool:
        """Create or update API key record.

        Args:
            api_key: API key record dict

        Returns:
            True if successful
        """
        try:
            item = self._serialize_item(api_key)
            self.table.put_item(Item=item)
            logger.info("api_key_created", api_key_id=api_key.get("api_key_id"))
            return True
        except ClientError as e:
            logger.error("put_api_key_failed", error=str(e))
            return False

    def list_api_keys_by_organizer(self, organizer_id: str) -> list[dict]:
        """List all API keys for an organizer.

        Args:
            organizer_id: Organizer ID

        Returns:
            List of API key records
        """
        try:
            response = self.table.query(
                IndexName="GSI1",
                KeyConditionExpression=Key("GSI1PK").eq(f"ORG#{organizer_id}") & Key("GSI1SK").begins_with("APIKEY#"),
            )
            return response.get("Items", [])
        except ClientError as e:
            logger.error("list_api_keys_by_organizer_failed", organizer_id=organizer_id, error=str(e))
            return []

    def update_api_key_usage(
        self,
        api_key_id: str,
        total_requests: int | None = None,
        total_cost_usd: float | None = None,
        last_used_at: str | None = None,
    ) -> bool:
        """Update API key usage statistics.

        Args:
            api_key_id: API key ID
            total_requests: New total request count
            total_cost_usd: New total cost
            last_used_at: Last used timestamp (ISO format)

        Returns:
            True if successful
        """
        try:
            from datetime import datetime

            update_parts = []
            expr_attr_values = {":updated_at": datetime.utcnow().isoformat()}

            if total_requests is not None:
                update_parts.append("total_requests = :total_requests")
                expr_attr_values[":total_requests"] = total_requests

            if total_cost_usd is not None:
                update_parts.append("total_cost_usd = :total_cost_usd")
                expr_attr_values[":total_cost_usd"] = total_cost_usd

            if last_used_at is not None:
                update_parts.append("last_used_at = :last_used_at")
                expr_attr_values[":last_used_at"] = last_used_at

            if not update_parts:
                return True  # Nothing to update

            update_expr = f"SET {', '.join(update_parts)}, updated_at = :updated_at"

            self.table.update_item(
                Key={"PK": f"APIKEY#{api_key_id}", "SK": "METADATA"},
                UpdateExpression=update_expr,
                ExpressionAttributeValues=expr_attr_values,
            )
            logger.info("api_key_usage_updated", api_key_id=api_key_id)
            return True
        except ClientError as e:
            logger.error("update_api_key_usage_failed", api_key_id=api_key_id, error=str(e))
            return False
