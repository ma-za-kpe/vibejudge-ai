"""Security event logging middleware for monitoring and anomaly detection."""

import time
from collections.abc import Callable
from datetime import datetime

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from src.models.rate_limit import SecurityEvent, Severity
from src.utils.dynamo import DynamoDBHelper
from src.utils.logging import get_logger

logger = get_logger(__name__)


class SecurityLoggerMiddleware(BaseHTTPMiddleware):
    """Middleware for logging security events and detecting anomalies.
    
    This middleware:
    1. Logs all authentication failures (401/403)
    2. Logs rate limit violations (429)
    3. Logs budget exceeded events (402)
    4. Detects unusual patterns (>100 req/min from single API key)
    5. Masks sensitive data (only logs first 8 chars of API keys)
    6. Stores events in DynamoDB with 30-day TTL
    7. Triggers CloudWatch alarms for critical anomalies
    """

    def __init__(
        self,
        app: ASGIApp,
        db_helper: DynamoDBHelper,
        anomaly_threshold: int = 100,  # requests per minute
    ) -> None:
        """Initialize security logger middleware.
        
        Args:
            app: ASGI application
            db_helper: DynamoDB helper instance
            anomaly_threshold: Requests per minute threshold for anomaly detection
        """
        super().__init__(app)
        self.db_helper = db_helper
        self.anomaly_threshold = anomaly_threshold

    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        """Process request and log security events.
        
        Args:
            request: Incoming HTTP request
            call_next: Next middleware/route handler
            
        Returns:
            HTTP response
        """
        # Extract API key (may be None for unauthenticated requests)
        api_key = request.headers.get("X-API-Key")
        api_key_prefix = api_key[:8] if api_key else "NONE"

        # Record request start time
        start_time = time.time()

        # Process request
        response = await call_next(request)

        # Calculate request duration
        duration_ms = (time.time() - start_time) * 1000

        # Log security events based on status code
        await self._log_security_event_if_needed(
            request=request,
            response=response,
            api_key_prefix=api_key_prefix,
            duration_ms=duration_ms,
        )

        # Check for anomalies if API key is present
        if api_key:
            await self._detect_and_log_anomalies(api_key, api_key_prefix)

        return response

    async def _log_security_event_if_needed(
        self,
        request: Request,
        response: Response,
        api_key_prefix: str,
        duration_ms: float,
    ) -> None:
        """Log security event if status code indicates a security issue.
        
        Args:
            request: HTTP request
            response: HTTP response
            api_key_prefix: First 8 characters of API key (masked)
            duration_ms: Request duration in milliseconds
        """
        status_code = response.status_code

        # Determine event type and severity based on status code
        event_type = None
        severity = None

        if status_code == 401:
            event_type = "auth_failure"
            severity = Severity.MEDIUM
        elif status_code == 403:
            event_type = "auth_failure"
            severity = Severity.HIGH
        elif status_code == 429:
            event_type = "rate_limit"
            severity = Severity.MEDIUM
        elif status_code == 402:
            event_type = "budget_exceeded"
            severity = Severity.HIGH
        elif status_code >= 500:
            # Server errors might indicate attacks or system issues
            event_type = "server_error"
            severity = Severity.HIGH

        # Log event if it's a security-relevant status code
        if event_type:
            await self.log_security_event(
                event_type=event_type,
                api_key_prefix=api_key_prefix,
                severity=severity,
                details={
                    "path": request.url.path,
                    "method": request.method,
                    "status_code": status_code,
                    "duration_ms": round(duration_ms, 2),
                    "user_agent": request.headers.get("User-Agent", "unknown"),
                    "ip_address": request.client.host if request.client else "unknown",
                },
            )

    async def log_security_event(
        self,
        event_type: str,
        api_key_prefix: str,
        severity: Severity,
        details: dict,
    ) -> None:
        """Log a security event to DynamoDB.
        
        Args:
            event_type: Type of security event (auth_failure, rate_limit, budget_exceeded, anomaly)
            api_key_prefix: First 8 characters of API key (masked)
            severity: Event severity level
            details: Additional event details
        """
        try:
            # Create security event
            event = SecurityEvent(
                event_id=generate_id(),
                event_type=event_type,
                api_key_prefix=api_key_prefix,
                severity=severity,
                timestamp=datetime.utcnow(),
                details=details,
            )

            # Set DynamoDB keys
            event.set_dynamodb_keys()

            # Store in DynamoDB
            self.db_helper.table.put_item(Item=event.model_dump())

            # Log to CloudWatch
            logger.warning(
                "security_event",
                event_type=event_type,
                api_key_prefix=api_key_prefix,
                severity=severity.value,
                details=details,
            )

            # Trigger CloudWatch alarm for critical events
            if severity == Severity.CRITICAL:
                await self._trigger_cloudwatch_alarm(event)

        except Exception as e:
            logger.error(
                "security_event_logging_failed",
                event_type=event_type,
                api_key_prefix=api_key_prefix,
                error=str(e),
            )

    async def _detect_and_log_anomalies(
        self, api_key: str, api_key_prefix: str
    ) -> None:
        """Detect unusual patterns and log anomalies.
        
        Args:
            api_key: Full API key string
            api_key_prefix: First 8 characters (masked)
        """
        try:
            # Check request rate in last minute
            current_time = int(time.time())
            one_minute_ago = current_time - 60

            # Count requests in last minute from rate limit counters
            request_count = await self._count_recent_requests(
                api_key=api_key,
                start_time=one_minute_ago,
                end_time=current_time,
            )

            # Check if threshold exceeded
            if request_count > self.anomaly_threshold:
                await self.log_security_event(
                    event_type="anomaly",
                    api_key_prefix=api_key_prefix,
                    severity=Severity.CRITICAL,
                    details={
                        "anomaly_type": "high_request_rate",
                        "request_count": request_count,
                        "threshold": self.anomaly_threshold,
                        "time_window_seconds": 60,
                        "message": f"Detected {request_count} requests in last minute (threshold: {self.anomaly_threshold})",
                    },
                )

        except Exception as e:
            logger.error(
                "anomaly_detection_failed",
                api_key_prefix=api_key_prefix,
                error=str(e),
            )

    async def _count_recent_requests(
        self, api_key: str, start_time: int, end_time: int
    ) -> int:
        """Count requests from API key in time window.
        
        Args:
            api_key: API key string
            start_time: Start of time window (Unix timestamp)
            end_time: End of time window (Unix timestamp)
            
        Returns:
            Total request count in time window
        """
        try:
            total_count = 0

            # Query rate limit counters for each second in the window
            for timestamp in range(start_time, end_time + 1):
                counter_data = self.db_helper.table.get_item(
                    Key={
                        "PK": f"RATELIMIT#{api_key}#{timestamp}",
                        "SK": "COUNTER",
                    }
                ).get("Item")

                if counter_data:
                    total_count += counter_data.get("request_count", 0)

            return total_count

        except Exception as e:
            logger.error("count_recent_requests_failed", error=str(e))
            return 0

    async def _trigger_cloudwatch_alarm(self, event: SecurityEvent) -> None:
        """Trigger CloudWatch alarm for critical security events.
        
        Args:
            event: Security event that triggered the alarm
        """
        try:
            # Log critical event with special marker for CloudWatch metric filter
            logger.critical(
                "CRITICAL_SECURITY_EVENT",
                event_id=event.event_id,
                event_type=event.event_type,
                api_key_prefix=event.api_key_prefix,
                severity=event.severity.value,
                details=event.details,
            )

            # TODO: In production, publish custom CloudWatch metric
            # import boto3
            # cloudwatch = boto3.client('cloudwatch')
            # cloudwatch.put_metric_data(
            #     Namespace='VibeJudge/Security',
            #     MetricData=[{
            #         'MetricName': 'CriticalSecurityEvents',
            #         'Value': 1,
            #         'Unit': 'Count',
            #         'Timestamp': event.timestamp,
            #         'Dimensions': [
            #             {'Name': 'EventType', 'Value': event.event_type},
            #             {'Name': 'Severity', 'Value': event.severity.value},
            #         ]
            #     }]
            # )

        except Exception as e:
            logger.error("cloudwatch_alarm_trigger_failed", error=str(e))
