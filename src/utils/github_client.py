"""GitHub REST API client using httpx (NOT PyGithub)."""

import httpx

from src.models.analysis import WorkflowRun
from src.utils.config import settings
from src.utils.logging import get_logger

logger = get_logger(__name__)


class GitHubClient:
    """GitHub REST API client for Actions data."""
    
    BASE_URL = "https://api.github.com"
    
    def __init__(self, token: str | None = None):
        """Initialize GitHub client.
        
        Args:
            token: GitHub personal access token (optional)
        """
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        
        token = token or settings.github_token
        if token:
            headers["Authorization"] = f"Bearer {token}"
        
        self.client = httpx.Client(
            base_url=self.BASE_URL,
            headers=headers,
            timeout=30.0,
        )
    
    def fetch_workflow_runs(
        self, owner: str, repo: str, max_runs: int = 50
    ) -> list[WorkflowRun]:
        """Fetch workflow run history.
        
        Args:
            owner: Repository owner
            repo: Repository name
            max_runs: Maximum number of runs to fetch
            
        Returns:
            List of WorkflowRun objects
        """
        # TODO: Implement workflow runs fetching
        # Reference: docs/08-git-analysis-spec.md section 6
        logger.warning("github_client_not_implemented", method="fetch_workflow_runs")
        return []
    
    def fetch_workflow_files(self, owner: str, repo: str) -> list[str]:
        """Fetch workflow definition YAML files.
        
        Args:
            owner: Repository owner
            repo: Repository name
            
        Returns:
            List of workflow definition strings
        """
        # TODO: Implement workflow file fetching
        # Reference: docs/08-git-analysis-spec.md section 6
        logger.warning("github_client_not_implemented", method="fetch_workflow_files")
        return []
