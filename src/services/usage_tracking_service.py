"""Usage tracking service for quota management and analytics."""

import csv
from datetime import datetime, timedelta
from io import StringIO

from src.models.rate_limit import DailyUsageBreakdown, UsageRecord, UsageSummary
from src.utils.dynamo import DynamoDBHelper
from src.utils.id_gen import generate_id
from src.utils.logging import get_logger

logger = get_logger(__name__)


class UsageTrackingService:
    """Service for tracking API usage, quotas, and generating analytics."""

    def __init__(self, db_helper: DynamoDBHelper) -> None:
        """Initialize usage tracking service.

        Args:
            db_helper: DynamoDB helper instance
        """
        self.db = db_helper

    def record_request(
        self,
        api_key: str,
        endpoint: str,
        status_code: int,
        response_time_ms: float,
        cost_usd: float = 0.0,
    ) -> None:
        """Record an API request with metadata.

        Updates the daily usage record for the API key, incrementing counters
        and tracking endpoint usage breakdown.

        Args:
            api_key: API key that made the request
            endpoint: API endpoint path (e.g., "/api/v1/hackathons")
            status_code: HTTP status code (200, 400, 500, etc.)
            response_time_ms: Response time in milliseconds
            cost_usd: Cost of the request in USD (for Bedrock calls)
        """
        try:
            # Get current date in UTC
            now = datetime.utcnow()
            date_str = now.strftime("%Y-%m-%d")

            # Get or create usage record for today
            usage_record = self._get_or_create_usage_record(api_key, date_str)

            # Track successful vs failed requests
            if 200 <= status_code < 400:
                usage_record.successful_requests += 1
            else:
                usage_record.failed_requests += 1

            # Update request count (must equal successful + failed)
            usage_record.request_count = (
                usage_record.successful_requests + usage_record.failed_requests
            )

            # Update cost tracking
            usage_record.total_cost_usd += cost_usd

            # Track endpoint usage breakdown
            if endpoint not in usage_record.endpoints_used:
                usage_record.endpoints_used[endpoint] = 0
            usage_record.endpoints_used[endpoint] += 1

            # Update timestamp
            usage_record.updated_at = now

            # Set DynamoDB keys
            usage_record.set_dynamodb_keys()

            # Save to DynamoDB
            usage_dict = usage_record.model_dump()
            serialized = self.db._serialize_item(usage_dict)
            self.db.table.put_item(Item=serialized)

            logger.info(
                "request_recorded",
                api_key_prefix=api_key[:8],
                endpoint=endpoint,
                status_code=status_code,
                cost_usd=cost_usd,
            )

        except Exception as e:
            logger.error(
                "record_request_failed",
                api_key_prefix=api_key[:8],
                endpoint=endpoint,
                error=str(e),
            )
            # Don't raise - usage tracking failures shouldn't break the API

    def check_daily_quota(self, api_key: str, daily_quota: int) -> tuple[bool, int, int]:
        """Check if API key has exceeded daily quota.

        Quota resets at midnight UTC. Only successful requests count toward quota.

        Args:
            api_key: API key to check
            daily_quota: Maximum requests allowed per day

        Returns:
            Tuple of (allowed: bool, used: int, remaining: int)
            - allowed: True if request is within quota
            - used: Number of successful requests today
            - remaining: Requests remaining in quota
        """
        try:
            # Get current date in UTC
            date_str = datetime.utcnow().strftime("%Y-%m-%d")

            # Get usage record for today
            usage_record = self._get_usage_record(api_key, date_str)

            if not usage_record:
                # No usage today - full quota available
                return (True, 0, daily_quota)

            # Only successful requests count toward quota
            used = usage_record.successful_requests
            remaining = max(0, daily_quota - used)
            allowed = used < daily_quota

            logger.info(
                "daily_quota_checked",
                api_key_prefix=api_key[:8],
                used=used,
                remaining=remaining,
                allowed=allowed,
            )

            return (allowed, used, remaining)

        except Exception as e:
            logger.error(
                "check_daily_quota_failed",
                api_key_prefix=api_key[:8],
                error=str(e),
            )
            # On error, allow the request (fail open)
            return (True, 0, daily_quota)

    def get_usage_summary(
        self,
        api_key: str,
        start_date: datetime,
        end_date: datetime,
    ) -> UsageSummary:
        """Get usage summary for an API key within a date range.

        Args:
            api_key: API key to get summary for
            start_date: Start date (inclusive)
            end_date: End date (inclusive)

        Returns:
            Dictionary with aggregated usage statistics:
            - total_requests: Total number of requests
            - successful_requests: Number of successful requests
            - failed_requests: Number of failed requests
            - total_cost_usd: Total cost in USD
            - endpoints_used: Breakdown by endpoint
            - daily_breakdown: List of daily usage records
        """
        try:
            # Query usage records using GSI1 (APIKEY#{api_key})
            response = self.db.table.query(
                IndexName="GSI1",
                KeyConditionExpression="GSI1PK = :pk AND GSI1SK BETWEEN :start AND :end",
                ExpressionAttributeValues={
                    ":pk": f"APIKEY#{api_key}",
                    ":start": f"DATE#{start_date.strftime('%Y-%m-%d')}",
                    ":end": f"DATE#{end_date.strftime('%Y-%m-%d')}",
                },
            )

            items = response.get("Items", [])

            # Aggregate statistics
            total_requests = 0
            successful_requests = 0
            failed_requests = 0
            total_cost_usd = 0.0
            endpoints_used: dict[str, int] = {}
            daily_breakdown = []

            for item in items:
                try:
                    usage_record = UsageRecord(**item)

                    # Aggregate counters
                    total_requests += usage_record.request_count
                    successful_requests += usage_record.successful_requests
                    failed_requests += usage_record.failed_requests
                    total_cost_usd += usage_record.total_cost_usd

                    # Aggregate endpoint usage
                    for endpoint, count in usage_record.endpoints_used.items():
                        if endpoint not in endpoints_used:
                            endpoints_used[endpoint] = 0
                        endpoints_used[endpoint] += count

                    # Add to daily breakdown
                    daily_breakdown.append(
                        DailyUsageBreakdown(
                            date=usage_record.date,
                            requests=usage_record.request_count,
                            successful=usage_record.successful_requests,
                            failed=usage_record.failed_requests,
                            cost_usd=usage_record.total_cost_usd,
                        )
                    )

                except Exception as e:
                    logger.warning("usage_record_conversion_failed", item=item, error=str(e))
                    continue

            summary = UsageSummary(
                api_key_prefix=api_key[:8],
                start_date=start_date.strftime("%Y-%m-%d"),
                end_date=end_date.strftime("%Y-%m-%d"),
                total_requests=total_requests,
                successful_requests=successful_requests,
                failed_requests=failed_requests,
                total_cost_usd=round(total_cost_usd, 4),
                endpoints_used=endpoints_used,
                daily_breakdown=daily_breakdown,
            )

            logger.info(
                "usage_summary_generated",
                api_key_prefix=api_key[:8],
                total_requests=total_requests,
                date_range_days=(end_date - start_date).days + 1,
            )

            return summary

        except Exception as e:
            logger.error(
                "get_usage_summary_failed",
                api_key_prefix=api_key[:8],
                error=str(e),
            )
            return UsageSummary(
                api_key_prefix=api_key[:8],
                start_date=start_date.strftime("%Y-%m-%d"),
                end_date=end_date.strftime("%Y-%m-%d"),
                total_requests=0,
                successful_requests=0,
                failed_requests=0,
                total_cost_usd=0.0,
                endpoints_used={},
                daily_breakdown=[],
                error=str(e),
            )

    def export_usage_csv(
        self,
        api_key: str,
        start_date: datetime,
        end_date: datetime,
    ) -> str:
        """Export usage data to CSV format.

        Args:
            api_key: API key to export data for
            start_date: Start date (inclusive)
            end_date: End date (inclusive)

        Returns:
            CSV string with columns: date, requests, successful, failed, cost_usd, endpoints
        """
        try:
            # Get usage summary
            summary = self.get_usage_summary(api_key, start_date, end_date)

            # Create CSV in memory
            output = StringIO()
            writer = csv.writer(output)

            # Write header
            writer.writerow(
                [
                    "date",
                    "total_requests",
                    "successful_requests",
                    "failed_requests",
                    "total_cost_usd",
                    "top_endpoint",
                    "top_endpoint_count",
                ]
            )

            # Write daily breakdown
            for day in summary["daily_breakdown"]:
                # Find top endpoint for this day (would need per-day endpoint data)
                # For now, we'll use the overall top endpoint
                top_endpoint = ""
                top_count = 0
                if summary["endpoints_used"]:
                    top_endpoint = max(
                        summary["endpoints_used"],
                        key=summary["endpoints_used"].get,  # type: ignore
                    )
                    top_count = summary["endpoints_used"][top_endpoint]

                writer.writerow(
                    [
                        day["date"],
                        day["requests"],
                        day["successful"],
                        day["failed"],
                        f"{day['cost_usd']:.4f}",
                        top_endpoint,
                        top_count,
                    ]
                )

            # Write summary row
            writer.writerow([])
            writer.writerow(["SUMMARY"])
            writer.writerow(["Total Requests", summary["total_requests"]])
            writer.writerow(["Successful Requests", summary["successful_requests"]])
            writer.writerow(["Failed Requests", summary["failed_requests"]])
            writer.writerow(["Total Cost (USD)", f"{summary['total_cost_usd']:.4f}"])

            # Write endpoint breakdown
            writer.writerow([])
            writer.writerow(["ENDPOINT BREAKDOWN"])
            writer.writerow(["Endpoint", "Request Count"])
            for endpoint, count in sorted(
                summary["endpoints_used"].items(),
                key=lambda x: x[1],
                reverse=True,
            ):
                writer.writerow([endpoint, count])

            csv_content = output.getvalue()
            output.close()

            logger.info(
                "usage_csv_exported",
                api_key_prefix=api_key[:8],
                rows=len(summary["daily_breakdown"]),
            )

            return csv_content

        except Exception as e:
            logger.error(
                "export_usage_csv_failed",
                api_key_prefix=api_key[:8],
                error=str(e),
            )
            return f"Error exporting CSV: {e}"

    def _get_usage_record(self, api_key: str, date: str) -> UsageRecord | None:
        """Get usage record for a specific date.

        Args:
            api_key: API key
            date: Date in YYYY-MM-DD format

        Returns:
            UsageRecord if found, None otherwise
        """
        try:
            response = self.db.table.get_item(
                Key={
                    "PK": f"USAGE#{api_key}#{date}",
                    "SK": "SUMMARY",
                }
            )

            item = response.get("Item")
            if not item:
                return None

            return UsageRecord(**item)

        except Exception as e:
            logger.error(
                "get_usage_record_failed",
                api_key_prefix=api_key[:8],
                date=date,
                error=str(e),
            )
            return None

    def _get_or_create_usage_record(self, api_key: str, date: str) -> UsageRecord:
        """Get or create usage record for a specific date.

        Args:
            api_key: API key
            date: Date in YYYY-MM-DD format

        Returns:
            UsageRecord (existing or newly created)
        """
        # Try to get existing record
        existing = self._get_usage_record(api_key, date)
        if existing:
            return existing

        # Create new record
        now = datetime.utcnow()
        usage_record = UsageRecord(
            usage_id=generate_id(),
            api_key=api_key,
            date=date,
            request_count=0,
            successful_requests=0,
            failed_requests=0,
            total_cost_usd=0.0,
            bedrock_cost_usd=0.0,
            lambda_cost_usd=0.0,
            endpoints_used={},
            created_at=now,
            updated_at=now,
        )

        return usage_record

    def get_quota_reset_time(self) -> datetime:
        """Get the next quota reset time (midnight UTC).

        Returns:
            Datetime of next midnight UTC
        """
        now = datetime.utcnow()
        # Next midnight UTC
        tomorrow = now.date() + timedelta(days=1)
        return datetime.combine(tomorrow, datetime.min.time())
