"""Hackathon service — CRUD operations and validation."""

from datetime import UTC, datetime

from src.models.common import HackathonStatus
from src.models.hackathon import (
    HackathonCreate,
    HackathonListItem,
    HackathonListResponse,
    HackathonResponse,
    HackathonUpdate,
)
from src.utils.dynamo import DynamoDBHelper
from src.utils.id_gen import generate_hack_id
from src.utils.logging import get_logger

logger = get_logger(__name__)


class HackathonService:
    """Service for hackathon operations."""

    def __init__(self, db: DynamoDBHelper):
        """Initialize hackathon service.

        Args:
            db: DynamoDB helper instance
        """
        self.db = db

    def create_hackathon(
        self,
        org_id: str,
        data: HackathonCreate,
    ) -> HackathonResponse:
        """Create new hackathon.

        Args:
            org_id: Organizer ID
            data: Hackathon creation data

        Returns:
            Hackathon response
        """
        hack_id = generate_hack_id()
        now = datetime.now(UTC)

        # Create organizer's hackathon list item (PK=ORG#, SK=HACK#)
        org_hack_record = {
            "PK": f"ORG#{org_id}",
            "SK": f"HACK#{hack_id}",
            "entity_type": "HACKATHON_REF",
            "hack_id": hack_id,
            "name": data.name,
            "status": HackathonStatus.DRAFT.value,
            "submission_count": 0,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }

        # Create hackathon detail record (PK=HACK#, SK=META)
        hack_detail_record = {
            "PK": f"HACK#{hack_id}",
            "SK": "META",
            "entity_type": "HACKATHON",
            "hack_id": hack_id,
            "org_id": org_id,
            "name": data.name,
            "description": data.description,
            "status": HackathonStatus.DRAFT.value,
            "start_date": data.start_date.isoformat() if data.start_date else None,
            "end_date": data.end_date.isoformat() if data.end_date else None,
            "rubric": data.rubric.model_dump(),
            "agents_enabled": [a.value if hasattr(a, "value") else a for a in data.agents_enabled],
            "ai_policy_mode": data.ai_policy_mode.value
            if hasattr(data.ai_policy_mode, "value")
            else data.ai_policy_mode,
            "ai_policy_config": data.ai_policy_config,
            "budget_limit_usd": data.budget_limit_usd,
            "submission_count": 0,
            "GSI1PK": f"HACK#{hack_id}",
            "GSI1SK": "META",
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }

        # Save both records
        success1 = self.db.put_hackathon(org_hack_record)
        success2 = self.db.put_hackathon_detail(hack_detail_record)

        if not (success1 and success2):
            logger.error("hackathon_creation_failed", hack_id=hack_id)
            raise RuntimeError("Failed to create hackathon")

        logger.info(
            "hackathon_created",
            hack_id=hack_id,
            org_id=org_id,
            name=data.name,
        )

        return HackathonResponse(
            hack_id=hack_id,
            org_id=org_id,
            name=data.name,
            description=data.description,
            status=HackathonStatus.DRAFT,
            start_date=data.start_date,
            end_date=data.end_date,
            rubric=data.rubric,
            agents_enabled=data.agents_enabled,
            ai_policy_mode=data.ai_policy_mode,
            submission_count=0,
            budget_limit_usd=data.budget_limit_usd,
            created_at=now,
            updated_at=now,
        )

    def get_hackathon(self, hack_id: str) -> HackathonResponse | None:
        """Get hackathon by ID.

        Args:
            hack_id: Hackathon ID

        Returns:
            Hackathon response or None if not found
        """
        record = self.db.get_hackathon(hack_id)
        if not record:
            return None

        from src.models.common import AgentName, AIPolicyMode
        from src.models.hackathon import RubricConfig

        return HackathonResponse(
            hack_id=record["hack_id"],
            org_id=record["org_id"],
            name=record["name"],
            description=record.get("description", ""),
            status=HackathonStatus(record.get("status", "draft")),
            start_date=datetime.fromisoformat(record["start_date"])
            if record.get("start_date")
            else None,
            end_date=datetime.fromisoformat(record["end_date"]) if record.get("end_date") else None,
            rubric=RubricConfig(**record["rubric"]),
            agents_enabled=[AgentName(a) for a in record["agents_enabled"]],
            ai_policy_mode=AIPolicyMode(record.get("ai_policy_mode", "ai_assisted")),
            submission_count=record.get("submission_count", 0),
            budget_limit_usd=record.get("budget_limit_usd"),
            created_at=datetime.fromisoformat(record["created_at"]),
            updated_at=datetime.fromisoformat(record["updated_at"]),
        )

    def list_hackathons(self, org_id: str) -> HackathonListResponse:
        """List hackathons for organizer.

        Args:
            org_id: Organizer ID

        Returns:
            List of hackathons
        """
        records = self.db.list_organizer_hackathons(org_id)

        items = [
            HackathonListItem(
                hack_id=r["hack_id"],
                name=r["name"],
                status=HackathonStatus(r.get("status", "draft")),
                submission_count=r.get("submission_count", 0),
                created_at=datetime.fromisoformat(r["created_at"]),
            )
            for r in records
        ]

        return HackathonListResponse(
            hackathons=items,
            next_cursor=None,
            has_more=False,
        )

    def update_hackathon(
        self,
        hack_id: str,
        data: HackathonUpdate,
    ) -> HackathonResponse:
        """Update hackathon.

        Args:
            hack_id: Hackathon ID
            data: Update data

        Returns:
            Updated hackathon response

        Raises:
            ValueError: If hackathon not found
        """
        record = self.db.get_hackathon(hack_id)
        if not record:
            raise ValueError(f"Hackathon {hack_id} not found")

        # Update fields
        if data.name is not None:
            record["name"] = data.name
        if data.description is not None:
            record["description"] = data.description
        if data.start_date is not None:
            record["start_date"] = data.start_date.isoformat()
        if data.end_date is not None:
            record["end_date"] = data.end_date.isoformat()
        if data.rubric is not None:
            record["rubric"] = data.rubric.model_dump()
        if data.agents_enabled is not None:
            record["agents_enabled"] = [
                a.value if hasattr(a, "value") else a for a in data.agents_enabled
            ]
        if data.ai_policy_mode is not None:
            record["ai_policy_mode"] = (
                data.ai_policy_mode.value
                if hasattr(data.ai_policy_mode, "value")
                else data.ai_policy_mode
            )
        if data.budget_limit_usd is not None:
            record["budget_limit_usd"] = data.budget_limit_usd

        record["updated_at"] = datetime.now(UTC).isoformat()

        success = self.db.put_hackathon_detail(record)
        if not success:
            logger.error("hackathon_update_failed", hack_id=hack_id)
            raise RuntimeError("Failed to update hackathon")

        logger.info("hackathon_updated", hack_id=hack_id)

        updated_hackathon = self.get_hackathon(hack_id)
        if updated_hackathon is None:
            raise RuntimeError(f"Failed to retrieve updated hackathon {hack_id}")
        return updated_hackathon

    def delete_hackathon(self, hack_id: str, org_id: str) -> bool:
        """Delete hackathon (soft delete by status).

        Args:
            hack_id: Hackathon ID
            org_id: Organizer ID

        Returns:
            True if successful
        """
        record = self.db.get_hackathon(hack_id)
        if not record:
            return False

        # Soft delete by setting status
        record["status"] = HackathonStatus.ARCHIVED.value
        record["updated_at"] = datetime.now(UTC).isoformat()

        success = self.db.put_hackathon_detail(record)
        if success:
            logger.info("hackathon_deleted", hack_id=hack_id)

        return success

    def activate_hackathon(self, hack_id: str, org_id: str) -> HackathonResponse:
        """Activate hackathon (transition from DRAFT to CONFIGURED).

        Args:
            hack_id: Hackathon ID
            org_id: Organizer ID

        Returns:
            Updated hackathon response

        Raises:
            ValueError: If hackathon not found or invalid state transition
        """
        record = self.db.get_hackathon(hack_id)
        if not record:
            raise ValueError(f"Hackathon {hack_id} not found")

        # Verify ownership
        if record.get("org_id") != org_id:
            raise ValueError("You do not have permission to activate this hackathon")

        # Check current status
        current_status = record.get("status", "draft")
        if current_status != HackathonStatus.DRAFT.value:
            raise ValueError(
                f"Cannot activate hackathon in {current_status} status. Only DRAFT hackathons can be activated."
            )

        # Update status to CONFIGURED
        record["status"] = HackathonStatus.CONFIGURED.value
        record["updated_at"] = datetime.now(UTC).isoformat()

        # Update both records (detail and organizer list)
        success1 = self.db.put_hackathon_detail(record)

        # Update organizer's hackathon list item
        org_hack_record = self.db.table.get_item(
            Key={"PK": f"ORG#{org_id}", "SK": f"HACK#{hack_id}"}
        ).get("Item")

        if org_hack_record:
            org_hack_record["status"] = HackathonStatus.CONFIGURED.value
            org_hack_record["updated_at"] = datetime.now(UTC).isoformat()
            self.db.put_hackathon(org_hack_record)

        if not success1:
            logger.error("hackathon_activation_failed", hack_id=hack_id)
            raise RuntimeError("Failed to activate hackathon")

        logger.info("hackathon_activated", hack_id=hack_id, org_id=org_id)

        updated_hackathon = self.get_hackathon(hack_id)
        if updated_hackathon is None:
            raise RuntimeError(f"Failed to retrieve activated hackathon {hack_id}")
        return updated_hackathon

    def increment_submission_count(self, hack_id: str) -> bool:
        """Increment submission count for hackathon.

        Args:
            hack_id: Hackathon ID

        Returns:
            True if successful
        """
        record = self.db.get_hackathon(hack_id)
        if not record:
            return False

        record["submission_count"] = record.get("submission_count", 0) + 1
        record["updated_at"] = datetime.now(UTC).isoformat()

        return self.db.put_hackathon_detail(record)

    def list_all_configured_hackathons(self) -> list[HackathonResponse]:
        """List all CONFIGURED hackathons across all organizers (for public endpoint).

        Returns:
            List of configured hackathons
        """
        # Use scan instead of GSI query since we need all hackathons across all organizers
        # GSI1 is organized by organizer (GSI1PK = ORG#xxx), not suitable for cross-org queries
        try:
            response = self.db.table.scan(
                FilterExpression="SK = :meta AND #status = :configured",
                ExpressionAttributeNames={"#status": "status"},
                ExpressionAttributeValues={
                    ":meta": "META",
                    ":configured": HackathonStatus.CONFIGURED.value,
                },
            )

            records = response.get("Items", [])

            # Convert to HackathonResponse objects
            configured_hackathons = []
            for record in records:
                hackathon = self.get_hackathon(record["hack_id"])
                if hackathon:
                    configured_hackathons.append(hackathon)

            logger.info(
                "public_hackathons_listed",
                configured_count=len(configured_hackathons),
            )

            return configured_hackathons

        except Exception as e:
            logger.error("list_all_configured_hackathons_failed", error=str(e))
            return []
