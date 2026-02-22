"""Organizer account models."""

from pydantic import EmailStr, Field

from src.models.common import Tier, TimestampMixin, VibeJudgeBase

# --- Request Models ---


class OrganizerCreate(VibeJudgeBase):
    """POST /api/v1/organizers"""

    email: EmailStr
    name: str = Field(..., min_length=1, max_length=100)
    organization: str | None = Field(None, max_length=200)


class OrganizerLogin(VibeJudgeBase):
    """POST /api/v1/organizers/login"""

    email: EmailStr


class OrganizerUpdate(VibeJudgeBase):
    """PUT /api/v1/organizers/me"""

    name: str | None = Field(None, min_length=1, max_length=100)
    organization: str | None = Field(None, max_length=200)


# --- Response Models ---


class OrganizerResponse(VibeJudgeBase, TimestampMixin):
    """GET /api/v1/organizers/me"""

    org_id: str
    email: str
    name: str
    organization: str | None = None
    tier: Tier = Tier.FREE
    hackathon_count: int = 0


class OrganizerCreateResponse(OrganizerResponse):
    """POST /api/v1/organizers — includes one-time API key"""

    api_key: str
    _warning: str = "Store your API key securely. It will not be shown again."


class OrganizerLoginResponse(VibeJudgeBase):
    """POST /api/v1/organizers/login"""

    org_id: str
    api_key: str
    _warning: str = "Previous API key has been invalidated."


# --- Internal / DynamoDB ---


class OrganizerRecord(OrganizerResponse):
    """Full DynamoDB record for organizer."""

    PK: str  # ORG#<org_id>
    SK: str = "PROFILE"
    entity_type: str = "ORGANIZER"
    api_key_hash: str
    GSI1PK: str  # EMAIL#<email>
    GSI1SK: str  # ORG#<org_id>
