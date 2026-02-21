"""Build agent context from repository data."""

from src.models.analysis import RepoData
from src.utils.logging import get_logger

logger = get_logger(__name__)


def build_context(
    repo_data: RepoData,
    hackathon_name: str,
    team_name: str,
    ai_policy_mode: str,
    rubric_json: str,
) -> str:
    """Assemble full repo context string for agent consumption.
    
    Args:
        repo_data: Extracted repository data
        hackathon_name: Name of the hackathon
        team_name: Name of the team
        ai_policy_mode: AI policy mode
        rubric_json: Rubric as JSON string
        
    Returns:
        Formatted context string
    """
    # TODO: Implement context assembly
    # Reference: docs/08-git-analysis-spec.md section 7
    logger.warning("context_builder_not_implemented", method="build_context")
    
    return f"""## HACKATHON SUBMISSION FOR EVALUATION

**Hackathon:** {hackathon_name}
**Team:** {team_name}
**Repository:** {repo_data.repo_url}

[TODO: Complete context template implementation]
"""
