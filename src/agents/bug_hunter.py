"""BugHunter Agent - Code quality and security analysis."""

from typing import Any

from src.agents.base import BaseAgent
from src.models.analysis import RepoData
from src.models.scores import BugHunterResponse
from src.prompts import bug_hunter_v1
from src.utils.bedrock import BedrockClient


class BugHunterAgent(BaseAgent):
    """Agent for code quality, security, and testing analysis."""

    def __init__(self, bedrock_client: BedrockClient | None = None) -> None:
        super().__init__("bug_hunter", bedrock_client)

    def get_system_prompt(self) -> str:
        """Get BugHunter system prompt."""
        return bug_hunter_v1.SYSTEM_PROMPT

    def build_user_message(
        self, repo_data: RepoData, hackathon_name: str, team_name: str, **kwargs: Any
    ) -> str:
        """Build user message for BugHunter."""

        # Format source files
        source_files_content = ""
        for sf in repo_data.source_files[:15]:  # Limit to top 15 files
            source_files_content += f"\n#### File: {sf.path} ({sf.lines} lines, {sf.language})\n"
            source_files_content += f"```\n{sf.content}\n```\n"

        # Format commit history
        commit_history = ""
        for c in repo_data.commit_history[:50]:
            commit_history += (
                f"{c.short_hash} | {c.timestamp.strftime('%Y-%m-%d %H:%M')} | "
                f"{c.author} | +{c.insertions}/-{c.deletions} | {c.message}\n"
            )

        # Format actions summary
        actions_summary = f"Workflow runs: {repo_data.meta.workflow_run_count}\n"
        actions_summary += f"Success rate: {repo_data.meta.workflow_success_rate * 100:.1f}%\n"

        message = f"""## HACKATHON SUBMISSION FOR EVALUATION

**Hackathon:** {hackathon_name}
**Team:** {team_name}
**Repository:** {repo_data.repo_url}
**Primary Language:** {repo_data.meta.primary_language or "Unknown"}
**Languages:** {repo_data.meta.languages}
**Total Files:** {repo_data.meta.total_files} | **Total Lines:** {repo_data.meta.total_lines}

---

### FILE TREE
{repo_data.file_tree}

### KEY SOURCE FILES
{source_files_content}

### GIT HISTORY (last 50 commits, newest first)
{commit_history}

### GITHUB ACTIONS (CI/CD)
{actions_summary}

---

Evaluate this submission. Return ONLY valid JSON.
"""
        return message

    def parse_response(self, response_dict: dict) -> BugHunterResponse:
        """Parse BugHunter response."""
        # Filter out evidence items with None file values (invalid)
        if "evidence" in response_dict and isinstance(response_dict["evidence"], list):
            response_dict["evidence"] = [
                e
                for e in response_dict["evidence"]
                if isinstance(e, dict) and e.get("file") is not None
            ]
        return BugHunterResponse(**response_dict)
