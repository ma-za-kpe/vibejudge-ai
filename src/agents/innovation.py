"""InnovationScorer Agent - Creativity and novelty analysis."""

from src.agents.base import BaseAgent
from src.models.analysis import RepoData
from src.models.scores import InnovationResponse
from src.prompts import innovation_v1


class InnovationScorerAgent(BaseAgent):
    """Agent for technical innovation, creativity, and documentation analysis."""

    def __init__(self, bedrock_client=None):
        super().__init__("innovation", bedrock_client)

    def get_system_prompt(self) -> str:
        """Get InnovationScorer system prompt."""
        return innovation_v1.SYSTEM_PROMPT

    def build_user_message(
        self, repo_data: RepoData, hackathon_name: str, team_name: str, **kwargs
    ) -> str:
        """Build user message for InnovationScorer."""

        # Format source files
        source_files_content = ""
        for sf in repo_data.source_files[:12]:  # Fewer files, more focus on README
            source_files_content += f"\n#### File: {sf.path} ({sf.lines} lines, {sf.language})\n"
            source_files_content += f"```\n{sf.content}\n```\n"

        # Format full commit history (innovation cares about journey)
        commit_history = ""
        for c in repo_data.commit_history:
            commit_history += (
                f"{c.short_hash} | {c.timestamp.strftime('%Y-%m-%d %H:%M')} | "
                f"{c.author} | +{c.insertions}/-{c.deletions} | {c.message}\n"
            )

        message = f"""## HACKATHON SUBMISSION FOR EVALUATION

**Hackathon:** {hackathon_name}
**Team:** {team_name}
**Repository:** {repo_data.repo_url}
**Primary Language:** {repo_data.meta.primary_language or "Unknown"}
**Total Files:** {repo_data.meta.total_files} | **Total Lines:** {repo_data.meta.total_lines}
**Development Duration:** {repo_data.meta.development_duration_hours:.1f} hours
**Commit Count:** {repo_data.meta.commit_count}

---

### README.md (FULL CONTENT)
{repo_data.readme_content}

### FILE TREE
{repo_data.file_tree}

### CORE APPLICATION FILES
{source_files_content}

### GIT HISTORY (ALL commits — this tells the development story)
{commit_history}

---

Evaluate this submission. Return ONLY valid JSON.
"""
        return message

    def parse_response(self, response_dict: dict) -> InnovationResponse:
        """Parse InnovationScorer response."""
        # Filter out evidence items with None file values (invalid)
        if "evidence" in response_dict and isinstance(response_dict["evidence"], list):
            response_dict["evidence"] = [
                e
                for e in response_dict["evidence"]
                if isinstance(e, dict) and e.get("file") is not None
            ]
        return InnovationResponse(**response_dict)
