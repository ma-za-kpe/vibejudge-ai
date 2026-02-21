# VibeJudge AI — Git Analysis Specification

> **Version:** 1.0  
> **Date:** February 2026  
> **Author:** Maku Mazakpe / Vibe Coders  
> **Status:** APPROVED  
> **Depends On:** ADR-005 (httpx), ADR-009 (GitPython+/tmp), Deliverable #4 (Agent Prompts)

---

## 1. Overview

The Git Analysis module is the data extraction layer — it transforms a raw GitHub repo URL into a structured `RepoData` object that agents consume. It has two sub-modules:

1. **`git_analyzer.py`** — Clones repo, extracts git history, file tree, source code, README
2. **`actions_analyzer.py`** — Calls GitHub REST API for Actions data (workflow runs, logs)

```
Repo URL → git_analyzer.clone_and_extract() → RepoData
         → actions_analyzer.fetch_actions()  ↗
```

---

## 2. Clone Strategy

### 2.1 Lambda /tmp Management

```python
import shutil
import tempfile
from pathlib import Path

CLONE_BASE = Path("/tmp/vibejudge-repos")

def get_clone_path(submission_id: str) -> Path:
    """Deterministic clone path per submission."""
    path = CLONE_BASE / submission_id
    path.mkdir(parents=True, exist_ok=True)
    return path

def cleanup_clone(submission_id: str) -> None:
    """Remove cloned repo after analysis."""
    path = CLONE_BASE / submission_id
    if path.exists():
        shutil.rmtree(path, ignore_errors=True)
```

### 2.2 Clone Parameters

```python
import git

def clone_repo(repo_url: str, clone_path: Path, timeout: int = 120) -> git.Repo:
    """Clone repository with full history.
    
    Args:
        repo_url: GitHub HTTPS URL
        clone_path: Local path for clone
        timeout: Git operation timeout in seconds
    
    Returns:
        GitPython Repo object
    
    Raises:
        git.GitCommandError: Clone failed (404, auth, timeout)
    """
    return git.Repo.clone_from(
        url=repo_url,
        to_path=str(clone_path),
        depth=None,          # Full history (not shallow)
        single_branch=False, # All branches
        no_tags=False,       # Include tags
        env={
            "GIT_TERMINAL_PROMPT": "0",  # Never prompt for credentials
            "GIT_HTTP_LOW_SPEED_LIMIT": "1000",  # Abort if <1KB/s
            "GIT_HTTP_LOW_SPEED_TIME": "30",      # for >30 seconds
        },
        kill_after_timeout=timeout,
    )
```

### 2.3 Fallback: Shallow Clone

If full clone exceeds /tmp capacity (2GB) or timeout:

```python
def clone_repo_shallow(repo_url: str, clone_path: Path) -> git.Repo:
    """Shallow clone — fallback for large repos."""
    return git.Repo.clone_from(
        url=repo_url,
        to_path=str(clone_path),
        depth=100,           # Last 100 commits only
        single_branch=True,  # Default branch only
        no_tags=True,
        env={"GIT_TERMINAL_PROMPT": "0"},
        kill_after_timeout=60,
    )
```

### 2.4 URL Parsing

```python
import re

GITHUB_URL_PATTERN = re.compile(
    r"^https://github\.com/(?P<owner>[\w\-\.]+)/(?P<repo>[\w\-\.]+?)(?:\.git)?/?$"
)

def parse_github_url(url: str) -> tuple[str, str]:
    """Extract owner and repo name from GitHub URL."""
    match = GITHUB_URL_PATTERN.match(url)
    if not match:
        raise ValueError(f"Invalid GitHub URL: {url}")
    return match.group("owner"), match.group("repo")
```

---

## 3. Git History Extraction

### 3.1 Commit History

```python
from datetime import datetime
from models.analysis import CommitInfo

def extract_commits(repo: git.Repo, max_commits: int = 100) -> list[CommitInfo]:
    """Extract commit history from default branch."""
    branch = _get_default_branch(repo)
    commits = []
    
    for commit in repo.iter_commits(branch, max_count=max_commits):
        stats = commit.stats.total
        commits.append(CommitInfo(
            hash=commit.hexsha,
            short_hash=commit.hexsha[:8],
            message=commit.message.strip().split("\n")[0][:200],  # First line, max 200 chars
            author=commit.author.name or commit.author.email or "unknown",
            timestamp=datetime.fromtimestamp(commit.committed_date),
            files_changed=stats.get("files", 0),
            insertions=stats.get("insertions", 0),
            deletions=stats.get("deletions", 0),
        ))
    
    return commits


def _get_default_branch(repo: git.Repo) -> str:
    """Determine the default branch (main, master, or first available)."""
    for branch_name in ["main", "master", "develop"]:
        if branch_name in [b.name for b in repo.branches]:
            return branch_name
    # Fallback to first branch
    if repo.branches:
        return repo.branches[0].name
    raise ValueError("Repository has no branches")
```

### 3.2 Diff Summary

```python
from models.analysis import DiffEntry

def extract_diff_summary(
    repo: git.Repo, 
    commits: list[CommitInfo], 
    max_diffs: int = 30
) -> list[DiffEntry]:
    """Extract significant diffs from commit history.
    
    Strategy: Focus on commits with the most changes (likely feature additions)
    and commits with fixes/refactors (indicate iteration).
    """
    diffs = []
    
    # Sort commits by total changes (insertions + deletions)
    sorted_commits = sorted(
        commits,
        key=lambda c: c.insertions + c.deletions,
        reverse=True,
    )
    
    for commit_info in sorted_commits[:max_diffs]:
        commit = repo.commit(commit_info.hash)
        parent = commit.parents[0] if commit.parents else git.NULL_TREE
        
        for diff_item in commit.diff(parent):
            change_type = _diff_change_type(diff_item)
            diffs.append(DiffEntry(
                commit_hash=commit_info.short_hash,
                file_path=diff_item.b_path or diff_item.a_path or "unknown",
                change_type=change_type,
                insertions=0,  # GitPython diff doesn't easily give per-file stats
                deletions=0,
                summary=f"{change_type}: {diff_item.b_path or diff_item.a_path}",
            ))
        
        if len(diffs) >= max_diffs:
            break
    
    return diffs[:max_diffs]


def _diff_change_type(diff_item) -> str:
    if diff_item.new_file:
        return "added"
    elif diff_item.deleted_file:
        return "deleted"
    elif diff_item.renamed_file:
        return "renamed"
    else:
        return "modified"
```

---

## 4. File Tree & Source Code Extraction

### 4.1 File Tree

```python
from pathlib import Path

# Files/dirs to always skip
IGNORE_PATTERNS = {
    ".git", "__pycache__", "node_modules", ".venv", "venv",
    ".env", ".DS_Store", "*.pyc", "*.pyo", "*.egg-info",
    "dist", "build", ".next", ".nuxt", "coverage",
    ".terraform", ".serverless",
}

def extract_file_tree(clone_path: Path, max_depth: int = 4) -> str:
    """Generate a file tree string for agent context."""
    lines = []
    _walk_tree(clone_path, lines, prefix="", depth=0, max_depth=max_depth)
    return "\n".join(lines[:200])  # Cap at 200 lines


def _walk_tree(
    path: Path, lines: list, prefix: str, depth: int, max_depth: int
) -> None:
    if depth > max_depth:
        return
    
    entries = sorted(path.iterdir(), key=lambda p: (not p.is_dir(), p.name))
    filtered = [e for e in entries if e.name not in IGNORE_PATTERNS]
    
    for i, entry in enumerate(filtered):
        is_last = i == len(filtered) - 1
        connector = "└── " if is_last else "├── "
        lines.append(f"{prefix}{connector}{entry.name}")
        
        if entry.is_dir():
            extension = "    " if is_last else "│   "
            _walk_tree(entry, lines, prefix + extension, depth + 1, max_depth)
```

### 4.2 Source File Selection & Extraction

```python
from models.analysis import SourceFile

# Priority scoring for file selection
FILE_PRIORITIES = {
    # Entry points (highest priority)
    "main.py": 100, "app.py": 100, "server.py": 100,
    "index.js": 100, "index.ts": 100, "main.go": 100,
    "main.rs": 100, "Program.cs": 100,
    
    # Configuration
    "requirements.txt": 90, "pyproject.toml": 90,
    "package.json": 90, "Cargo.toml": 90,
    "Dockerfile": 85, "docker-compose.yml": 85, "docker-compose.yaml": 85,
    
    # IaC
    "template.yaml": 80, "template.yml": 80,
    "serverless.yml": 80, "cdk.json": 80,
    
    # README always included via separate field
}

# Extensions considered "source code"
SOURCE_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".rs",
    ".java", ".kt", ".cs", ".rb", ".php", ".swift",
    ".c", ".cpp", ".h", ".hpp", ".sql", ".sh",
}

# Extensions for config/data files
CONFIG_EXTENSIONS = {
    ".json", ".yaml", ".yml", ".toml", ".env.example",
    ".cfg", ".ini", ".xml",
}

MAX_FILE_LINES = 200
MAX_FILES = 25


def extract_source_files(
    clone_path: Path, 
    max_files: int = MAX_FILES,
    max_lines_per_file: int = MAX_FILE_LINES,
) -> list[SourceFile]:
    """Select and extract the most important source files."""
    candidates = []
    
    for file_path in clone_path.rglob("*"):
        if not file_path.is_file():
            continue
        if any(p in file_path.parts for p in IGNORE_PATTERNS):
            continue
        
        relative = file_path.relative_to(clone_path)
        ext = file_path.suffix.lower()
        name = file_path.name
        
        # Determine priority
        priority = FILE_PRIORITIES.get(name, 0)
        
        if ext in SOURCE_EXTENSIONS:
            priority = max(priority, 50)
        elif ext in CONFIG_EXTENSIONS:
            priority = max(priority, 40)
        elif name.startswith("test_") or name.endswith("_test.py") or "test" in name.lower():
            priority = max(priority, 70)  # Tests are important
        elif ".github/workflows" in str(relative):
            priority = max(priority, 80)  # CI/CD definitions
        else:
            continue  # Skip non-code files (images, binaries, etc.)
        
        # Read file content
        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
            lines = content.split("\n")
            line_count = len(lines)
        except (OSError, UnicodeDecodeError):
            continue
        
        # Skip very large files (likely generated/vendor)
        if line_count > 5000:
            content = "\n".join(lines[:max_lines_per_file])
            content += f"\n\n... [TRUNCATED: {line_count} total lines, showing first {max_lines_per_file}]"
            line_count = max_lines_per_file
        elif line_count > max_lines_per_file:
            content = "\n".join(lines[:max_lines_per_file])
            content += f"\n\n... [TRUNCATED: {line_count} total lines]"
        
        candidates.append(SourceFile(
            path=str(relative),
            content=content,
            lines=line_count,
            language=_detect_language(ext),
            priority=priority,
        ))
    
    # Sort by priority (highest first), then by line count (larger = more important)
    candidates.sort(key=lambda f: (-f.priority, -f.lines))
    return candidates[:max_files]


def _detect_language(ext: str) -> str:
    LANG_MAP = {
        ".py": "Python", ".js": "JavaScript", ".ts": "TypeScript",
        ".jsx": "React/JSX", ".tsx": "React/TSX", ".go": "Go",
        ".rs": "Rust", ".java": "Java", ".kt": "Kotlin",
        ".cs": "C#", ".rb": "Ruby", ".php": "PHP",
        ".swift": "Swift", ".c": "C", ".cpp": "C++",
        ".sql": "SQL", ".sh": "Shell",
        ".json": "JSON", ".yaml": "YAML", ".yml": "YAML",
        ".toml": "TOML",
    }
    return LANG_MAP.get(ext, "Unknown")
```

### 4.3 README Extraction

```python
def extract_readme(clone_path: Path, max_chars: int = 12000) -> str:
    """Find and extract README content."""
    readme_names = [
        "README.md", "README.MD", "readme.md",
        "README.rst", "README.txt", "README",
    ]
    
    for name in readme_names:
        readme_path = clone_path / name
        if readme_path.exists():
            try:
                content = readme_path.read_text(encoding="utf-8", errors="replace")
                if len(content) > max_chars:
                    content = content[:max_chars] + "\n\n... [README TRUNCATED]"
                return content
            except OSError:
                continue
    
    return "[No README found]"
```

---

## 5. Language & Metadata Analysis

```python
from collections import Counter
from models.submission import RepoMeta

def extract_repo_meta(
    repo: git.Repo,
    clone_path: Path,
    commits: list[CommitInfo],
    workflow_runs: list = None,
) -> RepoMeta:
    """Build comprehensive repo metadata."""
    
    # Count files by extension
    ext_counter = Counter()
    total_files = 0
    total_lines = 0
    
    for file_path in clone_path.rglob("*"):
        if not file_path.is_file():
            continue
        if any(p in file_path.parts for p in IGNORE_PATTERNS):
            continue
        
        ext = file_path.suffix.lower()
        if ext in SOURCE_EXTENSIONS or ext in CONFIG_EXTENSIONS:
            total_files += 1
            try:
                line_count = sum(1 for _ in file_path.open(encoding="utf-8", errors="replace"))
                total_lines += line_count
                lang = _detect_language(ext)
                if lang != "Unknown":
                    ext_counter[lang] += line_count
            except OSError:
                pass
    
    # Calculate language percentages
    total_lang_lines = sum(ext_counter.values()) or 1
    languages = {
        lang: round(count / total_lang_lines * 100, 1)
        for lang, count in ext_counter.most_common(10)
    }
    primary_language = ext_counter.most_common(1)[0][0] if ext_counter else None
    
    # Development duration
    first_commit_at = commits[-1].timestamp if commits else None
    last_commit_at = commits[0].timestamp if commits else None
    dev_hours = 0.0
    if first_commit_at and last_commit_at:
        delta = last_commit_at - first_commit_at
        dev_hours = round(delta.total_seconds() / 3600, 2)
    
    # Contributors
    authors = set(c.author for c in commits)
    
    # Detect features
    has_readme = (clone_path / "README.md").exists() or (clone_path / "readme.md").exists()
    has_tests = _has_test_files(clone_path)
    has_ci = (clone_path / ".github" / "workflows").exists()
    has_dockerfile = (clone_path / "Dockerfile").exists()
    
    # Workflow stats
    wf_count = len(workflow_runs) if workflow_runs else 0
    wf_success = sum(1 for r in (workflow_runs or []) if r.conclusion == "success")
    wf_rate = round(wf_success / wf_count, 2) if wf_count > 0 else 0.0
    
    return RepoMeta(
        commit_count=len(commits),
        branch_count=len(list(repo.branches)),
        contributor_count=len(authors),
        primary_language=primary_language,
        languages=languages,
        total_files=total_files,
        total_lines=total_lines,
        has_readme=has_readme,
        has_tests=has_tests,
        has_ci=has_ci,
        has_dockerfile=has_dockerfile,
        first_commit_at=first_commit_at,
        last_commit_at=last_commit_at,
        development_duration_hours=dev_hours,
        workflow_run_count=wf_count,
        workflow_success_rate=wf_rate,
    )


def _has_test_files(clone_path: Path) -> bool:
    """Check if repo contains test files."""
    test_patterns = [
        "test_*.py", "*_test.py", "*_test.go", "*.test.js", "*.test.ts",
        "*.spec.js", "*.spec.ts", "*Test.java", "*_test.rs",
    ]
    tests_dir = clone_path / "tests"
    test_dir = clone_path / "test"
    
    if tests_dir.exists() or test_dir.exists():
        return True
    
    for pattern in test_patterns:
        if list(clone_path.rglob(pattern)):
            return True
    
    return False
```

---

## 6. GitHub Actions Analyzer

```python
"""GitHub Actions data extraction via REST API."""

import httpx
from models.analysis import WorkflowRun


class ActionsAnalyzer:
    """Fetch GitHub Actions data for a repository."""
    
    BASE_URL = "https://api.github.com"
    
    def __init__(self, token: str | None = None):
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
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
        """Fetch workflow run history."""
        runs = []
        try:
            resp = self.client.get(
                f"/repos/{owner}/{repo}/actions/runs",
                params={"per_page": min(max_runs, 100)},
            )
            if resp.status_code == 404:
                return []  # No Actions or private repo without auth
            resp.raise_for_status()
            
            for run in resp.json().get("workflow_runs", []):
                runs.append(WorkflowRun(
                    run_id=run["id"],
                    name=run.get("name", "unknown"),
                    status=run.get("status", "unknown"),
                    conclusion=run.get("conclusion"),
                    created_at=run["created_at"],
                    updated_at=run["updated_at"],
                    run_attempt=run.get("run_attempt", 1),
                ))
        except httpx.HTTPError:
            pass  # Actions data is supplementary; failure is non-fatal
        
        return runs[:max_runs]
    
    def fetch_workflow_files(self, owner: str, repo: str) -> list[str]:
        """Fetch workflow definition YAML files."""
        definitions = []
        try:
            resp = self.client.get(
                f"/repos/{owner}/{repo}/contents/.github/workflows"
            )
            if resp.status_code != 200:
                return []
            
            for item in resp.json():
                if item["name"].endswith((".yml", ".yaml")):
                    file_resp = self.client.get(item["download_url"])
                    if file_resp.status_code == 200:
                        definitions.append(
                            f"### {item['name']}\n```yaml\n{file_resp.text[:3000]}\n```"
                        )
        except httpx.HTTPError:
            pass
        
        return definitions
```

---

## 7. Context Assembly

The final step: assemble all extracted data into the repo context string that agents receive.

```python
from models.analysis import RepoData

def assemble_repo_context(
    repo_data: RepoData,
    hackathon_name: str,
    team_name: str,
    ai_policy_mode: str,
    rubric_json: str,
) -> str:
    """Assemble the full repo context string for agent consumption.
    
    Uses the REPO_CONTEXT_TEMPLATE from Deliverable #4 (Agent Prompt Library).
    """
    
    # Format source files block
    source_files_block = ""
    for sf in repo_data.source_files:
        source_files_block += f"\n#### File: {sf.path} ({sf.lines} lines, {sf.language})\n"
        source_files_block += f"```{sf.language.lower() if sf.language else ''}\n"
        source_files_block += sf.content
        source_files_block += "\n```\n"
    
    # Format commit history block
    commit_block = ""
    for c in repo_data.commit_history:
        commit_block += (
            f"  {c.short_hash} | {c.timestamp.strftime('%Y-%m-%d %H:%M')} | "
            f"{c.author} | +{c.insertions}/-{c.deletions} | {c.message}\n"
        )
    
    # Format diff summary
    diff_block = ""
    for d in repo_data.diff_summary:
        diff_block += f"  [{d.commit_hash}] {d.change_type}: {d.file_path}\n"
    
    # Format workflow runs
    runs_block = ""
    for r in repo_data.workflow_runs[:20]:
        runs_block += (
            f"  {r.name} | {r.status}/{r.conclusion or 'pending'} | "
            f"{r.created_at.strftime('%Y-%m-%d %H:%M')}\n"
        )
    
    # Format workflow definitions
    wf_defs = "\n".join(repo_data.workflow_definitions) if repo_data.workflow_definitions else "[No workflow files found]"
    
    # Build context from template
    context = REPO_CONTEXT_TEMPLATE.format(
        repo_owner=repo_data.repo_owner,
        repo_name=repo_data.repo_name,
        hackathon_name=hackathon_name,
        team_name=team_name,
        timestamp=datetime.utcnow().isoformat(),
        ai_policy_mode=ai_policy_mode,
        primary_language=repo_data.meta.primary_language or "Unknown",
        languages_breakdown=str(repo_data.meta.languages),
        total_files=repo_data.meta.total_files,
        total_lines=repo_data.meta.total_lines,
        commit_count=repo_data.meta.commit_count,
        contributor_count=repo_data.meta.contributor_count,
        dev_duration_hours=repo_data.meta.development_duration_hours,
        first_commit_at=repo_data.meta.first_commit_at or "N/A",
        last_commit_at=repo_data.meta.last_commit_at or "N/A",
        default_branch=repo_data.default_branch,
        has_readme=repo_data.meta.has_readme,
        has_tests=repo_data.meta.has_tests,
        has_ci=repo_data.meta.has_ci,
        file_tree=repo_data.file_tree,
        readme_content=repo_data.readme_content,
        num_files=len(repo_data.source_files),
        source_files_block=source_files_block,
        num_commits=len(repo_data.commit_history),
        commit_history_block=commit_block,
        diff_summary_block=diff_block,
        workflow_definitions=wf_defs,
        total_runs=repo_data.meta.workflow_run_count,
        successful_runs=sum(1 for r in repo_data.workflow_runs if r.conclusion == "success"),
        failed_runs=sum(1 for r in repo_data.workflow_runs if r.conclusion == "failure"),
        success_rate=round(repo_data.meta.workflow_success_rate * 100, 1),
        recent_runs_block=runs_block,
        rubric_json=rubric_json,
    )
    
    return context
```

---

## 8. End-to-End Flow

```python
async def analyze_submission(
    repo_url: str,
    submission_id: str,
    hackathon_config: HackathonDetail,
) -> RepoData:
    """Complete extraction pipeline for a single submission."""
    
    owner, repo_name = parse_github_url(repo_url)
    clone_path = get_clone_path(submission_id)
    
    try:
        # 1. Clone
        repo = clone_repo(repo_url, clone_path)
        
        # 2. Extract git history
        commits = extract_commits(repo, max_commits=100)
        diffs = extract_diff_summary(repo, commits, max_diffs=30)
        
        # 3. Extract files
        file_tree = extract_file_tree(clone_path)
        source_files = extract_source_files(clone_path)
        readme = extract_readme(clone_path)
        
        # 4. Fetch GitHub Actions (parallel with extraction)
        actions = ActionsAnalyzer(token=None)  # Public repos, no auth needed
        workflow_runs = actions.fetch_workflow_runs(owner, repo_name)
        workflow_defs = actions.fetch_workflow_files(owner, repo_name)
        
        # 5. Build metadata
        meta = extract_repo_meta(repo, clone_path, commits, workflow_runs)
        
        # 6. Assemble RepoData
        return RepoData(
            repo_url=repo_url,
            repo_owner=owner,
            repo_name=repo_name,
            default_branch=_get_default_branch(repo),
            meta=meta,
            file_tree=file_tree,
            readme_content=readme,
            source_files=source_files,
            commit_history=commits,
            diff_summary=diffs,
            workflow_definitions=workflow_defs,
            workflow_runs=workflow_runs,
        )
    
    finally:
        # ALWAYS clean up, even on error
        cleanup_clone(submission_id)
```

---

## 9. Error Scenarios

| Scenario | Handling |
|----------|---------|
| Repo URL 404 | Mark submission as `failed`, error: "Repository not found" |
| Private repo (no auth) | Mark as `failed`, error: "Repository not accessible (private)" |
| Clone timeout (>120s) | Retry with shallow clone. If still fails, mark `failed` |
| Repo >2GB | Use shallow clone (depth=100) |
| Empty repo (no commits) | Return RepoData with empty fields, agents score 0 |
| Binary-only repo | Return RepoData with no source files, agents note "no source code" |
| Malformed git history | Extract what's possible, note gaps in metadata |
| GitHub API rate limited | Skip Actions data, proceed with git-only analysis |

---

*End of Git Analysis Spec v1.0*  
*Next deliverable: #9 — Project Structure*
