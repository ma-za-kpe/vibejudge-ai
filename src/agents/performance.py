"""PerformanceAnalyzer Agent - Architecture and scalability analysis."""

from src.agents.base import BaseAgent
from src.models.analysis import RepoData
from src.models.scores import PerformanceResponse
from src.prompts import performance_v1


class PerformanceAnalyzerAgent(BaseAgent):
    """Agent for architecture, database, API, and scalability analysis."""

    def __init__(self, bedrock_client=None):
        super().__init__("performance", bedrock_client)

    def get_system_prompt(self) -> str:
        """Get PerformanceAnalyzer system prompt."""
        return performance_v1.SYSTEM_PROMPT

    def build_user_message(
        self, repo_data: RepoData, hackathon_name: str, team_name: str, **kwargs
    ) -> str:
        """Build user message for PerformanceAnalyzer."""

        # Format source files
        source_files_content = ""
        for sf in repo_data.source_files[:15]:
            source_files_content += f"\n#### File: {sf.path} ({sf.lines} lines, {sf.language})\n"
            source_files_content += f"```\n{sf.content}\n```\n"

        # Format commit history
        commit_history = ""
        for c in repo_data.commit_history[:50]:
            commit_history += (
                f"{c.short_hash} | {c.timestamp.strftime('%Y-%m-%d %H:%M')} | "
                f"{c.author} | +{c.insertions}/-{c.deletions} | {c.message}\n"
            )

        # Format workflow info
        workflow_info = f"Workflow runs: {repo_data.meta.workflow_run_count}\n"
        workflow_info += f"Success rate: {repo_data.meta.workflow_success_rate * 100:.1f}%\n"
        if repo_data.workflow_definitions:
            workflow_info += "\n".join(repo_data.workflow_definitions[:2])

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

### ARCHITECTURE FILES
{source_files_content}

### GIT HISTORY (last 50 commits)
{commit_history}

### GITHUB ACTIONS
{workflow_info}

---

Evaluate this submission. Return ONLY valid JSON.
"""
        return message

    def parse_response(self, response_dict: dict) -> PerformanceResponse:
        """Parse PerformanceAnalyzer response."""
        # Filter out evidence items with None file values (invalid)
        if "evidence" in response_dict and isinstance(response_dict["evidence"], list):
            response_dict["evidence"] = [
                e
                for e in response_dict["evidence"]
                if isinstance(e, dict) and e.get("file") is not None
            ]
        return PerformanceResponse(**response_dict)
