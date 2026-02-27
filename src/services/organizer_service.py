"""Organizer service — Account management with Advanced API key integration."""

from datetime import UTC, datetime

from src.models.common import Tier
from src.models.organizer import (
    OrganizerCreate,
    OrganizerCreateResponse,
    OrganizerLoginResponse,
    OrganizerRecord,
    OrganizerResponse,
)
from src.utils.dynamo import DynamoDBHelper
from src.utils.id_gen import generate_org_id
from src.utils.logging import get_logger

logger = get_logger(__name__)


class OrganizerService:
    """Service for organizer account operations."""

    def __init__(self, db: DynamoDBHelper):
        """Initialize organizer service.

        Args:
            db: DynamoDB helper instance
        """
        self.db = db

    def create_organizer(self, data: OrganizerCreate) -> OrganizerCreateResponse:
        """Create new organizer account with Advanced API key.

        Args:
            data: Organizer creation data

        Returns:
            Organizer response with Advanced API key

        Raises:
            ValueError: If email already exists
        """
        # Check if email already exists
        existing = self.db.get_organizer_by_email(data.email)
        if existing:
            logger.warning("organizer_email_exists", email=data.email)
            raise ValueError(f"Email {data.email} is already registered")

        # Generate organizer ID
        org_id = generate_org_id()
        now = datetime.now(UTC)

        # Create DynamoDB record (NO api_key_hash field)
        record = OrganizerRecord(
            PK=f"ORG#{org_id}",
            SK="PROFILE",
            entity_type="ORGANIZER",
            org_id=org_id,
            email=data.email,
            name=data.name,
            organization=data.organization,
            tier=Tier.FREE,
            hackathon_count=0,
            GSI1PK=f"EMAIL#{data.email}",
            GSI1SK=f"ORG#{org_id}",
            created_at=now,
            updated_at=now,
        )

        # Save organizer to DynamoDB
        success = self.db.put_organizer(record.model_dump())
        if not success:
            logger.error("organizer_creation_failed", org_id=org_id)
            raise RuntimeError("Failed to create organizer")

        # Create Advanced API key
        from src.services.api_key_service import APIKeyService

        api_key_service = APIKeyService(self.db, environment="live")

        try:
            api_key_response = api_key_service.create_api_key(
                organizer_id=org_id,
                tier=Tier.FREE,
                expires_at=None,  # Never expires for MVP
            )

            logger.info(
                "organizer_created_with_advanced_key",
                org_id=org_id,
                email=data.email,
                tier=Tier.FREE,
                api_key_id=api_key_response.api_key_id,
            )

            # Return response with Advanced API key (vj_live_xxx format)
            return OrganizerCreateResponse(
                org_id=org_id,
                email=data.email,
                name=data.name,
                organization=data.organization,
                tier=Tier.FREE,
                hackathon_count=0,
                api_key=api_key_response.api_key,  # Advanced key format
                created_at=now,
                updated_at=now,
            )

        except Exception as e:
            # Rollback: Delete organizer if API key creation fails
            self.db.table.delete_item(Key={"PK": f"ORG#{org_id}", "SK": "PROFILE"})
            logger.error("api_key_creation_failed_rollback", org_id=org_id, error=str(e))
            raise RuntimeError(f"Failed to create API key: {e}")

    def get_organizer(self, org_id: str) -> OrganizerResponse | None:
        """Get organizer by ID.

        Args:
            org_id: Organizer ID

        Returns:
            Organizer response or None if not found
        """
        record = self.db.get_organizer(org_id)
        if not record:
            return None

        return OrganizerResponse(
            org_id=record["org_id"],
            email=record["email"],
            name=record["name"],
            organization=record.get("organization"),
            tier=Tier(record.get("tier", "free")),
            hackathon_count=record.get("hackathon_count", 0),
            created_at=record["created_at"],
            updated_at=record["updated_at"],
        )

    def get_organizer_by_email(self, email: str) -> OrganizerResponse | None:
        """Get organizer by email.

        Args:
            email: Organizer email

        Returns:
            Organizer response or None if not found
        """
        record = self.db.get_organizer_by_email(email)
        if not record:
            return None

        return OrganizerResponse(
            org_id=record["org_id"],
            email=record["email"],
            name=record["name"],
            organization=record.get("organization"),
            tier=Tier(record.get("tier", "free")),
            hackathon_count=record.get("hackathon_count", 0),
            created_at=record["created_at"],
            updated_at=record["updated_at"],
        )

    def regenerate_api_key(self, org_id: str) -> OrganizerLoginResponse:
        """Regenerate API key for organizer (login) using Advanced system.

        Deactivates all existing Advanced API keys and creates a new one.

        Args:
            org_id: Organizer ID

        Returns:
            Login response with new Advanced API key

        Raises:
            ValueError: If organizer not found
        """
        # Get existing organizer
        record = self.db.get_organizer(org_id)
        if not record:
            raise ValueError(f"Organizer {org_id} not found")

        # Deactivate all existing API keys for this organizer
        from src.services.api_key_service import APIKeyService

        api_key_service = APIKeyService(self.db, environment="live")

        try:
            # Get all existing keys
            existing_keys = api_key_service.list_api_keys(org_id)

            # Revoke all active keys
            for key in existing_keys.api_keys:
                if key.active:
                    api_key_service.revoke_api_key(key.api_key_id)
                    logger.info("api_key_revoked_on_login", api_key_id=key.api_key_id)

            # Create new Advanced API key
            api_key_response = api_key_service.create_api_key(
                organizer_id=org_id,
                tier=Tier(record.get("tier", "free")),
                expires_at=None,  # Never expires for MVP
            )

            logger.info(
                "api_key_regenerated",
                org_id=org_id,
                new_api_key_id=api_key_response.api_key_id,
            )

            return OrganizerLoginResponse(
                org_id=org_id,
                api_key=api_key_response.api_key,  # Advanced key format
            )

        except Exception as e:
            logger.error("api_key_regeneration_failed", org_id=org_id, error=str(e))
            raise RuntimeError(f"Failed to regenerate API key: {e}")

    def increment_hackathon_count(self, org_id: str) -> bool:
        """Increment hackathon count for organizer.

        Args:
            org_id: Organizer ID

        Returns:
            True if successful
        """
        record = self.db.get_organizer(org_id)
        if not record:
            return False

        record["hackathon_count"] = record.get("hackathon_count", 0) + 1
        record["updated_at"] = datetime.now(UTC)

        return self.db.put_organizer(record)

    def update_organizer(
        self,
        org_id: str,
        name: str | None = None,
        organization: str | None = None,
    ) -> OrganizerResponse:
        """Update organizer profile.

        Args:
            org_id: Organizer ID
            name: New name (optional)
            organization: New organization (optional)

        Returns:
            Updated organizer response

        Raises:
            ValueError: If organizer not found or no fields to update
        """
        # Get existing organizer
        record = self.db.get_organizer(org_id)
        if not record:
            raise ValueError(f"Organizer {org_id} not found")

        # Check if any fields to update
        if name is None and organization is None:
            raise ValueError("At least one field must be provided for update")

        # Update fields
        if name is not None:
            record["name"] = name
        if organization is not None:
            record["organization"] = organization

        record["updated_at"] = datetime.now(UTC)

        # Save to DynamoDB
        success = self.db.put_organizer(record)
        if not success:
            logger.error("organizer_update_failed", org_id=org_id)
            raise RuntimeError("Failed to update organizer")

        logger.info(
            "organizer_updated",
            org_id=org_id,
            name=name,
            organization=organization,
        )

        return OrganizerResponse(
            org_id=record["org_id"],
            email=record["email"],
            name=record["name"],
            organization=record.get("organization"),
            tier=Tier(record.get("tier", "free")),
            hackathon_count=record.get("hackathon_count", 0),
            created_at=record["created_at"],
            updated_at=record["updated_at"],
        )
