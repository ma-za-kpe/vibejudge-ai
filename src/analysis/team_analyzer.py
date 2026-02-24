"""Team dynamics analyzer for hackathon submissions.

Analyzes team collaboration patterns, workload distribution, individual
contributions, and generates hiring intelligence from git history.
"""

import time
from collections import defaultdict

import structlog

from src.models.analysis import CommitInfo, RepoData
from src.models.team_dynamics import (
    CollaborationPattern,
    ContributorRole,
    ExpertiseArea,
    HiringSignals,
    IndividualScorecard,
    RedFlag,
    RedFlagSeverity,
    TeamAnalysisResult,
    WorkStyle,
)

logger = structlog.get_logger()


class TeamAnalyzer:
    """Analyzes team dynamics and individual contributions from git history.

    Responsibilities:
    - Calculate workload distribution across contributors
    - Detect collaboration patterns (pair programming, code review)
    - Identify red flags (ghost contributors, extreme imbalance)
    - Generate individual contributor scorecards
    - Detect work patterns (late-night coding, panic pushes)
    - Calculate team dynamics grade (A-F)
    """

    def __init__(self) -> None:
        """Initialize TeamAnalyzer."""
        self.logger = logger.bind(component="team_analyzer")

    def analyze(self, repo_data: RepoData) -> TeamAnalysisResult:
        """Analyze team dynamics from git history.

        Args:
            repo_data: Repository data with commit history

        Returns:
            TeamAnalysisResult with dynamics and scorecards
        """
        start_time = time.time()

        self.logger.info(
            "team_analysis_started",
            repo_url=repo_data.repo_url,
            commit_count=len(repo_data.commit_history),
        )

        # Handle edge cases
        if not repo_data.commit_history:
            self.logger.warning("empty_commit_history", repo_url=repo_data.repo_url)
            return self._empty_result(start_time)

        commits = repo_data.commit_history

        # Extract unique contributors
        contributors = self._extract_contributors(commits)

        # Calculate workload distribution
        workload_dist = self._calculate_workload_distribution(commits)

        # Detect collaboration patterns
        collab_patterns = self._detect_collaboration_patterns(commits)

        # Detect red flags
        red_flags = self._detect_red_flags(commits, contributors, workload_dist)

        # Generate individual scorecards
        scorecards = self._generate_individual_scorecards(
            commits, contributors, workload_dist, repo_data
        )

        # Calculate commit message quality
        msg_quality = self._calculate_commit_message_quality(commits)

        # Analyze commit timing (late-night coding, panic pushes)
        late_night_count, panic_push = self._analyze_commit_timing(commits)

        # Calculate team grade
        team_grade = self._calculate_team_grade(
            workload_dist, collab_patterns, msg_quality, red_flags
        )

        duration_ms = max(1, int((time.time() - start_time) * 1000))

        self.logger.info(
            "team_analysis_completed",
            repo_url=repo_data.repo_url,
            contributors=len(contributors),
            red_flags=len(red_flags),
            team_grade=team_grade,
            duration_ms=duration_ms,
        )

        return TeamAnalysisResult(
            workload_distribution=workload_dist,
            collaboration_patterns=collab_patterns,
            red_flags=red_flags,
            individual_scorecards=scorecards,
            team_dynamics_grade=team_grade,
            commit_message_quality=msg_quality,
            panic_push_detected=panic_push,
            duration_ms=duration_ms,
        )

    def _empty_result(self, start_time: float) -> TeamAnalysisResult:
        """Return empty result for repositories with no commits."""
        duration_ms = max(1, int((time.time() - start_time) * 1000))
        return TeamAnalysisResult(
            workload_distribution={},
            collaboration_patterns=[],
            red_flags=[],
            individual_scorecards=[],
            team_dynamics_grade="F",
            commit_message_quality=0.0,
            panic_push_detected=False,
            duration_ms=duration_ms,
        )

    def _extract_contributors(self, commits: list[CommitInfo]) -> list[str]:
        """Extract unique contributor names from commits."""
        return list({commit.author for commit in commits})

    def _calculate_workload_distribution(self, commits: list[CommitInfo]) -> dict[str, float]:
        """Calculate percentage of commits per contributor.

        Args:
            commits: List of commit information

        Returns:
            Dictionary mapping contributor name to percentage (0-100)
        """
        if not commits:
            return {}

        # Count commits per contributor
        commit_counts: dict[str, int] = defaultdict(int)
        for commit in commits:
            commit_counts[commit.author] += 1

        # Calculate percentages
        total_commits = len(commits)
        distribution = {
            author: (count / total_commits) * 100 for author, count in commit_counts.items()
        }

        return distribution

    def _detect_collaboration_patterns(
        self, commits: list[CommitInfo]
    ) -> list[CollaborationPattern]:
        """Detect pair programming, code review, and knowledge silos.

        Analyzes:
        1. Alternating commits (pair programming indicator)
        2. Code review patterns from commit messages
        3. Knowledge silos (files touched by only one person)

        Args:
            commits: List of commit information

        Returns:
            List of detected collaboration patterns
        """
        patterns: list[CollaborationPattern] = []

        # 1. Detect alternating commits (pair programming indicator)
        if len(commits) >= 4:
            patterns.extend(self._detect_alternating_commits(commits))

        # 2. Detect code review patterns from commit messages
        patterns.extend(self._detect_code_review_patterns(commits))

        # 3. Identify knowledge silos (files touched by only one person)
        patterns.extend(self._detect_knowledge_silos(commits))

        return patterns

    def _detect_alternating_commits(self, commits: list[CommitInfo]) -> list[CollaborationPattern]:
        """Detect alternating commit patterns between two contributors."""
        patterns: list[CollaborationPattern] = []

        # Sort commits by timestamp
        sorted_commits = sorted(commits, key=lambda c: c.timestamp)

        # Look for sequences of alternating authors
        for i in range(len(sorted_commits) - 3):
            authors = [
                sorted_commits[i].author,
                sorted_commits[i + 1].author,
                sorted_commits[i + 2].author,
                sorted_commits[i + 3].author,
            ]

            # Check if pattern is A-B-A-B
            if authors[0] == authors[2] and authors[1] == authors[3] and authors[0] != authors[1]:
                pattern = CollaborationPattern(
                    pattern_type="pair_programming",
                    contributors=[authors[0], authors[1]],
                    evidence=f"Alternating commits: {sorted_commits[i].short_hash}, "
                    f"{sorted_commits[i + 1].short_hash}, "
                    f"{sorted_commits[i + 2].short_hash}, "
                    f"{sorted_commits[i + 3].short_hash}",
                    positive=True,
                )
                patterns.append(pattern)
                break  # Only report first occurrence

        return patterns

    def _detect_code_review_patterns(self, commits: list[CommitInfo]) -> list[CollaborationPattern]:
        """Detect code review patterns from commit messages.

        Looks for indicators of code review in commit messages:
        - "reviewed by", "review:", "reviewed-by:"
        - "co-authored-by:", "pair:", "pairing with"
        - Merge commits (indicating PR merges)

        Args:
            commits: List of commit information

        Returns:
            List of code review collaboration patterns
        """
        patterns: list[CollaborationPattern] = []

        # Keywords indicating code review
        review_keywords = [
            "reviewed by",
            "review:",
            "reviewed-by:",
            "co-authored-by:",
            "pair:",
            "pairing with",
            "pair programming",
        ]

        # Track reviewers and authors
        review_pairs: dict[tuple[str, str], list[str]] = {}  # (author, reviewer) -> [commit_hashes]
        merge_commits = 0

        for commit in commits:
            message_lower = commit.message.lower()

            # Check for merge commits (PR indicator)
            if message_lower.startswith("merge pull request") or message_lower.startswith(
                "merge branch"
            ):
                merge_commits += 1
                continue

            # Check for review keywords
            for keyword in review_keywords:
                if keyword in message_lower:
                    # Extract reviewer name if possible
                    # Format: "reviewed by @username" or "co-authored-by: Name <email>"
                    reviewer = "unknown"
                    if "co-authored-by:" in message_lower:
                        # Extract name from "Co-authored-by: Name <email>"
                        parts = commit.message.split("Co-authored-by:")
                        if len(parts) > 1:
                            reviewer_part = parts[1].split("<")[0].strip()
                            if reviewer_part:
                                reviewer = reviewer_part

                    pair_key = (commit.author, reviewer)
                    if pair_key not in review_pairs:
                        review_pairs[pair_key] = []
                    review_pairs[pair_key].append(commit.short_hash)
                    break

        # Generate patterns for significant review activity
        for (author, reviewer), commit_hashes in review_pairs.items():
            if len(commit_hashes) >= 2:  # At least 2 reviewed commits
                patterns.append(
                    CollaborationPattern(
                        pattern_type="code_review",
                        contributors=[author, reviewer] if reviewer != "unknown" else [author],
                        evidence=f"Code review indicators in {len(commit_hashes)} commits: {', '.join(commit_hashes[:3])}",
                        positive=True,
                    )
                )

        # Add pattern for merge commits (PR-based workflow)
        if merge_commits >= 3:
            patterns.append(
                CollaborationPattern(
                    pattern_type="code_review",
                    contributors=[],  # Team-wide pattern
                    evidence=f"{merge_commits} merge commits detected (PR-based workflow)",
                    positive=True,
                )
            )

        return patterns

    def _detect_knowledge_silos(self, commits: list[CommitInfo]) -> list[CollaborationPattern]:
        """Identify knowledge silos - files touched by only one person.

        Analyzes commit history to find files that only one contributor
        has modified, which can indicate knowledge concentration and
        potential bus factor issues.

        Args:
            commits: List of commit information

        Returns:
            List of knowledge silo patterns (negative collaboration indicator)
        """
        patterns: list[CollaborationPattern] = []

        # Build file -> set of contributors mapping
        # Note: We don't have per-file data in CommitInfo, so we'll use a heuristic
        # based on commit patterns and file counts

        # Track contributors and their commit patterns
        contributor_commits: dict[str, list[CommitInfo]] = {}
        for commit in commits:
            if commit.author not in contributor_commits:
                contributor_commits[commit.author] = []
            contributor_commits[commit.author].append(commit)

        # If we have multiple contributors, check for isolation patterns
        if len(contributor_commits) >= 2:
            # Look for contributors who never overlap in timing
            # (indicator of working on separate parts)
            contributors = list(contributor_commits.keys())

            for i, contributor in enumerate(contributors):
                contributor_commit_times = [c.timestamp for c in contributor_commits[contributor]]

                # Check if this contributor's commits are isolated from others
                isolated = True
                for j, other_contributor in enumerate(contributors):
                    if i == j:
                        continue

                    other_commit_times = [
                        c.timestamp for c in contributor_commits[other_contributor]
                    ]

                    # Check for temporal overlap (commits within same time windows)
                    for c_time in contributor_commit_times:
                        for o_time in other_commit_times:
                            time_diff = abs((c_time - o_time).total_seconds())
                            # If commits within 1 hour, consider it collaborative
                            if time_diff < 3600:
                                isolated = False
                                break
                        if not isolated:
                            break
                    if not isolated:
                        break

                # If contributor is isolated and has significant commits
                if isolated and len(contributor_commits[contributor]) >= 5:
                    patterns.append(
                        CollaborationPattern(
                            pattern_type="knowledge_silo",
                            contributors=[contributor],
                            evidence=f"{contributor} has {len(contributor_commits[contributor])} commits "
                            f"with no temporal overlap with other contributors",
                            positive=False,  # This is a negative pattern
                        )
                    )

        return patterns

    def _detect_red_flags(
        self, commits: list[CommitInfo], contributors: list[str], workload_dist: dict[str, float]
    ) -> list[RedFlag]:
        """Identify concerning team dynamics patterns.

        Detects:
        - Ghost contributors (0 commits)
        - Minimal contribution (≤2 commits in team of 3+)
        - Extreme imbalance (>80% commits)
        - Unhealthy patterns (>10 late-night commits)
        - History rewriting (>5 force pushes)

        Args:
            commits: List of commit information
            contributors: List of contributor names
            workload_dist: Workload distribution percentages

        Returns:
            List of red flags with severity and recommendations
        """
        red_flags: list[RedFlag] = []

        # 1. Check for extreme workload imbalance (>80%)
        for author, percentage in workload_dist.items():
            if percentage > 80:
                commit_count = int(percentage * len(commits) / 100)
                red_flags.append(
                    RedFlag(
                        flag_type="extreme_imbalance",
                        severity=RedFlagSeverity.CRITICAL,
                        description=f"{author} contributed {percentage:.1f}% of commits",
                        evidence=f"{commit_count} out of {len(commits)} commits",
                        impact="Indicates potential ghost team members or unequal collaboration",
                        hiring_impact="Raises questions about team collaboration skills",
                        recommended_action="Investigate team dynamics and individual contributions",
                    )
                )
                self.logger.warning(
                    "extreme_imbalance_detected",
                    author=author,
                    percentage=round(percentage, 1),
                    commit_count=commit_count,
                )

        # 2. Check for significant imbalance (>70% but ≤80%)
        for author, percentage in workload_dist.items():
            if 70 < percentage <= 80:
                commit_count = int(percentage * len(commits) / 100)
                red_flags.append(
                    RedFlag(
                        flag_type="significant_imbalance",
                        severity=RedFlagSeverity.HIGH,
                        description=f"{author} contributed {percentage:.1f}% of commits",
                        evidence=f"{commit_count} out of {len(commits)} commits",
                        impact="Suggests uneven workload distribution",
                        hiring_impact="May indicate team coordination challenges",
                        recommended_action="Review team collaboration patterns",
                    )
                )
                self.logger.info(
                    "significant_imbalance_detected", author=author, percentage=round(percentage, 1)
                )

        # 3. Check for ghost contributors (0 commits)
        # Contributors who are listed but have no commits in the history
        commit_authors = {commit.author for commit in commits}
        for contributor in contributors:
            if contributor not in commit_authors:
                red_flags.append(
                    RedFlag(
                        flag_type="ghost_contributor",
                        severity=RedFlagSeverity.CRITICAL,
                        description=f"{contributor} is listed as a contributor but has 0 commits",
                        evidence="No commits found in repository history",
                        impact="Indicates non-participation or credit claiming without contribution",
                        hiring_impact="Disqualifies from team awards; raises ethical concerns",
                        recommended_action="Verify team roster and remove ghost contributors",
                    )
                )
                self.logger.warning("ghost_contributor_detected", contributor=contributor)

        # 4. Check for minimal contribution (≤2 commits in team of 3+)
        if len(contributors) >= 3:
            for author, percentage in workload_dist.items():
                commit_count = int(percentage * len(commits) / 100)
                if commit_count <= 2:
                    red_flags.append(
                        RedFlag(
                            flag_type="minimal_contribution",
                            severity=RedFlagSeverity.HIGH,
                            description=f"{author} only made {commit_count} commit(s)",
                            evidence=f"{commit_count} commits in team of {len(contributors)}",
                            impact="Indicates minimal participation in team project",
                            hiring_impact="Questions engagement and contribution level",
                            recommended_action="Verify individual's actual involvement",
                        )
                    )
                    self.logger.info(
                        "minimal_contribution_detected",
                        author=author,
                        commit_count=commit_count,
                        team_size=len(contributors),
                    )

        # 5. Check for unhealthy work patterns (>10 late-night commits per person)
        late_night_by_author: dict[str, int] = defaultdict(int)
        for commit in commits:
            hour = commit.timestamp.hour
            if 2 <= hour < 6:
                late_night_by_author[commit.author] += 1

        for author, count in late_night_by_author.items():
            if count > 10:
                red_flags.append(
                    RedFlag(
                        flag_type="unhealthy_work_patterns",
                        severity=RedFlagSeverity.MEDIUM,
                        description=f"{author} made {count} commits between 2am-6am",
                        evidence=f"{count} late-night commits",
                        impact="May indicate poor time management or unhealthy work habits",
                        hiring_impact="Raises concerns about work-life balance",
                        recommended_action="Encourage healthier work patterns",
                    )
                )
                self.logger.info(
                    "unhealthy_work_pattern_detected", author=author, late_night_commits=count
                )

        # 6. Check for history rewriting (>5 force pushes)
        # Note: Force pushes are difficult to detect from a cloned repository
        # because they rewrite history. We would need:
        # - GitHub API events (push events with "forced: true")
        # - Or reflog access (not available in fresh clones)
        #
        # For MVP, we detect potential history rewriting through commit patterns:
        # - Commits with identical timestamps (suspicious)
        # - Large gaps in commit sequence followed by many commits
        # - Commits that appear to be rebased (author date != commit date)

        # Detect suspicious commit patterns that might indicate history rewriting
        if len(commits) >= 10:
            # Check for commits with identical timestamps (within 1 second)
            timestamp_groups: dict[int, list[str]] = defaultdict(list)
            for commit in commits:
                timestamp_key = int(commit.timestamp.timestamp())
                timestamp_groups[timestamp_key].append(commit.short_hash)

            # If we have multiple groups with 3+ commits at the exact same time
            suspicious_groups = [
                (ts, hashes) for ts, hashes in timestamp_groups.items() if len(hashes) >= 3
            ]

            if len(suspicious_groups) >= 5:
                red_flags.append(
                    RedFlag(
                        flag_type="history_rewriting",
                        severity=RedFlagSeverity.HIGH,
                        description=f"Detected {len(suspicious_groups)} instances of multiple commits with identical timestamps",
                        evidence=f"{len(suspicious_groups)} suspicious commit groups suggesting history manipulation",
                        impact="May indicate force pushes to hide mistakes or rewrite history",
                        hiring_impact="Raises concerns about transparency and version control practices",
                        recommended_action="Review git history for force pushes and rebases",
                    )
                )
                self.logger.warning(
                    "potential_history_rewriting_detected", suspicious_groups=len(suspicious_groups)
                )

        # Log summary
        if red_flags:
            self.logger.info(
                "red_flags_detected",
                total_flags=len(red_flags),
                critical=sum(1 for f in red_flags if f.severity == RedFlagSeverity.CRITICAL),
                high=sum(1 for f in red_flags if f.severity == RedFlagSeverity.HIGH),
                medium=sum(1 for f in red_flags if f.severity == RedFlagSeverity.MEDIUM),
            )

        return red_flags

    def _analyze_commit_timing(self, commits: list[CommitInfo]) -> tuple[int, bool]:
        """Analyze commit timing patterns.

        Detects:
        - Late-night coding (2am-6am)
        - Panic pushes (>40% commits in final hour)

        Args:
            commits: List of commit information

        Returns:
            Tuple of (late_night_commit_count, panic_push_detected)
        """
        if not commits:
            return 0, False

        # Count late-night commits (2am-6am)
        late_night_count = 0
        for commit in commits:
            hour = commit.timestamp.hour
            if 2 <= hour < 6:
                late_night_count += 1

        # Detect panic pushes (>40% commits in final hour)
        # Sort commits by timestamp to find the most recent
        sorted_commits = sorted(commits, key=lambda c: c.timestamp)

        if len(sorted_commits) < 5:
            # Not enough commits to detect panic push pattern
            return late_night_count, False

        # Get the timestamp of the last commit (deadline proxy)
        last_commit_time = sorted_commits[-1].timestamp

        # Count commits in the final hour before last commit
        final_hour_commits = 0
        for commit in sorted_commits:
            time_diff = (last_commit_time - commit.timestamp).total_seconds()
            # If commit is within 1 hour (3600 seconds) of last commit
            if 0 <= time_diff <= 3600:
                final_hour_commits += 1

        # Calculate percentage of commits in final hour
        final_hour_percentage = final_hour_commits / len(commits)
        panic_push = final_hour_percentage > 0.40

        if late_night_count > 0 or panic_push:
            self.logger.info(
                "commit_timing_analysis",
                late_night_commits=late_night_count,
                final_hour_commits=final_hour_commits,
                final_hour_percentage=round(final_hour_percentage * 100, 1),
                panic_push_detected=panic_push,
            )

        return late_night_count, panic_push

    def _generate_individual_scorecards(
        self,
        commits: list[CommitInfo],
        contributors: list[str],
        workload_dist: dict[str, float],
        repo_data: RepoData,
    ) -> list[IndividualScorecard]:
        """Generate detailed scorecard for each contributor.

        Args:
            commits: List of commit information
            contributors: List of contributor names
            workload_dist: Workload distribution percentages
            repo_data: Repository data with file information

        Returns:
            List of individual scorecards
        """
        scorecards: list[IndividualScorecard] = []

        # Build file path list from repo_data
        all_files = [sf.path for sf in repo_data.source_files]

        for contributor in contributors:
            # Filter commits by this contributor
            contributor_commits = [c for c in commits if c.author == contributor]

            if not contributor_commits:
                continue

            # Calculate metrics
            commit_count = len(contributor_commits)
            lines_added = sum(c.insertions for c in contributor_commits)
            lines_deleted = sum(c.deletions for c in contributor_commits)

            # For MVP, use all files as files_touched
            # In production, would track per-commit file changes
            files_touched = all_files

            # Detect notable contributions (>500 insertions)
            notable = [
                f"{c.short_hash}: {c.message[:50]}"
                for c in contributor_commits
                if c.insertions > 500
            ]

            # Detect role and expertise from files and commits
            role = self._detect_role(contributor_commits, all_files)
            expertise = self._detect_expertise(contributor_commits, all_files)

            # Generate work style
            work_style = self._analyze_work_style(contributor_commits)

            # Generate strengths and weaknesses
            strengths, weaknesses, growth_areas = self._assess_contributor(
                contributor_commits, workload_dist.get(contributor, 0)
            )

            # Generate hiring signals
            hiring_signals = self._generate_hiring_signals(
                role, commit_count, lines_added, strengths, weaknesses
            )

            scorecard = IndividualScorecard(
                contributor_name=contributor,
                contributor_email="",  # Would need git config data
                role=role,
                expertise_areas=expertise,
                commit_count=commit_count,
                lines_added=lines_added,
                lines_deleted=lines_deleted,
                files_touched=files_touched,
                notable_contributions=notable,
                strengths=strengths,
                weaknesses=weaknesses,
                growth_areas=growth_areas,
                work_style=work_style,
                hiring_signals=hiring_signals,
            )

            scorecards.append(scorecard)

        return scorecards

    def _detect_role(self, commits: list[CommitInfo], files: list[str]) -> ContributorRole:
        """Detect contributor role from file patterns.

        Analyzes file extensions and paths to determine if contributor
        is backend, frontend, devops, or full-stack.

        Args:
            commits: Contributor's commits
            files: All files in repository

        Returns:
            Detected contributor role
        """
        if not files:
            return ContributorRole.UNKNOWN

        # Count file types
        backend_count = 0
        frontend_count = 0
        devops_count = 0

        backend_exts = {".py", ".java", ".go", ".rs", ".rb", ".php", ".cs", ".sql"}
        frontend_exts = {".js", ".jsx", ".ts", ".tsx", ".vue", ".html", ".css", ".scss", ".sass"}
        devops_files = {"dockerfile", "docker-compose", ".yml", ".yaml", "terraform", "jenkinsfile"}

        for file_path in files:
            file_lower = file_path.lower()

            # Check backend
            if any(file_path.endswith(ext) for ext in backend_exts):
                backend_count += 1

            # Check frontend
            if any(file_path.endswith(ext) for ext in frontend_exts):
                frontend_count += 1

            # Check devops
            if any(keyword in file_lower for keyword in devops_files):
                devops_count += 1

        # Determine role based on file distribution
        total = backend_count + frontend_count + devops_count
        if total == 0:
            return ContributorRole.UNKNOWN

        # Full-stack if working in 3+ domains
        domains = sum([backend_count > 0, frontend_count > 0, devops_count > 0])

        if domains >= 3:
            return ContributorRole.FULL_STACK

        # Determine primary role
        if backend_count > frontend_count and backend_count > devops_count:
            return ContributorRole.BACKEND
        elif frontend_count > backend_count and frontend_count > devops_count:
            return ContributorRole.FRONTEND
        elif devops_count > 0:
            return ContributorRole.DEVOPS
        elif backend_count > 0 and frontend_count > 0:
            return ContributorRole.FULL_STACK

        return ContributorRole.UNKNOWN

    def _detect_expertise(self, commits: list[CommitInfo], files: list[str]) -> list[ExpertiseArea]:
        """Identify expertise areas from file patterns and commit messages.

        Analyzes file types and commit messages to detect expertise in
        database, security, testing, API, UI/UX, and infrastructure.

        Args:
            commits: Contributor's commits
            files: All files in repository

        Returns:
            List of detected expertise areas
        """
        expertise: set[ExpertiseArea] = set()

        # Analyze files for expertise signals
        for file_path in files:
            file_lower = file_path.lower()

            # Database expertise
            if any(
                keyword in file_lower
                for keyword in [
                    "database",
                    "db",
                    "migration",
                    "schema",
                    ".sql",
                    "postgres",
                    "mysql",
                    "mongo",
                ]
            ):
                expertise.add(ExpertiseArea.DATABASE)

            # Security expertise
            if any(
                keyword in file_lower
                for keyword in ["auth", "security", "crypto", "jwt", "oauth", "permission", "rbac"]
            ):
                expertise.add(ExpertiseArea.SECURITY)

            # Testing expertise
            if any(
                keyword in file_lower
                for keyword in ["test", "spec", "__test__", ".test.", ".spec.", "pytest", "jest"]
            ):
                expertise.add(ExpertiseArea.TESTING)

            # API expertise
            if any(
                keyword in file_lower
                for keyword in ["api", "endpoint", "route", "controller", "graphql", "rest"]
            ):
                expertise.add(ExpertiseArea.API)

            # UI/UX expertise
            if any(
                keyword in file_lower
                for keyword in [
                    "component",
                    "ui",
                    "ux",
                    "style",
                    "theme",
                    "design",
                    ".css",
                    ".scss",
                ]
            ):
                expertise.add(ExpertiseArea.UI_UX)

            # Infrastructure expertise
            if any(
                keyword in file_lower
                for keyword in [
                    "docker",
                    "kubernetes",
                    "k8s",
                    "terraform",
                    "ci",
                    "cd",
                    "deploy",
                    "infra",
                ]
            ):
                expertise.add(ExpertiseArea.INFRASTRUCTURE)

        # Analyze commit messages for additional signals
        for commit in commits:
            msg_lower = commit.message.lower()

            if any(
                keyword in msg_lower for keyword in ["database", "migration", "schema", "query"]
            ):
                expertise.add(ExpertiseArea.DATABASE)

            if any(
                keyword in msg_lower for keyword in ["security", "auth", "vulnerability", "fix cve"]
            ):
                expertise.add(ExpertiseArea.SECURITY)

            if any(
                keyword in msg_lower for keyword in ["test", "testing", "coverage", "unit test"]
            ):
                expertise.add(ExpertiseArea.TESTING)

            if any(keyword in msg_lower for keyword in ["api", "endpoint", "rest", "graphql"]):
                expertise.add(ExpertiseArea.API)

            if any(
                keyword in msg_lower for keyword in ["ui", "ux", "design", "style", "component"]
            ):
                expertise.add(ExpertiseArea.UI_UX)

            if any(
                keyword in msg_lower for keyword in ["docker", "deploy", "ci/cd", "infrastructure"]
            ):
                expertise.add(ExpertiseArea.INFRASTRUCTURE)

        return list(expertise)

    def _analyze_work_style(self, commits: list[CommitInfo]) -> WorkStyle:
        """Analyze work style patterns from commits."""
        if not commits:
            return WorkStyle(
                commit_frequency="infrequent",
                avg_commit_size=0,
                active_hours=[],
                late_night_commits=0,
                weekend_commits=0,
            )

        # Calculate average commit size
        avg_size = sum(c.insertions + c.deletions for c in commits) // len(commits)

        # Determine commit frequency
        if len(commits) > 20:
            frequency = "frequent"
        elif len(commits) > 5:
            frequency = "moderate"
        else:
            frequency = "infrequent"

        # Extract active hours
        active_hours = list({c.timestamp.hour for c in commits})

        # Count late-night commits (2am-6am)
        late_night = sum(1 for c in commits if 2 <= c.timestamp.hour < 6)

        # Count weekend commits
        weekend = sum(1 for c in commits if c.timestamp.weekday() >= 5)

        return WorkStyle(
            commit_frequency=frequency,
            avg_commit_size=avg_size,
            active_hours=sorted(active_hours),
            late_night_commits=late_night,
            weekend_commits=weekend,
        )

    def _assess_contributor(
        self, commits: list[CommitInfo], workload_percentage: float
    ) -> tuple[list[str], list[str], list[str]]:
        """Assess contributor strengths, weaknesses, and growth areas."""
        strengths: list[str] = []
        weaknesses: list[str] = []
        growth_areas: list[str] = []

        # Assess based on commit count
        if len(commits) > 20:
            strengths.append("High commit frequency shows consistent contribution")
        elif len(commits) < 3:
            weaknesses.append("Low commit count suggests limited participation")

        # Assess based on workload
        if 20 <= workload_percentage <= 40:
            strengths.append("Balanced workload contribution")
        elif workload_percentage > 70:
            weaknesses.append("Carrying majority of workload may indicate team imbalance")
        elif workload_percentage < 10:
            weaknesses.append("Minimal contribution to team effort")

        # Assess commit messages
        descriptive_msgs = sum(
            1
            for c in commits
            if len(c.message.split()) > 3
            and not c.message.lower().startswith(("fix", "update", "wip"))
        )
        if descriptive_msgs / len(commits) > 0.7:
            strengths.append("Clear, descriptive commit messages")
        else:
            growth_areas.append("Improve commit message quality and documentation")

        return strengths, weaknesses, growth_areas

    def _generate_hiring_signals(
        self,
        role: ContributorRole,
        commit_count: int,
        lines_added: int,
        strengths: list[str],
        weaknesses: list[str],
    ) -> HiringSignals:
        """Generate hiring recommendations based on contribution patterns."""
        # Determine seniority based on commit patterns
        if commit_count > 30 and lines_added > 5000:
            seniority = "senior"
            salary_range = "$120k-$160k"
        elif commit_count > 15 and lines_added > 2000:
            seniority = "mid"
            salary_range = "$80k-$120k"
        else:
            seniority = "junior"
            salary_range = "$60k-$90k"

        # Determine if must-interview
        must_interview = len(strengths) > len(weaknesses) and commit_count > 10

        # Generate rationale
        rationale = f"Based on {commit_count} commits and {lines_added} lines added. "
        if strengths:
            rationale += f"Key strengths: {', '.join(strengths[:2])}."

        return HiringSignals(
            recommended_role=role.value if role != ContributorRole.UNKNOWN else "general",
            seniority_level=seniority,
            salary_range_usd=salary_range,
            must_interview=must_interview,
            sponsor_interest=[],
            rationale=rationale,
        )

    def _calculate_commit_message_quality(self, commits: list[CommitInfo]) -> float:
        """Calculate percentage of descriptive commit messages.

        Descriptive = >3 words and not starting with fix/update/wip
        """
        if not commits:
            return 0.0

        descriptive_count = sum(
            1
            for commit in commits
            if len(commit.message.split()) > 3
            and not commit.message.lower().startswith(("fix", "update", "wip"))
        )

        return descriptive_count / len(commits)

    def _calculate_team_grade(
        self,
        workload_dist: dict[str, float],
        collab_patterns: list[CollaborationPattern],
        msg_quality: float,
        red_flags: list[RedFlag],
    ) -> str:
        """Calculate team dynamics grade (A-F).

        Scoring:
        - Workload balance: 0-30 points
        - Collaboration quality: 0-30 points
        - Communication (commit messages): 0-20 points
        - Time management: 0-20 points
        """
        score = 0

        # Workload balance (0-30 points)
        if workload_dist:
            max_percentage = max(workload_dist.values())
            if max_percentage <= 40:
                score += 30  # Perfect balance
            elif max_percentage <= 50:
                score += 25
            elif max_percentage <= 60:
                score += 20
            elif max_percentage <= 70:
                score += 15
            elif max_percentage <= 80:
                score += 10
            else:
                score += 5  # Extreme imbalance

        # Collaboration quality (0-30 points)
        positive_patterns = sum(1 for p in collab_patterns if p.positive)
        if positive_patterns > 0:
            score += 30
        elif len(workload_dist) > 1:
            score += 15  # Multiple contributors but no clear patterns

        # Communication quality (0-20 points)
        score += int(msg_quality * 20)

        # Time management (0-20 points) - deduct for red flags
        time_score = 20
        for flag in red_flags:
            if flag.flag_type in ["panic_push", "unhealthy_work_patterns"]:
                time_score -= 10
        score += max(0, time_score)

        # Convert to letter grade
        if score >= 90:
            return "A"
        elif score >= 80:
            return "B"
        elif score >= 70:
            return "C"
        elif score >= 60:
            return "D"
        else:
            return "F"
