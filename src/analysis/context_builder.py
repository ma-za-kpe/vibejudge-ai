"""Build agent context from repository data."""

from datetime import datetime

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
    logger.info("building_context", team=team_name, repo=repo_data.repo_name)

    # Format source files block
    source_files_block = ""
    for sf in repo_data.source_files:
        source_files_block += f"\n#### File: {sf.path} ({sf.lines} lines, {sf.language})\n"
        source_files_block += f"```{sf.language.lower() if sf.language else ''}\n"
        source_files_block += sf.content
        source_files_block += "\n```\n"

    # Format commit history block
    commit_block = ""
    for c in repo_data.commit_history[:50]:  # Limit to 50 most recent
        commit_block += (
            f"  {c.short_hash} | {c.timestamp.strftime('%Y-%m-%d %H:%M')} | "
            f"{c.author} | +{c.insertions}/-{c.deletions} | {c.message}\n"
        )

    # Format diff summary
    diff_block = ""
    for d in repo_data.diff_summary[:30]:  # Limit to 30
        diff_block += f"  [{d.commit_hash}] {d.change_type}: {d.file_path}\n"

    # Format workflow runs
    runs_block = ""
    for r in repo_data.workflow_runs[:20]:  # Limit to 20 most recent
        runs_block += (
            f"  {r.name} | {r.status}/{r.conclusion or 'pending'} | "
            f"{r.created_at.strftime('%Y-%m-%d %H:%M')}\n"
        )

    # Format workflow definitions
    wf_defs = (
        "\n".join(repo_data.workflow_definitions)
        if repo_data.workflow_definitions
        else "[No workflow files found]"
    )

    # Calculate workflow stats
    total_runs = len(repo_data.workflow_runs)
    successful_runs = sum(1 for r in repo_data.workflow_runs if r.conclusion == "success")
    failed_runs = sum(1 for r in repo_data.workflow_runs if r.conclusion == "failure")
    success_rate = (
        round(repo_data.meta.workflow_success_rate * 100, 1)
        if repo_data.meta.workflow_success_rate
        else 0.0
    )

    # Build complete context
    context = f"""## HACKATHON SUBMISSION FOR EVALUATION

**Hackathon:** {hackathon_name}
**Team:** {team_name}
**Repository:** {repo_data.repo_owner}/{repo_data.repo_name}
**URL:** {repo_data.repo_url}
**Timestamp:** {datetime.utcnow().isoformat()}Z
**AI Policy Mode:** {ai_policy_mode}

---

## REPOSITORY OVERVIEW

### Language & Technology Stack
- **Primary Language:** {repo_data.meta.primary_language or "Unknown"}
- **Language Breakdown:** {repo_data.meta.languages}
- **Total Files:** {repo_data.meta.total_files}
- **Total Lines of Code:** {repo_data.meta.total_lines}

### Development Activity
- **Commits:** {repo_data.meta.commit_count}
- **Contributors:** {repo_data.meta.contributor_count}
- **Development Duration:** {repo_data.meta.development_duration_hours:.1f} hours
- **First Commit:** {repo_data.meta.first_commit_at.strftime("%Y-%m-%d %H:%M") if repo_data.meta.first_commit_at else "N/A"}
- **Last Commit:** {repo_data.meta.last_commit_at.strftime("%Y-%m-%d %H:%M") if repo_data.meta.last_commit_at else "N/A"}
- **Default Branch:** {repo_data.default_branch}

### Project Features
- **Has README:** {"✓" if repo_data.meta.has_readme else "✗"}
- **Has Tests:** {"✓" if repo_data.meta.has_tests else "✗"}
- **Has CI/CD:** {"✓" if repo_data.meta.has_ci else "✗"}
- **Has Dockerfile:** {"✓" if repo_data.meta.has_dockerfile else "✗"}

---

## FILE STRUCTURE

```
{repo_data.file_tree}
```

---

## README

{repo_data.readme_content}

---

## SOURCE CODE ({len(repo_data.source_files)} files included)

{source_files_block}

---

## GIT HISTORY ({len(repo_data.commit_history)} commits)

### Recent Commits
{commit_block}

### Significant Changes
{diff_block}

---

## CI/CD & AUTOMATION

### GitHub Actions Workflows

**Workflow Definitions:**
{wf_defs}

**Workflow Run History:**
- **Total Runs:** {total_runs}
- **Successful:** {successful_runs}
- **Failed:** {failed_runs}
- **Success Rate:** {success_rate}%

**Recent Runs:**
{runs_block}

---

## EVALUATION RUBRIC

{rubric_json}

---

## INSTRUCTIONS

Analyze this repository according to the rubric above. Consider:
1. Code quality, architecture, and best practices
2. Innovation and creativity in the solution
3. Development process and iteration (git history)
4. Testing and CI/CD sophistication
5. Documentation quality
6. AI usage patterns (based on AI policy mode: {ai_policy_mode})

Provide specific evidence from the code, commits, and workflows to support your assessment.
"""

    logger.info("context_built", length=len(context), team=team_name)
    return context
