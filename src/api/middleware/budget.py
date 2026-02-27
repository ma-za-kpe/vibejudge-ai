"""Budget enforcement middleware for multi-level cost control."""

from collections.abc import Callable
from datetime import datetime
from typing import Any

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from src.models.api_key import APIKey
from src.models.rate_limit import BudgetTracking
from src.utils.config import settings
from src.utils.dynamo import DynamoDBHelper
from src.utils.logging import get_logger

logger = get_logger(__name__)


class BudgetMiddleware(BaseHTTPMiddleware):
    """Middleware for enforcing budget limits at submission, hackathon, and API key levels.
    
    This middleware:
    1. Estimates cost for analysis requests
    2. Checks per-submission budget cap (configurable, default $0.50)
    3. Checks per-hackathon budget limit
    4. Checks per-API-key cumulative budget
    5. Returns 402 Payment Required if any limit exceeded
    6. Sends alerts at 50%, 80%, 90%, 100% thresholds
    7. Updates budget tracking after successful requests
    """

    def __init__(
        self,
        app: ASGIApp,
        db_helper: DynamoDBHelper,
        max_cost_per_submission: float | None = None,
    ) -> None:
        """Initialize budget enforcement middleware.
        
        Args:
            app: ASGI application
            db_helper: DynamoDB helper instance
            max_cost_per_submission: Maximum cost per submission (default from config)
        """
        super().__init__(app)
        self.db_helper = db_helper
        self.max_cost_per_submission = max_cost_per_submission or settings.max_cost_per_submission_usd

    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        """Process request through budget enforcement checks.
        
        Args:
            request: Incoming HTTP request
            call_next: Next middleware/route handler
            
        Returns:
            HTTP response with budget information or 402 if exceeded
        """
        # Only check budget for analysis endpoints
        if not self._should_check_budget(request):
            return await call_next(request)

        # Get API key data from request state (set by RateLimitMiddleware)
        api_key = getattr(request.state, "api_key", None)
        api_key_data = getattr(request.state, "api_key_data", None)

        if not api_key or not api_key_data:
            # This shouldn't happen if RateLimitMiddleware runs first
            logger.error("budget_check_missing_api_key", path=request.url.path)
            return Response(
                status_code=401,
                content='{"error": "Missing API key data"}',
                media_type="application/json",
            )

        # Extract hackathon_id from path (e.g., /api/v1/hackathons/{id}/analyze)
        hackathon_id = self._extract_hackathon_id(request)

        # Estimate cost for this request
        estimated_cost = await self._estimate_request_cost(request, hackathon_id)

        # Check all three budget levels
        budget_check_result = await self.check_budget_limits(
            api_key=api_key,
            api_key_data=api_key_data,
            hackathon_id=hackathon_id,
            estimated_cost=estimated_cost,
        )

        if not budget_check_result["allowed"]:
            logger.warning(
                "budget_exceeded",
                api_key_prefix=api_key[:8],
                level=budget_check_result["level"],
                estimated_cost=estimated_cost,
                limit=budget_check_result["limit"],
                current=budget_check_result["current"],
            )

            return Response(
                status_code=402,
                content=self._format_budget_error(budget_check_result, estimated_cost),
                media_type="application/json",
            )

        # Store estimated cost in request state for downstream use
        request.state.estimated_cost = estimated_cost

        # Process request
        response = await call_next(request)

        # Update budget tracking after successful request (only for 2xx responses)
        if 200 <= response.status_code < 300:
            await self._update_budget_tracking(
                api_key=api_key,
                hackathon_id=hackathon_id,
                actual_cost=estimated_cost,  # Use actual cost from response if available
            )

        return response

    def _should_check_budget(self, request: Request) -> bool:
        """Determine if budget check is needed for this request.
        
        Args:
            request: Incoming HTTP request
            
        Returns:
            True if budget check should be performed
        """
        # Check budget for analysis endpoints
        analysis_paths = ["/analyze", "/submissions"]
        return any(path in request.url.path for path in analysis_paths)

    def _extract_hackathon_id(self, request: Request) -> str | None:
        """Extract hackathon ID from request path.
        
        Args:
            request: Incoming HTTP request
            
        Returns:
            Hackathon ID or None if not found
        """
        # Parse path like /api/v1/hackathons/{hackathon_id}/analyze
        path_parts = request.url.path.split("/")
        try:
            if "hackathons" in path_parts:
                idx = path_parts.index("hackathons")
                if idx + 1 < len(path_parts):
                    return path_parts[idx + 1]
        except (ValueError, IndexError):
            pass
        return None

    async def _estimate_request_cost(
        self, request: Request, hackathon_id: str | None
    ) -> float:
        """Estimate cost for this request.
        
        Args:
            request: Incoming HTTP request
            hackathon_id: Hackathon ID if available
            
        Returns:
            Estimated cost in USD
        """
        # For MVP, use a simple estimation based on endpoint
        # In production, this would use CostEstimationService with repo size analysis

        if "/analyze" in request.url.path:
            # Full hackathon analysis - estimate based on submission count
            if hackathon_id:
                try:
                    submissions = self.db_helper.list_submissions(hackathon_id)
                    submission_count = len(submissions)
                    # Average cost per submission: $0.063 (from design doc)
                    return submission_count * 0.063
                except Exception as e:
                    logger.error("cost_estimation_failed", error=str(e))
                    # Conservative estimate
                    return 5.0
            else:
                # Single submission analysis
                return 0.063

        # Default for other endpoints
        return 0.0

    async def check_budget_limits(
        self,
        api_key: str,
        api_key_data: APIKey,
        hackathon_id: str | None,
        estimated_cost: float,
    ) -> dict[str, Any]:
        """Check all three budget levels: submission, hackathon, and API key.
        
        Args:
            api_key: API key string
            api_key_data: API key metadata object
            hackathon_id: Hackathon ID if available
            estimated_cost: Estimated cost for this request
            
        Returns:
            Dict with keys: allowed (bool), level (str), limit (float), current (float), message (str)
        """
        # Level 1: Per-submission cap
        if estimated_cost > self.max_cost_per_submission:
            return {
                "allowed": False,
                "level": "submission",
                "limit": self.max_cost_per_submission,
                "current": estimated_cost,
                "message": f"Per-submission cost limit exceeded. Estimated: ${estimated_cost:.4f}, Limit: ${self.max_cost_per_submission:.4f}",
            }

        # Level 2: Per-API-key budget
        api_key_budget = await self._get_budget_tracking("api_key", api_key)
        if api_key_budget:
            if api_key_budget.current_spend_usd + estimated_cost > api_key_budget.budget_limit_usd:
                return {
                    "allowed": False,
                    "level": "api_key",
                    "limit": api_key_budget.budget_limit_usd,
                    "current": api_key_budget.current_spend_usd,
                    "message": f"API key budget limit exceeded. Current: ${api_key_budget.current_spend_usd:.4f}, Limit: ${api_key_budget.budget_limit_usd:.4f}",
                }

            # Check for alert thresholds
            await self._check_and_send_alerts(api_key_budget, estimated_cost, "api_key", api_key)

        # Level 3: Per-hackathon budget
        if hackathon_id:
            hackathon_budget = await self._get_budget_tracking("hackathon", hackathon_id)
            if hackathon_budget:
                if hackathon_budget.current_spend_usd + estimated_cost > hackathon_budget.budget_limit_usd:
                    return {
                        "allowed": False,
                        "level": "hackathon",
                        "limit": hackathon_budget.budget_limit_usd,
                        "current": hackathon_budget.current_spend_usd,
                        "message": f"Hackathon budget limit exceeded. Current: ${hackathon_budget.current_spend_usd:.4f}, Limit: ${hackathon_budget.budget_limit_usd:.4f}",
                    }

                # Check for alert thresholds
                await self._check_and_send_alerts(hackathon_budget, estimated_cost, "hackathon", hackathon_id)

        # All checks passed
        return {
            "allowed": True,
            "level": None,
            "limit": None,
            "current": None,
            "message": None,
        }

    async def _get_budget_tracking(
        self, entity_type: str, entity_id: str
    ) -> BudgetTracking | None:
        """Get budget tracking record from DynamoDB.
        
        Args:
            entity_type: Type of entity (api_key, hackathon, submission)
            entity_id: Entity identifier
            
        Returns:
            BudgetTracking object or None if not found
        """
        try:
            result = self.db_helper.table.get_item(
                Key={
                    "PK": f"BUDGET#{entity_type}#{entity_id}",
                    "SK": "TRACKING",
                }
            )

            if "Item" not in result:
                # Create default budget tracking if not exists
                return await self._create_default_budget_tracking(entity_type, entity_id)

            item = result["Item"]

            # Convert datetime strings back to datetime objects
            for field in ["created_at", "updated_at"]:
                if field in item and item[field]:
                    if isinstance(item[field], str):
                        item[field] = datetime.fromisoformat(item[field])

            return BudgetTracking(**item)

        except Exception as e:
            logger.error(
                "budget_tracking_lookup_failed",
                entity_type=entity_type,
                entity_id=entity_id[:8] if entity_type == "api_key" else entity_id,
                error=str(e),
            )
            return None

    async def _create_default_budget_tracking(
        self, entity_type: str, entity_id: str
    ) -> BudgetTracking | None:
        """Create default budget tracking record.
        
        Args:
            entity_type: Type of entity (api_key, hackathon, submission)
            entity_id: Entity identifier
            
        Returns:
            BudgetTracking object or None if creation fails
        """
        try:
            # Get default budget limit based on entity type
            if entity_type == "api_key":
                # Get from API key metadata
                api_key_data = self.db_helper.get_api_key_by_secret(entity_id)
                if not api_key_data:
                    return None
                budget_limit = api_key_data.get("budget_limit_usd", settings.default_budget_limit_usd)
            elif entity_type == "hackathon":
                # Get from hackathon metadata
                hackathon_data = self.db_helper.get_hackathon(entity_id)
                if not hackathon_data:
                    return None
                # Use default if hackathon doesn't have budget_limit_usd field
                budget_limit = hackathon_data.get("budget_limit_usd", settings.default_budget_limit_usd)
            else:
                # Submission level uses per-submission cap
                budget_limit = self.max_cost_per_submission

            # Create budget tracking record
            budget_tracking = BudgetTracking(
                entity_type=entity_type,
                entity_id=entity_id,
                budget_limit_usd=budget_limit,
                current_spend_usd=0.0,
            )
            budget_tracking.set_dynamodb_keys()

            # Store in DynamoDB
            self.db_helper.table.put_item(Item=budget_tracking.model_dump())

            logger.info(
                "budget_tracking_created",
                entity_type=entity_type,
                entity_id=entity_id[:8] if entity_type == "api_key" else entity_id,
                budget_limit=budget_limit,
            )

            return budget_tracking

        except Exception as e:
            logger.error(
                "budget_tracking_creation_failed",
                entity_type=entity_type,
                entity_id=entity_id[:8] if entity_type == "api_key" else entity_id,
                error=str(e),
            )
            return None

    async def _check_and_send_alerts(
        self,
        budget_tracking: BudgetTracking,
        estimated_cost: float,
        entity_type: str,
        entity_id: str,
    ) -> None:
        """Check if budget alerts should be sent and send them.
        
        Args:
            budget_tracking: Current budget tracking record
            estimated_cost: Estimated cost for this request
            entity_type: Type of entity (api_key, hackathon, submission)
            entity_id: Entity identifier
        """
        # Calculate projected usage percentage after this request
        projected_spend = budget_tracking.current_spend_usd + estimated_cost
        projected_percentage = (projected_spend / budget_tracking.budget_limit_usd) * 100

        # Check each threshold
        for threshold in [50, 80, 90, 100]:
            if budget_tracking.should_send_alert(threshold) and projected_percentage >= threshold:
                await self._send_budget_alert(
                    entity_type=entity_type,
                    entity_id=entity_id,
                    threshold=threshold,
                    current_spend=budget_tracking.current_spend_usd,
                    budget_limit=budget_tracking.budget_limit_usd,
                    projected_spend=projected_spend,
                )

                # Mark alert as sent
                await self._mark_alert_sent(budget_tracking, threshold)

    async def _send_budget_alert(
        self,
        entity_type: str,
        entity_id: str,
        threshold: int,
        current_spend: float,
        budget_limit: float,
        projected_spend: float,
    ) -> None:
        """Send budget alert notification.
        
        Args:
            entity_type: Type of entity (api_key, hackathon, submission)
            entity_id: Entity identifier
            threshold: Alert threshold percentage (50, 80, 90, 100)
            current_spend: Current spend in USD
            budget_limit: Budget limit in USD
            projected_spend: Projected spend after current request
        """
        logger.warning(
            "budget_alert",
            entity_type=entity_type,
            entity_id=entity_id[:8] if entity_type == "api_key" else entity_id,
            threshold=threshold,
            current_spend=current_spend,
            budget_limit=budget_limit,
            projected_spend=projected_spend,
            usage_percentage=f"{(projected_spend / budget_limit) * 100:.1f}%",
        )

        # TODO: In production, send SNS notification or email
        # For MVP, logging is sufficient

    async def _mark_alert_sent(
        self, budget_tracking: BudgetTracking, threshold: int
    ) -> None:
        """Mark alert as sent in DynamoDB.
        
        Args:
            budget_tracking: Budget tracking record
            threshold: Alert threshold (50, 80, 90, 100)
        """
        try:
            alert_field = f"alert_{threshold}_sent"

            self.db_helper.table.update_item(
                Key={
                    "PK": budget_tracking.PK,
                    "SK": budget_tracking.SK,
                },
                UpdateExpression=f"SET {alert_field} = :true",
                ExpressionAttributeValues={
                    ":true": True,
                },
            )

            logger.info(
                "budget_alert_marked",
                entity_type=budget_tracking.entity_type,
                entity_id=budget_tracking.entity_id[:8] if budget_tracking.entity_type == "api_key" else budget_tracking.entity_id,
                threshold=threshold,
            )

        except Exception as e:
            logger.error("mark_alert_sent_failed", error=str(e), threshold=threshold)

    async def _update_budget_tracking(
        self,
        api_key: str,
        hackathon_id: str | None,
        actual_cost: float,
    ) -> None:
        """Update budget tracking after successful request.
        
        Args:
            api_key: API key string
            hackathon_id: Hackathon ID if available
            actual_cost: Actual cost incurred
        """
        try:
            # Update API key budget
            await self._increment_budget_spend("api_key", api_key, actual_cost)

            # Update hackathon budget if applicable
            if hackathon_id:
                await self._increment_budget_spend("hackathon", hackathon_id, actual_cost)

            logger.info(
                "budget_tracking_updated",
                api_key_prefix=api_key[:8],
                hackathon_id=hackathon_id,
                cost=actual_cost,
            )

        except Exception as e:
            logger.error("budget_tracking_update_failed", error=str(e))

    async def _increment_budget_spend(
        self, entity_type: str, entity_id: str, cost: float
    ) -> None:
        """Atomically increment budget spend in DynamoDB.
        
        Args:
            entity_type: Type of entity (api_key, hackathon, submission)
            entity_id: Entity identifier
            cost: Cost to add
        """
        try:
            self.db_helper.table.update_item(
                Key={
                    "PK": f"BUDGET#{entity_type}#{entity_id}",
                    "SK": "TRACKING",
                },
                UpdateExpression="SET current_spend_usd = if_not_exists(current_spend_usd, :zero) + :cost, last_updated = :updated",
                ExpressionAttributeValues={
                    ":zero": 0.0,
                    ":cost": cost,
                    ":updated": datetime.utcnow().isoformat(),
                },
            )

        except Exception as e:
            logger.error(
                "increment_budget_spend_failed",
                entity_type=entity_type,
                entity_id=entity_id[:8] if entity_type == "api_key" else entity_id,
                error=str(e),
            )

    def _format_budget_error(
        self, budget_check_result: dict[str, Any], estimated_cost: float
    ) -> str:
        """Format budget exceeded error response.
        
        Args:
            budget_check_result: Result from check_budget_limits
            estimated_cost: Estimated cost for this request
            
        Returns:
            JSON error response string
        """
        import json

        return json.dumps({
            "error": "Budget limit exceeded",
            "level": budget_check_result["level"],
            "message": budget_check_result["message"],
            "details": {
                "estimated_cost_usd": round(estimated_cost, 4),
                "current_spend_usd": round(budget_check_result["current"], 4) if budget_check_result["current"] else None,
                "budget_limit_usd": round(budget_check_result["limit"], 4) if budget_check_result["limit"] else None,
                "remaining_budget_usd": round(budget_check_result["limit"] - budget_check_result["current"], 4) if budget_check_result["limit"] and budget_check_result["current"] else None,
            },
        })
