"""Error response models."""

from src.models.common import VibeJudgeBase


class ErrorDetail(VibeJudgeBase):
    """Standard error response body."""
    code: str
    message: str
    status: int
    detail: dict | list | str | None = None
    request_id: str | None = None


class ErrorResponse(VibeJudgeBase):
    """Wrapped error response."""
    error: ErrorDetail
