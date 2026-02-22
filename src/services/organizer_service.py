"""Organizer service — Account management and API key generation."""

import hashlib
import secrets
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

    def _generate_api_key(self) -> str:
        """Generate a secure API key.

        Returns:
            API key string (32 bytes hex = 64 characters)
        """
        return secrets.token_hex(32)

    def _hash_api_key(self, api_key: str) -> str:
        """Hash API key for storage.

        Args:
            api_key: Plain text API key

        Returns:
            SHA-256 hash of API key
        """
        return hashlib.sha256(api_key.encode()).hexdigest()

    def create_organizer(self, data: OrganizerCreate) -> OrganizerCreateResponse:
        """Create new organizer account.

        Args:
            data: Organizer creation data

        Returns:
            Organizer response with API key

        Raises:
            ValueError: If email already exists
        """
        # Check if email already exists
        existing = self.db.get_organizer_by_email(data.email)
        if existing:
            logger.warning("organizer_email_exists", email=data.email)
            raise ValueError(f"Email {data.email} is already registered")

        # Generate IDs and API key
        org_id = generate_org_id()
        api_key = self._generate_api_key()
        api_key_hash = self._hash_api_key(api_key)

        now = datetime.now(UTC)

        # Create DynamoDB record
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
            api_key_hash=api_key_hash,
            GSI1PK=f"EMAIL#{data.email}",
            GSI1SK=f"ORG#{org_id}",
            created_at=now,
            updated_at=now,
        )

        # Save to DynamoDB
        success = self.db.put_organizer(record.model_dump())
        if not success:
            logger.error("organizer_creation_failed", org_id=org_id)
            raise RuntimeError("Failed to create organizer")

        logger.info(
            "organizer_created",
            org_id=org_id,
            email=data.email,
            tier=Tier.FREE,
        )

        # Return response with API key (only time it's shown)
        return OrganizerCreateResponse(
            org_id=org_id,
            email=data.email,
            name=data.name,
            organization=data.organization,
            tier=Tier.FREE,
            hackathon_count=0,
            api_key=api_key,
            created_at=now,
            updated_at=now,
        )

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

    def verify_api_key(self, api_key: str) -> str | None:
        """Verify API key and return organizer ID.

        Args:
            api_key: Plain text API key

        Returns:
            Organizer ID if valid, None otherwise

        Note:
            For MVP, scans all organizers and filters in Python (acceptable for small datasets).
            In production, add GSI3 with api_key_hash as PK for O(1) lookup.
            Uses secrets.compare_digest() for constant-time comparison to prevent timing attacks.
        """
        api_key_hash = self._hash_api_key(api_key)

        # Scan all organizers and filter in Python (DynamoDB Local has issues with FilterExpression)
        try:
            response = self.db.table.scan(
                FilterExpression="entity_type = :type",
                ExpressionAttributeValues={":type": "ORGANIZER"},
            )

            items = response.get("Items", [])
            for item in items:
                stored_hash = item.get("api_key_hash", "")
                # Use constant-time comparison to prevent timing attacks
                # Add length check to prevent length-based timing leaks
                if len(api_key_hash) == len(stored_hash) and secrets.compare_digest(
                    api_key_hash, stored_hash
                ):
                    org_id = item.get("org_id")
                    logger.info("api_key_verified", org_id=org_id)
                    return org_id

            logger.warning("api_key_invalid", api_key_hash_prefix=api_key_hash[:16])
            return None

        except Exception as e:
            logger.error("api_key_verification_failed", error=str(e))
            return None

    def regenerate_api_key(self, org_id: str) -> OrganizerLoginResponse:
        """Regenerate API key for organizer (login).

        Args:
            org_id: Organizer ID

        Returns:
            Login response with new API key

        Raises:
            ValueError: If organizer not found
        """
        # Get existing organizer
        record = self.db.get_organizer(org_id)
        if not record:
            raise ValueError(f"Organizer {org_id} not found")

        # Generate new API key
        api_key = self._generate_api_key()
        api_key_hash = self._hash_api_key(api_key)

        # Update record
        record["api_key_hash"] = api_key_hash
        record["updated_at"] = datetime.now(UTC)

        success = self.db.put_organizer(record)
        if not success:
            logger.error("api_key_regeneration_failed", org_id=org_id)
            raise RuntimeError("Failed to regenerate API key")

        logger.info("api_key_regenerated", org_id=org_id)

        return OrganizerLoginResponse(
            org_id=org_id,
            api_key=api_key,
        )

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
