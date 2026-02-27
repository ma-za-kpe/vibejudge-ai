"""API key service for lifecycle management."""

import base64
import secrets
from datetime import datetime, timedelta

from src.models.api_key import (
    APIKey,
    APIKeyCreateResponse,
    APIKeyListResponse,
    APIKeyResponse,
    Tier,
    get_tier_defaults,
)
from src.utils.dynamo import DynamoDBHelper
from src.utils.id_gen import generate_id
from src.utils.logging import get_logger

logger = get_logger(__name__)

# Grace period for deprecated keys (7 days)
GRACE_PERIOD_DAYS = 7


class APIKeyService:
    """Service for managing API key lifecycle."""

    def __init__(self, db_helper: DynamoDBHelper, environment: str = "live") -> None:
        """Initialize API key service.

        Args:
            db_helper: DynamoDB helper instance
            environment: Environment for key generation ("live" or "test")
        """
        self.db = db_helper
        self.environment = environment

    def create_api_key(
        self,
        organizer_id: str,
        hackathon_id: str | None = None,
        tier: Tier = Tier.FREE,
        expires_at: datetime | None = None,
        rate_limit: int | None = None,
        daily_quota: int | None = None,
        budget_limit_usd: float | None = None,
    ) -> APIKeyCreateResponse:
        """Create a new API key with secure generation.

        Args:
            organizer_id: Owner organizer ID
            hackathon_id: Optional hackathon scope
            tier: API key tier (determines default limits)
            expires_at: Optional expiration timestamp
            rate_limit: Custom rate limit (uses tier default if None)
            daily_quota: Custom daily quota (uses tier default if None)
            budget_limit_usd: Custom budget limit (uses tier default if None)

        Returns:
            APIKeyCreateResponse with secret key (shown only once)
        """
        # Generate secure API key
        api_key_string = self._generate_secure_key()

        # Get tier defaults
        tier_defaults = get_tier_defaults(tier)

        # Use custom limits or tier defaults
        final_rate_limit = rate_limit if rate_limit is not None else tier_defaults["rate_limit_per_second"]
        final_daily_quota = daily_quota if daily_quota is not None else tier_defaults["daily_quota"]
        final_budget_limit = (
            budget_limit_usd if budget_limit_usd is not None else tier_defaults["budget_limit_usd"]
        )

        # Create API key object
        api_key_id = generate_id()
        now = datetime.utcnow()

        api_key = APIKey(
            api_key_id=api_key_id,
            api_key=api_key_string,
            organizer_id=organizer_id,
            hackathon_id=hackathon_id,
            tier=tier,
            rate_limit_per_second=final_rate_limit,
            daily_quota=final_daily_quota,
            budget_limit_usd=final_budget_limit,
            active=True,
            created_at=now,
            updated_at=now,
            expires_at=expires_at,
            deprecated=False,
            total_requests=0,
            total_cost_usd=0.0,
        )

        # Set DynamoDB keys
        api_key.set_dynamodb_keys()

        # Store in DynamoDB
        api_key_dict = api_key.model_dump()
        serialized = self.db._serialize_item(api_key_dict)

        try:
            self.db.table.put_item(Item=serialized)
        except Exception as e:
            logger.error("api_key_creation_failed", api_key_id=api_key_id, error=str(e))
            raise RuntimeError(f"Failed to create API key in database: {e}")

        logger.info(
            "api_key_created",
            api_key_id=api_key_id,
            organizer_id=organizer_id,
            tier=tier.value,
            hackathon_id=hackathon_id,
        )

        return api_key.to_create_response()

    def validate_api_key(self, api_key: str) -> APIKey | None:
        """Validate API key and check expiration.

        Args:
            api_key: API key string to validate

        Returns:
            APIKey object if valid, None if invalid/expired/inactive

        Note:
            Currently uses table scan which is not optimal for production.
            TODO: Add GSI on api_key field for efficient lookup.
        """
        try:
            response = self.db.table.scan(
                FilterExpression="api_key = :key",
                ExpressionAttributeValues={":key": api_key},
            )
            items = response.get("Items", [])

            if not items:
                logger.warning("api_key_not_found", api_key_prefix=api_key[:8])
                return None

            # Convert to APIKey model
            api_key_data = items[0]
            api_key_obj = APIKey(**api_key_data)

            # Check if valid
            if not api_key_obj.is_valid():
                logger.warning(
                    "api_key_invalid",
                    api_key_id=api_key_obj.api_key_id,
                    active=api_key_obj.active,
                    expired=api_key_obj.is_expired(),
                )
                return None

            logger.info("api_key_validated", api_key_id=api_key_obj.api_key_id)
            return api_key_obj

        except Exception as e:
            logger.error("api_key_validation_error", error=str(e))
            return None

    def rotate_api_key(self, api_key_id: str) -> tuple[APIKey, APIKey]:
        """Rotate API key with grace period.

        Creates a new key and marks the old one as deprecated.
        The old key remains valid for GRACE_PERIOD_DAYS.

        Args:
            api_key_id: ID of the API key to rotate

        Returns:
            Tuple of (new_key, old_key)

        Raises:
            ValueError: If API key not found
        """
        # Get existing key
        old_key_data = self.db.table.get_item(
            Key={"PK": f"APIKEY#{api_key_id}", "SK": "METADATA"}
        ).get("Item")

        if not old_key_data:
            raise ValueError(f"API key not found: {api_key_id}")

        old_key = APIKey(**old_key_data)

        # Create new key with same settings
        new_key_response = self.create_api_key(
            organizer_id=old_key.organizer_id,
            hackathon_id=old_key.hackathon_id,
            tier=old_key.tier,
            expires_at=old_key.expires_at,
            rate_limit=old_key.rate_limit_per_second,
            daily_quota=old_key.daily_quota,
            budget_limit_usd=old_key.budget_limit_usd,
        )

        # Mark old key as deprecated
        now = datetime.utcnow()
        grace_period_end = now + timedelta(days=GRACE_PERIOD_DAYS)

        old_key.deprecated = True
        old_key.deprecated_at = now
        old_key.expires_at = grace_period_end  # Override expiration with grace period
        old_key.updated_at = now

        # Update old key in database
        self.db.table.update_item(
            Key={"PK": f"APIKEY#{api_key_id}", "SK": "METADATA"},
            UpdateExpression="SET deprecated = :deprecated, deprecated_at = :deprecated_at, "
            "expires_at = :expires_at, updated_at = :updated_at",
            ExpressionAttributeValues={
                ":deprecated": True,
                ":deprecated_at": now.isoformat(),
                ":expires_at": grace_period_end.isoformat(),
                ":updated_at": now.isoformat(),
            },
        )

        logger.info(
            "api_key_rotated",
            old_key_id=api_key_id,
            new_key_id=new_key_response.api_key_id,
            grace_period_days=GRACE_PERIOD_DAYS,
        )

        # Convert new_key_response to APIKey for return
        new_key = APIKey(
            api_key_id=new_key_response.api_key_id,
            api_key=new_key_response.api_key,
            organizer_id=new_key_response.organizer_id,
            hackathon_id=new_key_response.hackathon_id,
            tier=new_key_response.tier,
            rate_limit_per_second=new_key_response.rate_limit_per_second,
            daily_quota=new_key_response.daily_quota,
            budget_limit_usd=new_key_response.budget_limit_usd,
            active=new_key_response.active,
            created_at=new_key_response.created_at,
            updated_at=new_key_response.updated_at,
            expires_at=new_key_response.expires_at,
            deprecated=new_key_response.deprecated,
            deprecated_at=new_key_response.deprecated_at,
            total_requests=new_key_response.total_requests,
            total_cost_usd=new_key_response.total_cost_usd,
            last_used_at=new_key_response.last_used_at,
        )

        return (new_key, old_key)

    def revoke_api_key(self, api_key_id: str) -> bool:
        """Revoke API key (soft delete).

        Sets active=false without deleting the record.

        Args:
            api_key_id: ID of the API key to revoke

        Returns:
            True if successful, False otherwise
        """
        try:
            now = datetime.utcnow()

            self.db.table.update_item(
                Key={"PK": f"APIKEY#{api_key_id}", "SK": "METADATA"},
                UpdateExpression="SET active = :active, updated_at = :updated_at",
                ExpressionAttributeValues={
                    ":active": False,
                    ":updated_at": now.isoformat(),
                },
            )

            logger.info("api_key_revoked", api_key_id=api_key_id)
            return True

        except Exception as e:
            logger.error("api_key_revocation_failed", api_key_id=api_key_id, error=str(e))
            return False

    def list_api_keys(self, organizer_id: str) -> APIKeyListResponse:
        """List all API keys for an organizer.

        Args:
            organizer_id: Organizer ID

        Returns:
            APIKeyListResponse with list of keys (excludes secret keys)
        """
        try:
            # Query using GSI1 (ORG#{organizer_id})
            response = self.db.table.query(
                IndexName="GSI1",
                KeyConditionExpression="GSI1PK = :pk",
                ExpressionAttributeValues={":pk": f"ORG#{organizer_id}"},
            )

            items = response.get("Items", [])

            # Convert to APIKey objects and then to response models
            api_keys = []
            for item in items:
                try:
                    api_key = APIKey(**item)
                    api_keys.append(api_key.to_response())
                except Exception as e:
                    logger.warning("api_key_conversion_failed", item=item, error=str(e))
                    continue

            logger.info("api_keys_listed", organizer_id=organizer_id, count=len(api_keys))

            return APIKeyListResponse(api_keys=api_keys, total=len(api_keys))

        except Exception as e:
            logger.error("list_api_keys_failed", organizer_id=organizer_id, error=str(e))
            return APIKeyListResponse(api_keys=[], total=0)

    def get_api_key_by_id(self, api_key_id: str) -> APIKeyResponse | None:
        """Get API key by ID (excludes secret key).

        Args:
            api_key_id: API key ID

        Returns:
            APIKeyResponse if found, None otherwise
        """
        try:
            response = self.db.table.get_item(
                Key={"PK": f"APIKEY#{api_key_id}", "SK": "METADATA"}
            )

            item = response.get("Item")
            if not item:
                logger.warning("api_key_not_found_by_id", api_key_id=api_key_id)
                return None

            api_key = APIKey(**item)
            return api_key.to_response()

        except Exception as e:
            logger.error("get_api_key_by_id_failed", api_key_id=api_key_id, error=str(e))
            return None

    def _generate_secure_key(self) -> str:
        """Generate cryptographically secure API key.

        Uses secrets.token_bytes(24) for 256-bit entropy.
        Format: vj_{environment}_{32-char-base64}

        Returns:
            Secure API key string matching format vj_(live|test)_[A-Za-z0-9+/]{32}
        """
        # Generate 24 random bytes (192 bits of entropy)
        # Base64 encoding will produce 32 characters
        random_bytes = secrets.token_bytes(24)

        # Standard base64 encoding (not URL-safe) to match the regex pattern
        # The pattern expects [A-Za-z0-9+/] not [A-Za-z0-9-_]
        base64_key = base64.b64encode(random_bytes).decode("utf-8")

        # Remove padding characters (=) to get exactly 32 chars
        base64_key = base64_key.rstrip("=")

        # Construct key with format: vj_{env}_{base64}
        api_key = f"vj_{self.environment}_{base64_key}"

        return api_key


# ============================================================
# HELPER FUNCTIONS
# ============================================================


def get_default_limits_for_tier(tier: Tier) -> dict[str, int | float]:
    """Get default rate limit, quota, and budget for a tier.

    Args:
        tier: API key tier

    Returns:
        Dictionary with rate_limit_per_second, daily_quota, budget_limit_usd
    """
    return get_tier_defaults(tier)
