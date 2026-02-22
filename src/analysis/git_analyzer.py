"""Git repository analysis using GitPython."""

import re
import shutil
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

import git

from src.models.analysis import (
    CommitInfo,
    DiffEntry,
    RepoData,
    SourceFile,
)
from src.models.submission import RepoMeta
from src.utils.logging import get_logger

logger = get_logger(__name__)

# Clone configuration
CLONE_BASE = Path("/tmp/vibejudge-repos")
CLONE_TIMEOUT = 120  # seconds

# File patterns to ignore
IGNORE_PATTERNS = {
    ".git",
    "__pycache__",
    "node_modules",
    ".venv",
    "venv",
    ".env",
    ".DS_Store",
    ".pyc",
    ".pyo",
    ".egg-info",
    "dist",
    "build",
    ".next",
    ".nuxt",
    "coverage",
    ".terraform",
    ".serverless",
    "target",
    "bin",
    "obj",
}

# Source code extensions
SOURCE_EXTENSIONS = {
    ".py",
    ".js",
    ".ts",
    ".jsx",
    ".tsx",
    ".go",
    ".rs",
    ".java",
    ".kt",
    ".cs",
    ".rb",
    ".php",
    ".swift",
    ".c",
    ".cpp",
    ".h",
    ".hpp",
    ".sql",
    ".sh",
    ".bash",
}

# Config file extensions
CONFIG_EXTENSIONS = {
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".env.example",
    ".cfg",
    ".ini",
    ".xml",
    ".md",
    ".txt",
}

# File priority scoring
FILE_PRIORITIES = {
    # Entry points
    "main.py": 100,
    "app.py": 100,
    "server.py": 100,
    "index.js": 100,
    "index.ts": 100,
    "main.go": 100,
    "main.rs": 100,
    "Program.cs": 100,
    # Configuration
    "requirements.txt": 90,
    "pyproject.toml": 90,
    "package.json": 90,
    "Cargo.toml": 90,
    "Dockerfile": 85,
    "docker-compose.yml": 85,
    "docker-compose.yaml": 85,
    # IaC
    "template.yaml": 80,
    "template.yml": 80,
    "serverless.yml": 80,
    "cdk.json": 80,
}

# GitHub URL pattern
GITHUB_URL_PATTERN = re.compile(
    r"^https://github\.com/(?P<owner>[\w\-\.]+)/(?P<repo>[\w\-\.]+?)(?:\.git)?/?$"
)


def parse_github_url(url: str) -> tuple[str, str]:
    """Extract owner and repo name from GitHub URL.

    Args:
        url: GitHub repository URL

    Returns:
        Tuple of (owner, repo_name)

    Raises:
        ValueError: If URL is invalid
    """
    match = GITHUB_URL_PATTERN.match(url)
    if not match:
        raise ValueError(f"Invalid GitHub URL: {url}")
    return match.group("owner"), match.group("repo")


def get_clone_path(submission_id: str) -> Path:
    """Get deterministic clone path for submission.

    Args:
        submission_id: Submission ID

    Returns:
        Path for cloning
    """
    path = CLONE_BASE / submission_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def cleanup_clone(submission_id: str) -> None:
    """Remove cloned repository.

    Args:
        submission_id: Submission ID
    """
    path = CLONE_BASE / submission_id
    if path.exists():
        try:
            shutil.rmtree(path, ignore_errors=True)
            logger.info("clone_cleaned_up", sub_id=submission_id)
        except Exception as e:
            logger.warning("clone_cleanup_failed", sub_id=submission_id, error=str(e))


def clone_repo(repo_url: str, clone_path: Path, timeout: int = CLONE_TIMEOUT) -> git.Repo:
    """Clone repository with full history.

    Args:
        repo_url: GitHub HTTPS URL
        clone_path: Local path for clone
        timeout: Git operation timeout in seconds

    Returns:
        GitPython Repo object

    Raises:
        git.GitCommandError: Clone failed
    """
    try:
        repo = git.Repo.clone_from(
            url=repo_url,
            to_path=str(clone_path),
            depth=None,  # Full history
            single_branch=False,  # All branches
            no_tags=False,  # Include tags
            env={
                "GIT_TERMINAL_PROMPT": "0",  # Never prompt
                "GIT_HTTP_LOW_SPEED_LIMIT": "1000",
                "GIT_HTTP_LOW_SPEED_TIME": "30",
            },
            kill_after_timeout=timeout,
        )
        logger.info("repo_cloned", url=repo_url, path=str(clone_path))
        return repo
    except git.GitCommandError as e:
        # Try shallow clone as fallback
        logger.warning("full_clone_failed_trying_shallow", url=repo_url, error=str(e))
        return clone_repo_shallow(repo_url, clone_path)


def clone_repo_shallow(repo_url: str, clone_path: Path) -> git.Repo:
    """Shallow clone as fallback for large repos.

    Args:
        repo_url: GitHub HTTPS URL
        clone_path: Local path for clone

    Returns:
        GitPython Repo object

    Raises:
        git.GitCommandError: Clone failed
    """
    repo = git.Repo.clone_from(
        url=repo_url,
        to_path=str(clone_path),
        depth=100,  # Last 100 commits
        single_branch=True,  # Default branch only
        no_tags=True,
        env={"GIT_TERMINAL_PROMPT": "0"},
        kill_after_timeout=60,
    )
    logger.info("repo_cloned_shallow", url=repo_url)
    return repo


def get_default_branch(repo: git.Repo) -> str:
    """Determine the default branch.

    Args:
        repo: GitPython Repo object

    Returns:
        Default branch name
    """
    for branch_name in ["main", "master", "develop"]:
        if branch_name in [b.name for b in repo.branches]:
            return branch_name

    # Fallback to first branch
    if repo.branches:
        return repo.branches[0].name

    raise ValueError("Repository has no branches")


def extract_commits(repo: git.Repo, max_commits: int = 100) -> list[CommitInfo]:
    """Extract commit history from default branch.

    Args:
        repo: GitPython Repo object
        max_commits: Maximum number of commits to extract

    Returns:
        List of CommitInfo objects
    """
    branch = get_default_branch(repo)
    commits = []

    try:
        for commit in repo.iter_commits(branch, max_count=max_commits):
            stats = commit.stats.total
            commits.append(
                CommitInfo(
                    hash=commit.hexsha,
                    short_hash=commit.hexsha[:8],
                    message=commit.message.strip().split("\n")[0][:200],
                    author=commit.author.name or commit.author.email or "unknown",
                    timestamp=datetime.fromtimestamp(commit.committed_date, tz=UTC),
                    files_changed=stats.get("files", 0),
                    insertions=stats.get("insertions", 0),
                    deletions=stats.get("deletions", 0),
                )
            )
    except Exception as e:
        logger.warning("commit_extraction_failed", error=str(e))

    logger.info("commits_extracted", count=len(commits))
    return commits


def extract_diff_summary(
    repo: git.Repo, commits: list[CommitInfo], max_diffs: int = 30
) -> list[DiffEntry]:
    """Extract significant diffs from commit history.

    Args:
        repo: GitPython Repo object
        commits: List of commits
        max_diffs: Maximum number of diffs to extract

    Returns:
        List of DiffEntry objects
    """
    diffs = []

    # Sort commits by total changes
    sorted_commits = sorted(
        commits,
        key=lambda c: c.insertions + c.deletions,
        reverse=True,
    )

    for commit_info in sorted_commits[:max_diffs]:
        try:
            commit = repo.commit(commit_info.hash)
            parent = commit.parents[0] if commit.parents else git.NULL_TREE

            for diff_item in commit.diff(parent):
                change_type = _diff_change_type(diff_item)
                file_path = diff_item.b_path or diff_item.a_path or "unknown"

                diffs.append(
                    DiffEntry(
                        commit_hash=commit_info.short_hash,
                        file_path=file_path,
                        change_type=change_type,
                        insertions=0,  # Per-file stats not easily available
                        deletions=0,
                        summary=f"{change_type}: {file_path}",
                    )
                )

            if len(diffs) >= max_diffs:
                break
        except Exception as e:
            logger.warning("diff_extraction_failed", commit=commit_info.short_hash, error=str(e))
            continue

    logger.info("diffs_extracted", count=len(diffs))
    return diffs[:max_diffs]


def _diff_change_type(diff_item) -> str:
    """Determine change type from diff item."""
    if diff_item.new_file:
        return "added"
    elif diff_item.deleted_file:
        return "deleted"
    elif diff_item.renamed_file:
        return "renamed"
    else:
        return "modified"


def extract_file_tree(clone_path: Path, max_depth: int = 4) -> str:
    """Generate file tree string.

    Args:
        clone_path: Path to cloned repository
        max_depth: Maximum depth to traverse

    Returns:
        File tree string
    """
    lines = []
    _walk_tree(clone_path, lines, prefix="", depth=0, max_depth=max_depth)
    return "\n".join(lines[:200])  # Cap at 200 lines


def _walk_tree(path: Path, lines: list, prefix: str, depth: int, max_depth: int) -> None:
    """Recursively walk directory tree."""
    if depth > max_depth:
        return

    try:
        entries = sorted(path.iterdir(), key=lambda p: (not p.is_dir(), p.name))
        filtered = [e for e in entries if e.name not in IGNORE_PATTERNS]

        for i, entry in enumerate(filtered):
            is_last = i == len(filtered) - 1
            connector = "└── " if is_last else "├── "
            lines.append(f"{prefix}{connector}{entry.name}")

            if entry.is_dir():
                extension = "    " if is_last else "│   "
                _walk_tree(entry, lines, prefix + extension, depth + 1, max_depth)
    except PermissionError:
        pass


def extract_source_files(
    clone_path: Path,
    max_files: int = 25,
    max_lines_per_file: int = 200,
) -> list[SourceFile]:
    """Select and extract important source files.

    Args:
        clone_path: Path to cloned repository
        max_files: Maximum number of files to extract
        max_lines_per_file: Maximum lines per file

    Returns:
        List of SourceFile objects
    """
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
        elif "test" in name.lower():
            priority = max(priority, 70)
        elif ".github/workflows" in str(relative):
            priority = max(priority, 80)
        else:
            continue

        # Read file content
        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
            lines = content.split("\n")
            line_count = len(lines)
        except (OSError, UnicodeDecodeError):
            continue

        # Handle large files
        if line_count > 5000:
            content = "\n".join(lines[:max_lines_per_file])
            content += (
                f"\n\n... [TRUNCATED: {line_count} total lines, showing first {max_lines_per_file}]"
            )
            line_count = max_lines_per_file
        elif line_count > max_lines_per_file:
            content = "\n".join(lines[:max_lines_per_file])
            content += f"\n\n... [TRUNCATED: {line_count} total lines]"

        candidates.append(
            SourceFile(
                path=str(relative),
                content=content,
                lines=line_count,
                language=_detect_language(ext),
                priority=priority,
            )
        )

    # Sort by priority and size
    candidates.sort(key=lambda f: (-f.priority, -f.lines))
    logger.info("source_files_extracted", count=len(candidates[:max_files]))
    return candidates[:max_files]


def _detect_language(ext: str) -> str:
    """Detect language from file extension."""
    LANG_MAP = {
        ".py": "Python",
        ".js": "JavaScript",
        ".ts": "TypeScript",
        ".jsx": "React/JSX",
        ".tsx": "React/TSX",
        ".go": "Go",
        ".rs": "Rust",
        ".java": "Java",
        ".kt": "Kotlin",
        ".cs": "C#",
        ".rb": "Ruby",
        ".php": "PHP",
        ".swift": "Swift",
        ".c": "C",
        ".cpp": "C++",
        ".sql": "SQL",
        ".sh": "Shell",
        ".bash": "Bash",
        ".json": "JSON",
        ".yaml": "YAML",
        ".yml": "YAML",
        ".toml": "TOML",
        ".md": "Markdown",
        ".txt": "Text",
    }
    return LANG_MAP.get(ext, "Unknown")


def extract_readme(clone_path: Path, max_chars: int = 12000) -> str:
    """Find and extract README content.

    Args:
        clone_path: Path to cloned repository
        max_chars: Maximum characters to extract

    Returns:
        README content or placeholder
    """
    readme_names = [
        "README.md",
        "README.MD",
        "readme.md",
        "README.rst",
        "README.txt",
        "README",
    ]

    for name in readme_names:
        readme_path = clone_path / name
        if readme_path.exists():
            try:
                content = readme_path.read_text(encoding="utf-8", errors="replace")
                if len(content) > max_chars:
                    content = content[:max_chars] + "\n\n... [README TRUNCATED]"
                logger.info("readme_extracted", length=len(content))
                return content
            except OSError:
                continue

    logger.info("readme_not_found")
    return "[No README found]"


def extract_repo_meta(
    repo: git.Repo,
    clone_path: Path,
    commits: list[CommitInfo],
    workflow_runs: list = None,
) -> RepoMeta:
    """Build comprehensive repository metadata.

    Args:
        repo: GitPython Repo object
        clone_path: Path to cloned repository
        commits: List of commits
        workflow_runs: Optional list of workflow runs

    Returns:
        RepoMeta object
    """
    # Count files by language
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
    authors = {c.author for c in commits}

    # Detect features
    has_readme = any((clone_path / name).exists() for name in ["README.md", "readme.md", "README"])
    has_tests = _has_test_files(clone_path)
    has_ci = (clone_path / ".github" / "workflows").exists()
    has_dockerfile = (clone_path / "Dockerfile").exists()

    # Workflow stats
    wf_count = len(workflow_runs) if workflow_runs else 0
    wf_success = sum(1 for r in (workflow_runs or []) if r.conclusion == "success")
    wf_rate = round(wf_success / wf_count, 2) if wf_count > 0 else 0.0

    logger.info(
        "repo_meta_extracted",
        files=total_files,
        lines=total_lines,
        commits=len(commits),
        contributors=len(authors),
    )

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
    """Check if repository contains test files."""
    test_dirs = ["tests", "test", "__tests__", "spec"]

    for test_dir in test_dirs:
        if (clone_path / test_dir).exists():
            return True

    test_patterns = [
        "test_*.py",
        "*_test.py",
        "*_test.go",
        "*.test.js",
        "*.test.ts",
        "*.spec.js",
        "*.spec.ts",
        "*Test.java",
        "*_test.rs",
    ]

    return any(clone_path.rglob(pattern) for pattern in test_patterns)


def clone_and_extract(
    repo_url: str,
    submission_id: str,
    workflow_runs: list = None,
    workflow_definitions: list[str] = None,
) -> RepoData:
    """Complete extraction pipeline for a repository.

    Args:
        repo_url: GitHub repository URL
        submission_id: Submission ID for clone path
        workflow_runs: Optional pre-fetched workflow runs
        workflow_definitions: Optional pre-fetched workflow definitions

    Returns:
        RepoData object with all extracted information

    Raises:
        ValueError: Invalid URL
        git.GitCommandError: Clone failed
    """
    owner, repo_name = parse_github_url(repo_url)
    clone_path = get_clone_path(submission_id)

    try:
        # Clone repository
        repo = clone_repo(repo_url, clone_path)

        # Extract git history
        commits = extract_commits(repo, max_commits=100)
        diffs = extract_diff_summary(repo, commits, max_diffs=30)

        # Extract files
        file_tree = extract_file_tree(clone_path)
        source_files = extract_source_files(clone_path)
        readme = extract_readme(clone_path)

        # Build metadata
        meta = extract_repo_meta(repo, clone_path, commits, workflow_runs)

        # Get default branch
        default_branch = get_default_branch(repo)

        logger.info(
            "repo_extraction_complete",
            sub_id=submission_id,
            owner=owner,
            repo=repo_name,
            commits=len(commits),
            files=len(source_files),
        )

        return RepoData(
            repo_url=repo_url,
            repo_owner=owner,
            repo_name=repo_name,
            default_branch=default_branch,
            meta=meta,
            file_tree=file_tree,
            readme_content=readme,
            source_files=source_files,
            commit_history=commits,
            diff_summary=diffs,
            workflow_definitions=workflow_definitions or [],
            workflow_runs=workflow_runs or [],
        )

    finally:
        # Always cleanup
        cleanup_clone(submission_id)
