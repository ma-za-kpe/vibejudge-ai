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
        from datetime import datetime
        
        runs = []
        try:
            resp = self.client.get(
                f"/repos/{owner}/{repo}/actions/runs",
                params={"per_page": min(max_runs, 100)},
            )
            
            if resp.status_code == 404:
                logger.info("github_actions_not_found", owner=owner, repo=repo)
                return []  # No Actions or private repo without auth
            
            resp.raise_for_status()
            
            for run in resp.json().get("workflow_runs", []):
                runs.append(WorkflowRun(
                    run_id=run["id"],
                    name=run.get("name", "unknown"),
                    status=run.get("status", "unknown"),
                    conclusion=run.get("conclusion"),
                    created_at=datetime.fromisoformat(run["created_at"].replace("Z", "+00:00")),
                    updated_at=datetime.fromisoformat(run["updated_at"].replace("Z", "+00:00")),
                    run_attempt=run.get("run_attempt", 1),
                ))
            
            logger.info(
                "github_workflow_runs_fetched",
                owner=owner,
                repo=repo,
                count=len(runs),
            )
            
        except httpx.HTTPError as e:
            logger.warning(
                "github_workflow_runs_failed",
                owner=owner,
                repo=repo,
                error=str(e),
            )
            # Actions data is supplementary; failure is non-fatal
        
        return runs[:max_runs]
    
    def fetch_workflow_files(self, owner: str, repo: str) -> list[str]:
        """Fetch workflow definition YAML files.
        
        Args:
            owner: Repository owner
            repo: Repository name
            
        Returns:
            List of workflow definition strings
        """
        definitions = []
        try:
            resp = self.client.get(
                f"/repos/{owner}/{repo}/contents/.github/workflows"
            )
            
            if resp.status_code != 200:
                logger.info("github_workflows_not_found", owner=owner, repo=repo)
                return []
            
            for item in resp.json():
                if item["name"].endswith((".yml", ".yaml")):
                    file_resp = self.client.get(item["download_url"])
                    if file_resp.status_code == 200:
                        content = file_resp.text[:3000]  # Truncate to 3000 chars
                        definitions.append(
                            f"### {item['name']}\n```yaml\n{content}\n```"
                        )
            
            logger.info(
                "github_workflow_files_fetched",
                owner=owner,
                repo=repo,
                count=len(definitions),
            )
            
        except httpx.HTTPError as e:
            logger.warning(
                "github_workflow_files_failed",
                owner=owner,
                repo=repo,
                error=str(e),
            )
        
        return definitions
    
    def close(self):
        """Close the HTTP client."""
        self.client.close()
