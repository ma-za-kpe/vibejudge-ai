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
            "agents_enabled": [a.value if hasattr(a, 'value') else a for a in data.agents_enabled],
            "ai_policy_mode": data.ai_policy_mode.value if hasattr(data.ai_policy_mode, 'value') else data.ai_policy_mode,
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
            name=record["name"],
            description=record.get("description", ""),
            status=HackathonStatus(record.get("status", "draft")),
            start_date=datetime.fromisoformat(record["start_date"]) if record.get("start_date") else None,
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
            record["agents_enabled"] = [a.value if hasattr(a, 'value') else a for a in data.agents_enabled]
        if data.ai_policy_mode is not None:
            record["ai_policy_mode"] = data.ai_policy_mode.value if hasattr(data.ai_policy_mode, 'value') else data.ai_policy_mode
        if data.budget_limit_usd is not None:
            record["budget_limit_usd"] = data.budget_limit_usd

        record["updated_at"] = datetime.now(UTC).isoformat()

        success = self.db.put_hackathon_detail(record)
        if not success:
            logger.error("hackathon_update_failed", hack_id=hack_id)
            raise RuntimeError("Failed to update hackathon")

        logger.info("hackathon_updated", hack_id=hack_id)

        return self.get_hackathon(hack_id)

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
