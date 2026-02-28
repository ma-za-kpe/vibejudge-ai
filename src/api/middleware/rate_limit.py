"""Rate limiting middleware using sliding window algorithm with DynamoDB."""

import time
from collections.abc import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from src.models.api_key import APIKey
from src.utils.dynamo import DynamoDBHelper
from src.utils.id_gen import generate_id
from src.utils.logging import get_logger

logger = get_logger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware for enforcing per-API-key rate limits using sliding window algorithm.

    This middleware:
    1. Extracts API key from X-API-Key header
    2. Validates API key exists and is active
    3. Checks rate limit using sliding window counter in DynamoDB
    4. Increments counter atomically
    5. Checks daily quota
    6. Returns 429 if limits exceeded
    7. Adds RFC 6585 rate limit headers to all responses
    8. Exempts /health and /docs endpoints
    """

    def __init__(
        self,
        app: ASGIApp,
        db_helper: DynamoDBHelper,
        exempt_paths: list[str] | None = None,
    ) -> None:
        """Initialize rate limit middleware.

        Args:
            app: ASGI application
            db_helper: DynamoDB helper instance
            exempt_paths: List of paths to exempt from rate limiting (supports * wildcard)
        """
        super().__init__(app)
        self.db_helper = db_helper
        self.exempt_paths = exempt_paths or [
            "/health",
            "/api/v1/health",  # Health check with prefix
            "/docs",
            "/openapi.json",
            "/redoc",
            "/api/v1/organizers",  # Registration endpoint (public)
            "/organizers",  # Registration endpoint (without prefix)
            "/api/v1/organizers/login",  # Login endpoint (public)
            "/organizers/login",  # Login endpoint (without prefix)
        ]

    def _is_path_exempt(self, path: str) -> bool:
        """Check if path is exempt from rate limiting (supports * wildcard).

        Args:
            path: Request path to check

        Returns:
            True if path is exempt, False otherwise
        """
        for exempt_path in self.exempt_paths:
            # Exact match
            if path == exempt_path:
                return True

            # Wildcard match (e.g., "/api/v1/public/hackathons/*/submissions")
            if "*" in exempt_path:
                import re

                # Convert wildcard pattern to regex (escape special chars, replace * with .*)
                pattern = "^" + re.escape(exempt_path).replace(r"\*", ".*") + "$"
                if re.match(pattern, path):
                    return True

        return False

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request through rate limiting checks.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware/route handler

        Returns:
            HTTP response with rate limit headers
        """
        # Check if path is exempt (supports wildcard matching with *)
        logger.info("rate_limit_check_path", path=request.url.path, exempt_paths=self.exempt_paths)
        if self._is_path_exempt(request.url.path):
            logger.info("path_exempt_from_rate_limit", path=request.url.path)
            return await call_next(request)

        # Extract API key from header
        api_key = request.headers.get("X-API-Key")
        if not api_key:
            return Response(
                status_code=401,
                content='{"error": "Missing X-API-Key header"}',
                media_type="application/json",
            )

        # Validate API key and get metadata
        api_key_data = await self._get_api_key(api_key)
        if not api_key_data:
            return Response(
                status_code=401,
                content='{"error": "Invalid API key"}',
                media_type="application/json",
            )

        # Check if key is active and not expired
        if not api_key_data.is_valid():
            error_msg = "API key expired" if api_key_data.is_expired() else "API key inactive"
            return Response(
                status_code=401,
                content=f'{{"error": "{error_msg}"}}',
                media_type="application/json",
            )

        # Check rate limit (requests per second)
        current_time = int(time.time())
        allowed, remaining, reset_time = await self.check_rate_limit(
            api_key=api_key,
            window_start=current_time,
            rate_limit=api_key_data.rate_limit_per_second,
        )

        if not allowed:
            retry_after = reset_time - current_time
            return Response(
                status_code=429,
                headers={
                    "X-RateLimit-Limit": str(api_key_data.rate_limit_per_second),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(reset_time),
                    "Retry-After": str(retry_after),
                },
                content=f'{{"error": "Rate limit exceeded: {api_key_data.rate_limit_per_second} req/sec", "retry_after": {retry_after}}}',
                media_type="application/json",
            )

        # Check daily quota
        date_str = time.strftime("%Y-%m-%d", time.gmtime(current_time))
        quota_allowed, used, quota_remaining = await self.check_daily_quota(
            api_key=api_key,
            date=date_str,
            daily_quota=api_key_data.daily_quota,
        )

        if not quota_allowed:
            # Calculate midnight UTC reset time
            import datetime

            tomorrow = datetime.datetime.utcnow().date() + datetime.timedelta(days=1)
            reset_timestamp = int(
                datetime.datetime.combine(tomorrow, datetime.time.min).timestamp()
            )

            return Response(
                status_code=429,
                headers={
                    "X-Quota-Limit": str(api_key_data.daily_quota),
                    "X-Quota-Remaining": "0",
                    "X-Quota-Reset": str(reset_timestamp),
                },
                content=f'{{"error": "Daily quota exceeded. Resets at midnight UTC", "quota_reset": {reset_timestamp}}}',
                media_type="application/json",
            )

        # Store API key data in request state for downstream use
        request.state.api_key = api_key
        request.state.api_key_data = api_key_data

        # Process request
        response = await call_next(request)

        # Add rate limit headers to response
        response.headers["X-RateLimit-Limit"] = str(api_key_data.rate_limit_per_second)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset_time)
        response.headers["X-Quota-Limit"] = str(api_key_data.daily_quota)
        response.headers["X-Quota-Remaining"] = str(quota_remaining)

        return response

    async def _get_api_key(self, api_key: str) -> APIKey | None:
        """Get API key metadata from DynamoDB using Advanced API key system.

        Args:
            api_key: API key string

        Returns:
            APIKey object or None if not found
        """
        try:
            logger.info("api_key_lookup", api_key_prefix=api_key[:8])

            # Use Advanced API key system only
            api_key_data = self.db_helper.get_api_key_by_secret(api_key)

            if api_key_data:
                # Convert DynamoDB item to APIKey model
                from datetime import datetime

                # Convert ISO strings back to datetime objects
                for field in [
                    "created_at",
                    "updated_at",
                    "expires_at",
                    "deprecated_at",
                    "last_used_at",
                ]:
                    if field in api_key_data and api_key_data[field]:
                        if isinstance(api_key_data[field], str):
                            api_key_data[field] = datetime.fromisoformat(api_key_data[field])

                # Create APIKey model instance
                api_key_obj = APIKey(**api_key_data)
                return api_key_obj

            logger.warning("api_key_not_found", api_key_prefix=api_key[:8])
            return None

        except Exception as e:
            logger.error("api_key_lookup_failed", error=str(e), api_key_prefix=api_key[:8])
            return None

    async def check_rate_limit(
        self,
        api_key: str,
        window_start: int,
        rate_limit: int,
    ) -> tuple[bool, int, int]:
        """Check and enforce rate limit using sliding window algorithm.

        Args:
            api_key: API key string
            window_start: Current Unix timestamp (second precision)
            rate_limit: Maximum requests per second

        Returns:
            Tuple of (allowed, remaining, reset_time)
            - allowed: Whether request is allowed
            - remaining: Requests remaining in window
            - reset_time: Unix timestamp when window resets
        """
        try:
            # Get current counter value
            counter_data = self.db_helper.table.get_item(
                Key={
                    "PK": f"RATELIMIT#{api_key}#{window_start}",
                    "SK": "COUNTER",
                }
            ).get("Item")

            current_count = counter_data.get("request_count", 0) if counter_data else 0

            # Check if limit exceeded
            if current_count >= rate_limit:
                remaining = 0
                reset_time = window_start + 1
                return False, remaining, reset_time

            # Increment counter atomically
            new_count = await self._increment_counter_atomic(
                api_key=api_key,
                window_start=window_start,
                ttl=window_start + 60,
            )

            remaining = max(0, rate_limit - new_count)
            reset_time = window_start + 1

            logger.info(
                "rate_limit_check",
                api_key_prefix=api_key[:8],
                count=new_count,
                limit=rate_limit,
                remaining=remaining,
            )

            return True, remaining, reset_time

        except Exception as e:
            logger.error("rate_limit_check_failed", error=str(e))
            # Fail open to avoid blocking legitimate traffic
            return True, rate_limit, window_start + 1

    async def _increment_counter_atomic(
        self,
        api_key: str,
        window_start: int,
        ttl: int,
    ) -> int:
        """Atomically increment rate limit counter in DynamoDB.

        Args:
            api_key: API key string
            window_start: Window start timestamp
            ttl: TTL for auto-deletion

        Returns:
            New counter value after increment
        """
        try:
            response = self.db_helper.table.update_item(
                Key={
                    "PK": f"RATELIMIT#{api_key}#{window_start}",
                    "SK": "COUNTER",
                },
                UpdateExpression="SET request_count = if_not_exists(request_count, :zero) + :inc, #ttl = :ttl, api_key = :api_key, window_start = :window_start, entity_type = :entity_type",
                ExpressionAttributeNames={
                    "#ttl": "ttl",
                },
                ExpressionAttributeValues={
                    ":zero": 0,
                    ":inc": 1,
                    ":ttl": ttl,
                    ":api_key": api_key,
                    ":window_start": window_start,
                    ":entity_type": "RATE_LIMIT_COUNTER",
                },
                ReturnValues="UPDATED_NEW",
            )

            return int(response["Attributes"]["request_count"])

        except Exception as e:
            logger.error("increment_counter_failed", error=str(e))
            raise

    async def check_daily_quota(
        self,
        api_key: str,
        date: str,
        daily_quota: int,
    ) -> tuple[bool, int, int]:
        """Check daily quota usage.

        Args:
            api_key: API key string
            date: Date in YYYY-MM-DD format
            daily_quota: Maximum requests per day

        Returns:
            Tuple of (allowed, used, remaining)
            - allowed: Whether request is allowed
            - used: Requests used today
            - remaining: Requests remaining today
        """
        try:
            # Get usage record for today
            usage_data = self.db_helper.table.get_item(
                Key={
                    "PK": f"USAGE#{api_key}#{date}",
                    "SK": "SUMMARY",
                }
            ).get("Item")

            current_usage = usage_data.get("request_count", 0) if usage_data else 0

            # Check if quota exceeded
            if current_usage >= daily_quota:
                return False, current_usage, 0

            # Increment usage counter
            await self._increment_usage_counter(api_key, date)

            new_usage = current_usage + 1
            remaining = max(0, daily_quota - new_usage)

            logger.info(
                "daily_quota_check",
                api_key_prefix=api_key[:8],
                date=date,
                used=new_usage,
                quota=daily_quota,
                remaining=remaining,
            )

            return True, new_usage, remaining

        except Exception as e:
            logger.error("daily_quota_check_failed", error=str(e))
            # Fail open to avoid blocking legitimate traffic
            return True, 0, daily_quota

    async def _increment_usage_counter(
        self,
        api_key: str,
        date: str,
    ) -> None:
        """Increment daily usage counter.

        Args:
            api_key: API key string
            date: Date in YYYY-MM-DD format
        """
        try:
            from datetime import datetime

            self.db_helper.table.update_item(
                Key={
                    "PK": f"USAGE#{api_key}#{date}",
                    "SK": "SUMMARY",
                },
                UpdateExpression=(
                    "SET request_count = if_not_exists(request_count, :zero) + :inc, "
                    "last_updated = :updated, "
                    "api_key = :api_key, "
                    "#date = :date, "
                    "usage_id = if_not_exists(usage_id, :usage_id), "
                    "successful_requests = if_not_exists(successful_requests, :zero), "
                    "failed_requests = if_not_exists(failed_requests, :zero), "
                    "total_cost_usd = if_not_exists(total_cost_usd, :zero_decimal), "
                    "bedrock_cost_usd = if_not_exists(bedrock_cost_usd, :zero_decimal), "
                    "lambda_cost_usd = if_not_exists(lambda_cost_usd, :zero_decimal), "
                    "entity_type = :entity_type, "
                    "GSI1PK = :gsi1pk, "
                    "GSI1SK = :gsi1sk"
                ),
                ExpressionAttributeNames={
                    "#date": "date",
                },
                ExpressionAttributeValues={
                    ":zero": 0,
                    ":zero_decimal": 0.0,
                    ":inc": 1,
                    ":updated": datetime.utcnow().isoformat(),
                    ":api_key": api_key,
                    ":date": date,
                    ":usage_id": generate_id(),
                    ":entity_type": "USAGE_RECORD",
                    ":gsi1pk": f"APIKEY#{api_key}",
                    ":gsi1sk": f"DATE#{date}",
                },
            )

        except Exception as e:
            logger.error("increment_usage_counter_failed", error=str(e))
            # Don't raise - usage tracking is not critical for request processing
