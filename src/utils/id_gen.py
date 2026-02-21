"""ULID generation for entity IDs."""

from ulid import ULID


def generate_id() -> str:
    """Generate a new ULID.
    
    ULIDs are:
    - Lexicographically sortable by timestamp
    - 128-bit (26 character string)
    - URL-safe
    - Case-insensitive
    - Monotonic within same millisecond
    
    Returns:
        ULID string (e.g., "01ARZ3NDEKTSV4RRFFQ69G5FAV")
    """
    return str(ULID())


def generate_org_id() -> str:
    """Generate organizer ID."""
    return generate_id()


def generate_hack_id() -> str:
    """Generate hackathon ID."""
    return generate_id()


def generate_sub_id() -> str:
    """Generate submission ID."""
    return generate_id()


def generate_job_id() -> str:
    """Generate analysis job ID."""
    return generate_id()
