"""AIDetectionAnalyst Agent - Development authenticity analysis."""

from typing import Any

from src.agents.base import BaseAgent
from src.models.analysis import RepoData
from src.models.scores import AIDetectionResponse
from src.prompts import ai_detection_v1
from src.utils.bedrock import BedrockClient


class AIDetectionAgent(BaseAgent):
    """Agent for analyzing development patterns and AI usage indicators."""

    def __init__(self, bedrock_client: BedrockClient | None = None) -> None:
        super().__init__("ai_detection", bedrock_client)

    def get_system_prompt(self) -> str:
        """Get AIDetection system prompt."""
        return ai_detection_v1.SYSTEM_PROMPT

    def build_user_message(
        self,
        repo_data: RepoData,
        hackathon_name: str,
        team_name: str,
        ai_policy_mode: str = "ai_assisted",
        **kwargs: Any,
    ) -> str:
        """Build user message for AIDetection."""

        # Calculate velocity metrics
        if repo_data.meta.development_duration_hours > 0:
            lines_per_hour = repo_data.meta.total_lines / repo_data.meta.development_duration_hours
        else:
            lines_per_hour = 0

        # Format detailed commit log
        detailed_git_log = ""
        for c in repo_data.commit_history:
            detailed_git_log += (
                f"Commit: {c.hash}\n"
                f"Author: {c.author}\n"
                f"Date: {c.timestamp.isoformat()}\n"
                f"Message: {c.message}\n"
                f"Files changed: {c.files_changed}, +{c.insertions}/-{c.deletions}\n\n"
            )

        # Sample files for style analysis
        sample_files = ""
        for sf in repo_data.source_files[:3]:
            sample_files += f"\n#### File: {sf.path}\n```\n{sf.content[:1000]}\n```\n"

        message = f"""## HACKATHON SUBMISSION FOR EVALUATION

**Hackathon:** {hackathon_name}
**Team:** {team_name}
**Repository:** {repo_data.repo_url}
**AI Policy Mode:** {ai_policy_mode}
**Primary Language:** {repo_data.meta.primary_language or "Unknown"}
**Total Files:** {repo_data.meta.total_files} | **Total Lines:** {repo_data.meta.total_lines}
**Development Duration:** {repo_data.meta.development_duration_hours:.1f} hours
**Lines per Hour:** {lines_per_hour:.1f}

---

### GIT LOG (FULL — hash, author, date, message, files changed, insertions, deletions)
{detailed_git_log}

### COMMIT TIMING ANALYSIS
Total commits: {repo_data.meta.commit_count}
Development hours: {repo_data.meta.development_duration_hours:.1f}
First commit: {repo_data.meta.first_commit_at}
Last commit: {repo_data.meta.last_commit_at}

### SAMPLE CODE (for style analysis — 3 representative files)
{sample_files}

### GITHUB ACTIONS
Workflow runs: {repo_data.meta.workflow_run_count}
Success rate: {repo_data.meta.workflow_success_rate * 100:.1f}%

---

Evaluate per your dimensions and the AI policy mode. Return ONLY valid JSON.
"""
        return message

    def parse_response(self, response_dict: dict) -> AIDetectionResponse:
        """Parse AIDetection response."""
        # Filter out evidence items with None file values (invalid)
        if "evidence" in response_dict and isinstance(response_dict["evidence"], list):
            response_dict["evidence"] = [
                e
                for e in response_dict["evidence"]
                if isinstance(e, dict) and e.get("file") is not None
            ]
        return AIDetectionResponse(**response_dict)
