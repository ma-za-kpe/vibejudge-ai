"""GitHub Actions workflow analysis."""

from src.models.analysis import WorkflowRun
from src.utils.github_client import GitHubClient
from src.utils.logging import get_logger

logger = get_logger(__name__)


class ActionsAnalyzer:
    """Analyze GitHub Actions workflows and runs."""
    
    def __init__(self, github_token: str | None = None):
        """Initialize Actions analyzer.
        
        Args:
            github_token: GitHub personal access token (optional)
        """
        self.client = GitHubClient(token=github_token)
    
    def analyze(self, owner: str, repo: str) -> dict:
        """Analyze GitHub Actions for a repository.
        
        Args:
            owner: Repository owner
            repo: Repository name
            
        Returns:
            Dict with workflow_runs and workflow_definitions
        """
        logger.info("actions_analysis_started", owner=owner, repo=repo)
        
        # Fetch workflow runs
        workflow_runs = self.client.fetch_workflow_runs(owner, repo, max_runs=50)
        
        # Fetch workflow definition files
        workflow_definitions = self.client.fetch_workflow_files(owner, repo)
        
        logger.info(
            "actions_analysis_complete",
            owner=owner,
            repo=repo,
            runs=len(workflow_runs),
            definitions=len(workflow_definitions),
        )
        
        return {
            "workflow_runs": workflow_runs,
            "workflow_definitions": workflow_definitions,
        }
    
    def close(self):
        """Close the GitHub client."""
        self.client.close()
