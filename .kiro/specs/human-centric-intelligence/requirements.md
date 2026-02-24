# Requirements Document: Human-Centric Intelligence Enhancement

## Introduction

VibeJudge AI currently functions as a code auditor - analyzing repositories using 4 AI agents and returning technical scores with evidence. This feature transforms VibeJudge from a code auditor into a human-centric hackathon intelligence platform by adding two critical enhancement layers:

1. **Technical Foundation (Hybrid Architecture)**: Integrate free static analysis tools, deep CI/CD analysis, and actual test execution to reduce AI costs by 42% while increasing findings by 3x
2. **Human Intelligence Layer**: Add team dynamics analysis, individual contributor recognition, strategic thinking detection, and brand voice transformation to provide organizers with hiring intelligence and participants with personalized growth feedback

This paradigm shift addresses the fundamental gap: hackathons are about PEOPLE learning and collaborating, not just code quality scores.

## Glossary

- **VibeJudge_System**: The complete hackathon judging platform including API, analysis engine, and AI agents
- **Static_Analysis_Engine**: Module that runs free open-source code analysis tools (Flake8, ESLint, Bandit, etc.)
- **Team_Analyzer**: Module that extracts team dynamics, collaboration patterns, and individual contributions from git history
- **Strategy_Detector**: Module that understands the "why" behind technical decisions, not just the "what"
- **Brand_Voice_Transformer**: Module that converts cold technical findings into warm, educational mentorship feedback
- **Organizer_Intelligence_Dashboard**: Aggregated insights for hackathon organizers including hiring signals, technology trends, and prize recommendations
- **Evidence**: Specific file:line citations with code examples that support findings
- **Hybrid_Architecture**: Analysis approach combining free static tools (60% of findings, $0 cost) with AI agents (40% of findings, strategic analysis)
- **Individual_Contributor_Scorecard**: Detailed assessment of each team member's contributions, expertise, strengths, weaknesses, and hiring signals
- **Red_Flag**: Concerning pattern in team behavior (e.g., toxic dynamics, ghost contributors, security violations)
- **Strategic_Thinking**: Understanding the reasoning behind technical choices (e.g., why integration tests over unit tests)
- **Hiring_Signal**: Indicator of skill level, expertise area, or seniority based on code patterns and collaboration behavior

## Requirements

### Requirement 1: Static Analysis Tool Integration

**User Story:** As a platform operator, I want to integrate free static analysis tools, so that I can reduce AI costs while catching more issues.

#### Acceptance Criteria

1. WHEN a Python repository is analyzed, THE Static_Analysis_Engine SHALL run Flake8, Bandit, Safety, and Radon
2. WHEN a JavaScript/TypeScript repository is analyzed, THE Static_Analysis_Engine SHALL run ESLint, npm audit, and Prettier
3. WHEN a Go repository is analyzed, THE Static_Analysis_Engine SHALL run go vet and staticcheck
4. WHEN a Rust repository is analyzed, THE Static_Analysis_Engine SHALL run clippy and cargo audit
5. WHEN any static analysis tool times out after 60 seconds, THE Static_Analysis_Engine SHALL log the timeout and continue with remaining tools
6. WHEN a static analysis tool is not installed, THE Static_Analysis_Engine SHALL gracefully skip that tool and log a warning
7. THE Static_Analysis_Engine SHALL normalize findings from all tools into a consistent evidence format with file, line, severity, category, and recommendation fields
8. WHEN static analysis completes, THE Static_Analysis_Engine SHALL return total issue count, critical issue count, and list of tools successfully run
9. THE Static_Analysis_Engine SHALL complete all static analysis within 30 seconds for repositories under 10,000 lines of code
10. FOR ALL static analysis findings, THE VibeJudge_System SHALL validate that cited files and line numbers exist in the repository

### Requirement 2: CI/CD Deep Analysis

**User Story:** As a hackathon organizer, I want to understand CI/CD sophistication beyond just success rates, so that I can identify teams with production-ready practices.

#### Acceptance Criteria

1. WHEN GitHub Actions workflow runs exist, THE VibeJudge_System SHALL fetch build logs for the most recent 5 workflow runs
2. WHEN build logs contain test output, THE VibeJudge_System SHALL parse and extract test results including pass count, fail count, and test names
3. WHEN build logs contain linter output, THE VibeJudge_System SHALL extract specific linting errors with file and line numbers
4. WHEN workflow artifacts include coverage reports, THE VibeJudge_System SHALL download and parse coverage percentages by file
5. WHEN workflow YAML files exist, THE VibeJudge_System SHALL parse them to detect lint jobs, test jobs, build jobs, and deployment jobs
6. WHEN workflow YAML contains caching configuration, THE VibeJudge_System SHALL recognize this as a CI optimization signal
7. WHEN workflow YAML contains matrix builds, THE VibeJudge_System SHALL recognize this as advanced CI sophistication
8. THE VibeJudge_System SHALL calculate CI sophistication score based on: job types present, caching usage, matrix builds, and deployment automation
9. WHEN CI/CD analysis fails due to API rate limits, THE VibeJudge_System SHALL retry with exponential backoff up to 3 times
10. THE VibeJudge_System SHALL complete CI/CD deep analysis within 15 seconds per repository

### Requirement 3: Test Execution Engine

**User Story:** As a code quality analyst, I want to actually run tests instead of just checking if test files exist, so that I know if tests pass or fail.

#### Acceptance Criteria

1. WHEN a repository contains pytest.ini or setup.py with test dependencies, THE VibeJudge_System SHALL detect pytest as the test framework
2. WHEN a repository contains package.json with a test script, THE VibeJudge_System SHALL detect the JavaScript test framework (jest, mocha, vitest)
3. WHEN a repository contains go.mod, THE VibeJudge_System SHALL detect go test as the test framework
4. WHEN a test framework is detected, THE VibeJudge_System SHALL execute tests in a sandboxed environment with 60-second timeout
5. WHEN tests execute, THE VibeJudge_System SHALL capture JSON output including total tests, passed tests, failed tests, and skipped tests
6. WHEN tests fail, THE VibeJudge_System SHALL extract failing test names, error messages, and file locations
7. WHEN test execution includes coverage reporting, THE VibeJudge_System SHALL parse coverage percentages by file
8. IF test execution times out after 60 seconds, THEN THE VibeJudge_System SHALL terminate the process and mark tests as incomplete
9. IF test execution fails due to missing dependencies, THEN THE VibeJudge_System SHALL attempt to install dependencies once before retrying
10. THE VibeJudge_System SHALL store actual test pass rate (passed/total) instead of estimating test quality from file existence
11. FOR ALL test execution, THE VibeJudge_System SHALL run tests in isolated /tmp directory to prevent side effects

### Requirement 4: Team Dynamics Analysis

**User Story:** As a hackathon organizer, I want to understand team collaboration patterns, so that I can identify high-functioning teams and toxic dynamics.

#### Acceptance Criteria

1. WHEN a repository has multiple contributors, THE Team_Analyzer SHALL calculate workload distribution as percentage of commits per contributor
2. WHEN workload distribution shows one contributor with >80% of commits, THE Team_Analyzer SHALL flag this as "extreme imbalance" red flag
3. WHEN workload distribution shows one contributor with >70% of commits, THE Team_Analyzer SHALL flag this as "significant imbalance" warning
4. WHEN commit history shows alternating commits between two contributors, THE Team_Analyzer SHALL detect this as pair programming pattern
5. WHEN a team member is listed but has 0 commits, THE Team_Analyzer SHALL flag this as "ghost contributor" critical red flag
6. WHEN a team member has ≤2 commits in a team of 3+, THE Team_Analyzer SHALL flag this as "minimal contribution" warning
7. THE Team_Analyzer SHALL analyze commit timestamps to detect late-night coding patterns (commits between 2am-6am)
8. WHEN >40% of commits occur in the final hour before deadline, THE Team_Analyzer SHALL flag this as "panic push" time management issue
9. THE Team_Analyzer SHALL evaluate commit message quality by measuring percentage of descriptive messages (>3 words, not starting with "fix"/"update"/"wip")
10. THE Team_Analyzer SHALL calculate team dynamics grade (A-F) based on workload balance, communication quality, and collaboration patterns
11. FOR ALL team dynamics analysis, THE Team_Analyzer SHALL provide specific evidence with commit hashes and timestamps

### Requirement 5: Individual Contributor Recognition

**User Story:** As a hackathon participant, I want individual recognition for my contributions, so that I can showcase my specific skills and growth.

#### Acceptance Criteria

1. WHEN analyzing commits, THE Team_Analyzer SHALL detect contributor roles based on commit messages and file patterns (Backend, Frontend, DevOps, Full-Stack)
2. WHEN a contributor touches files in 3+ different domains, THE Team_Analyzer SHALL classify them as "Full-Stack"
3. THE Team_Analyzer SHALL identify expertise areas for each contributor based on file types and commit content (Database, Security, Testing, API, UI/UX)
4. THE Team_Analyzer SHALL generate notable contributions list for each contributor highlighting commits with >500 insertions or >10 files changed
5. THE Team_Analyzer SHALL detect work style patterns including commit frequency, commit size distribution, and active hours
6. THE Team_Analyzer SHALL identify growth indicators such as learning new technologies (detected from commit messages with "first", "learning", "trying")
7. THE Team_Analyzer SHALL generate individual strengths list based on code quality metrics, expertise areas, and collaboration patterns
8. THE Team_Analyzer SHALL generate individual weaknesses list based on red flags, code smells, and missing best practices
9. THE Team_Analyzer SHALL provide hiring signals for each contributor including recommended role, seniority level, and salary range estimate
10. THE Team_Analyzer SHALL generate Individual_Contributor_Scorecard for each team member with sections: role, expertise, notable contributions, strengths, weaknesses, growth areas, hiring signals
11. FOR ALL individual assessments, THE Team_Analyzer SHALL cite specific commits, files, and line numbers as evidence

### Requirement 6: Strategic Thinking Detection

**User Story:** As a hackathon mentor, I want to understand WHY teams made technical decisions, so that I can provide context-aware feedback instead of generic criticism.

#### Acceptance Criteria

1. WHEN analyzing test strategy, THE Strategy_Detector SHALL distinguish between unit tests, integration tests, and end-to-end tests
2. WHEN a team has more integration tests than unit tests, THE Strategy_Detector SHALL recognize this as "integration-focused strategy" and explain the strategic reasoning
3. WHEN tests focus on authentication or payment flows, THE Strategy_Detector SHALL recognize this as "critical path prioritization" and explain why this shows product thinking
4. WHEN a team has 0 tests but polished UI, THE Strategy_Detector SHALL recognize this as "demo-first strategy" and provide context-adjusted scoring
5. WHEN a team has low overall coverage but 100% coverage of critical paths, THE Strategy_Detector SHALL recognize this as "smart prioritization" and adjust score upward
6. WHEN analyzing architecture decisions, THE Strategy_Detector SHALL identify trade-offs such as "chose speed over security for demo" or "over-engineered for hackathon scope"
7. THE Strategy_Detector SHALL detect technology learning during hackathon by analyzing commit history for framework adoption patterns
8. THE Strategy_Detector SHALL provide strategic context for all scores explaining the reasoning behind technical choices
9. WHEN generating feedback, THE Strategy_Detector SHALL include "What this reveals about the team" section explaining maturity level and thinking patterns
10. FOR ALL strategic assessments, THE Strategy_Detector SHALL distinguish between junior patterns (tutorial-following) and senior patterns (production thinking)

### Requirement 7: Brand Voice Transformation

**User Story:** As a hackathon participant, I want encouraging, educational feedback instead of cold criticism, so that I can learn and grow from the experience.

#### Acceptance Criteria

1. WHEN generating feedback for security issues, THE Brand_Voice_Transformer SHALL start by acknowledging what the team did right before explaining the vulnerability
2. WHEN explaining vulnerabilities, THE Brand_Voice_Transformer SHALL provide context about why the issue is common in hackathons
3. WHEN providing fixes, THE Brand_Voice_Transformer SHALL include code examples showing both vulnerable and fixed versions with explanations
4. WHEN providing recommendations, THE Brand_Voice_Transformer SHALL include learning resources (links to documentation, tutorials, OWASP guides)
5. THE Brand_Voice_Transformer SHALL use warm, conversational language avoiding cold technical jargon where possible
6. THE Brand_Voice_Transformer SHALL celebrate achievements and strengths before discussing weaknesses
7. THE Brand_Voice_Transformer SHALL provide effort estimates ("5-minute fix") and difficulty levels ("Easy", "Moderate", "Advanced") for all recommendations
8. THE Brand_Voice_Transformer SHALL explain business impact of issues ("Checkout bugs = lost revenue") not just technical severity
9. THE Brand_Voice_Transformer SHALL frame weaknesses as "growth opportunities" with specific learning paths
10. THE Brand_Voice_Transformer SHALL maintain honesty while being encouraging (no false praise, but constructive criticism)
11. FOR ALL feedback, THE Brand_Voice_Transformer SHALL follow the pattern: Acknowledge → Explain Context → Show Fix → Explain Why → Provide Resources

### Requirement 8: Red Flag Detection

**User Story:** As a hackathon organizer, I want to identify toxic team dynamics and concerning patterns, so that I can provide appropriate interventions and avoid rewarding dysfunction.

#### Acceptance Criteria

1. WHEN one contributor has >80% of commits, THE Team_Analyzer SHALL flag "Extreme workload imbalance" with severity critical
2. WHEN a contributor has 0 commits but is listed on team, THE Team_Analyzer SHALL flag "Ghost contributor" with severity critical
3. WHEN git history shows force pushes >5 times, THE Team_Analyzer SHALL flag "History rewriting" with severity high
4. WHEN commit history shows secrets committed then force-pushed to hide, THE Team_Analyzer SHALL flag "Security incident cover-up" with severity critical
5. WHEN a contributor has >10 commits between 2am-6am, THE Team_Analyzer SHALL flag "Unhealthy work patterns" with severity medium
6. WHEN one contributor deletes another contributor's code without discussion, THE Team_Analyzer SHALL flag "Territorial behavior" with severity high
7. WHEN all commits go directly to main with no PRs or branches, THE Team_Analyzer SHALL flag "No code review culture" with severity medium
8. FOR ALL red flags, THE Team_Analyzer SHALL provide explanation of why it matters, impact on team health, and recommended actions
9. FOR ALL red flags, THE Team_Analyzer SHALL include hiring impact assessment explaining why this disqualifies from certain roles
10. WHEN critical red flags exist, THE Team_Analyzer SHALL recommend disqualification from team awards while allowing individual assessment

### Requirement 9: Organizer Intelligence Dashboard

**User Story:** As a hackathon organizer, I want aggregated insights across all submissions, so that I can identify hiring targets, technology trends, and make informed prize decisions.

#### Acceptance Criteria

1. THE Organizer_Intelligence_Dashboard SHALL aggregate top performers with team scores, key strengths, and sponsor interest flags
2. THE Organizer_Intelligence_Dashboard SHALL categorize hiring intelligence by role (Backend, Frontend, DevOps, Full-Stack) with must-interview candidates
3. THE Organizer_Intelligence_Dashboard SHALL provide technology trend analysis showing most-used technologies, emerging technologies, and popular stack combinations
4. THE Organizer_Intelligence_Dashboard SHALL identify common issues across submissions with percentages affected and workshop recommendations
5. THE Organizer_Intelligence_Dashboard SHALL highlight standout moments including most creative API use, best learning journey, and best collaboration
6. THE Organizer_Intelligence_Dashboard SHALL provide recommendations for next hackathon including needed workshops, technology focus, and prize category suggestions
7. THE Organizer_Intelligence_Dashboard SHALL generate sponsor follow-up actions including API usage statistics, feedback themes, and hiring leads
8. THE Organizer_Intelligence_Dashboard SHALL calculate infrastructure maturity metrics (CI/CD adoption, Docker usage, monitoring/logging adoption)
9. THE Organizer_Intelligence_Dashboard SHALL provide prize recommendations with justifications based on actual evidence not just scores
10. FOR ALL dashboard insights, THE Organizer_Intelligence_Dashboard SHALL include specific team examples and evidence

### Requirement 10: Cost Optimization Through Hybrid Architecture

**User Story:** As a platform operator, I want to reduce AI costs while improving analysis quality, so that the platform remains economically viable at scale.

#### Acceptance Criteria

1. THE VibeJudge_System SHALL run static analysis tools before AI agents to catch syntax errors, undefined variables, and common issues at $0 cost
2. THE VibeJudge_System SHALL reduce BugHunter agent scope to focus on logic bugs and edge cases, skipping syntax and import errors already caught by static tools
3. THE VibeJudge_System SHALL pass static analysis results as context to AI agents to avoid duplicate analysis
4. THE VibeJudge_System SHALL achieve 42% cost reduction from current $0.086 per repo to target $0.050 per repo
5. THE VibeJudge_System SHALL increase total findings by 3x through combination of static tools (60% of findings) and AI agents (40% of findings)
6. THE VibeJudge_System SHALL complete full analysis within 90 seconds per repository (vs current 75 seconds, allowing 15 seconds for static tools)
7. THE VibeJudge_System SHALL track cost breakdown showing static analysis cost ($0), AI agent costs by agent, and total cost per repository
8. WHEN static analysis finds >50 critical issues, THE VibeJudge_System SHALL prioritize top 20 for AI agent review to stay within token budget
9. THE VibeJudge_System SHALL maintain or improve evidence verification rate (target: 95%+ of citations are valid file:line references)
10. FOR ALL cost tracking, THE VibeJudge_System SHALL store per-agent token usage and cost in DynamoDB for dashboard reporting

### Requirement 11: Actionable Feedback Generation

**User Story:** As a hackathon participant, I want specific, actionable feedback with code examples, so that I can immediately improve my code and learn best practices.

#### Acceptance Criteria

1. WHEN generating feedback for each finding, THE VibeJudge_System SHALL include priority ranking (1-5 based on severity and business impact)
2. WHEN generating feedback, THE VibeJudge_System SHALL include effort estimate in minutes and difficulty level (Easy/Moderate/Advanced)
3. WHEN generating feedback for code issues, THE VibeJudge_System SHALL include current code snippet showing the problem
4. WHEN generating feedback for code issues, THE VibeJudge_System SHALL include fixed code snippet with inline comments explaining the changes
5. WHEN generating feedback, THE VibeJudge_System SHALL explain why the current approach is vulnerable or problematic
6. WHEN generating feedback, THE VibeJudge_System SHALL explain why the fixed approach solves the problem
7. WHEN generating feedback, THE VibeJudge_System SHALL include testing instructions to verify the fix works
8. WHEN generating feedback, THE VibeJudge_System SHALL include 2-3 learning resource links (documentation, tutorials, OWASP guides)
9. THE VibeJudge_System SHALL group related findings into themes (e.g., "Authentication Security" grouping SQL injection, password hashing, session management)
10. THE VibeJudge_System SHALL generate personalized learning roadmap for each team member based on their weaknesses and growth areas
11. FOR ALL actionable feedback, THE VibeJudge_System SHALL maintain warm, educational tone following Brand_Voice_Transformer guidelines

### Requirement 12: Evidence Validation and Verification

**User Story:** As a platform operator, I want to validate all evidence citations, so that we never provide hallucinated findings that destroy trust.

#### Acceptance Criteria

1. FOR ALL findings with file citations, THE VibeJudge_System SHALL verify the file exists in the repository
2. FOR ALL findings with line number citations, THE VibeJudge_System SHALL verify the line number is within the file's line count
3. WHEN a finding cites a file that doesn't exist, THE VibeJudge_System SHALL mark the finding as unverified and log an error
4. WHEN a finding cites a line number exceeding file length, THE VibeJudge_System SHALL mark the finding as unverified and log an error
5. THE VibeJudge_System SHALL calculate evidence verification rate as (verified findings / total findings) × 100
6. THE VibeJudge_System SHALL achieve minimum 95% evidence verification rate across all findings
7. WHEN evidence verification rate falls below 95%, THE VibeJudge_System SHALL log a critical alert for investigation
8. THE VibeJudge_System SHALL store verification status (verified/unverified) with each finding in DynamoDB
9. THE VibeJudge_System SHALL exclude unverified findings from final scorecard to prevent hallucinated evidence
10. FOR ALL evidence validation, THE VibeJudge_System SHALL perform validation before passing findings to Brand_Voice_Transformer

### Requirement 13: Parser and Pretty Printer for Analysis Results

**User Story:** As a system integrator, I want to parse analysis results from various tools into a consistent format and pretty-print them for debugging, so that I can ensure data quality and troubleshoot issues.

#### Acceptance Criteria

1. THE VibeJudge_System SHALL parse Flake8 JSON output into normalized evidence format with file, line, code, message, severity fields
2. THE VibeJudge_System SHALL parse Bandit JSON output into normalized evidence format with file, line, code, message, severity, CWE fields
3. THE VibeJudge_System SHALL parse ESLint JSON output into normalized evidence format with file, line, code, message, severity fields
4. THE VibeJudge_System SHALL parse pytest JSON output into normalized test results format with total, passed, failed, skipped fields
5. THE VibeJudge_System SHALL parse jest JSON output into normalized test results format with total, passed, failed, skipped fields
6. THE Pretty_Printer SHALL format normalized evidence back into human-readable markdown for debugging and logging
7. THE Pretty_Printer SHALL format Individual_Contributor_Scorecard into structured markdown with sections for role, expertise, contributions, strengths, weaknesses
8. THE Pretty_Printer SHALL format Organizer_Intelligence_Dashboard into structured markdown with sections for top performers, hiring intelligence, technology trends
9. FOR ALL parsing operations, THE VibeJudge_System SHALL handle malformed JSON gracefully by logging parse errors and continuing with remaining tools
10. FOR ALL parsed data, THE VibeJudge_System SHALL validate required fields exist before storing in database
11. THE VibeJudge_System SHALL implement round-trip property: parse(pretty_print(data)) SHALL produce equivalent data structure

## Non-Functional Requirements

### Performance Requirements

1. Static analysis SHALL complete within 30 seconds for repositories under 10,000 lines of code
2. CI/CD deep analysis SHALL complete within 15 seconds per repository
3. Test execution SHALL timeout after 60 seconds to prevent blocking
4. Team dynamics analysis SHALL complete within 10 seconds for repositories with <500 commits
5. Full hybrid analysis pipeline SHALL complete within 90 seconds per repository
6. The system SHALL support analyzing 50 repositories in parallel without degradation
7. The system SHALL maintain <200ms API response time for non-analysis endpoints

### Cost Requirements

1. The system SHALL reduce per-repository analysis cost from $0.086 to $0.050 (42% reduction)
2. The system SHALL achieve cost reduction while maintaining or improving analysis quality
3. The system SHALL track and report cost breakdown by analysis phase (static: $0, AI: $0.050)
4. The system SHALL stay within AWS Free Tier limits for all services except Bedrock
5. The system SHALL optimize AI agent token usage by providing pre-filtered context from static analysis

### Security Requirements

1. Test execution SHALL run in isolated sandboxed environment with no network access
2. Test execution SHALL use separate /tmp directory per repository to prevent cross-contamination
3. Test execution SHALL terminate processes after 60-second timeout to prevent resource exhaustion
4. Static analysis tools SHALL not execute arbitrary code from repositories
5. The system SHALL sanitize all file paths before executing shell commands to prevent injection attacks
6. The system SHALL validate all tool outputs before parsing to prevent malicious JSON injection
7. Red flag detection SHALL identify and report security incidents (committed secrets, force-push cover-ups)

### Reliability Requirements

1. Static analysis SHALL gracefully handle missing tools by logging warnings and continuing
2. Static analysis SHALL gracefully handle tool timeouts by logging and continuing with remaining tools
3. CI/CD analysis SHALL retry failed API calls with exponential backoff up to 3 times
4. Test execution SHALL handle missing dependencies by attempting one install before failing
5. The system SHALL maintain 95%+ evidence verification rate to prevent hallucinated findings
6. The system SHALL log all errors with structured context for debugging
7. The system SHALL continue analysis even if individual components fail (graceful degradation)

### Usability Requirements

1. Feedback SHALL use warm, educational tone instead of cold technical criticism
2. Feedback SHALL include code examples showing both problem and solution
3. Feedback SHALL include effort estimates and difficulty levels for all recommendations
4. Feedback SHALL provide learning resources (documentation links, tutorials)
5. Individual scorecards SHALL be honest about strengths and weaknesses without false praise
6. Organizer dashboard SHALL provide actionable insights not just statistics
7. All findings SHALL include specific evidence with file:line citations

### Maintainability Requirements

1. Static analysis tools SHALL be optional dependencies with graceful degradation if not installed
2. New static analysis tools SHALL be addable without modifying core analysis logic
3. Evidence format SHALL be normalized across all tools for consistent processing
4. All modules SHALL follow single responsibility principle (Team_Analyzer, Strategy_Detector, Brand_Voice_Transformer as separate modules)
5. All modules SHALL have comprehensive type hints for maintainability
6. All modules SHALL have structured logging with context for debugging
7. The system SHALL follow existing project structure with no circular imports

## Dependencies and Constraints

### External Dependencies

1. Static analysis tools: Flake8, Bandit, Safety, Mypy, ESLint, npm audit, Radon, Lizard (all optional)
2. Test frameworks: pytest, jest, mocha, vitest, go test (detected automatically)
3. GitHub API for CI/CD data (existing dependency)
4. Amazon Bedrock for AI agents (existing dependency)
5. DynamoDB for data storage (existing dependency)

### Technical Constraints

1. Must stay within AWS Lambda 15-minute timeout limit
2. Must stay within Lambda /tmp storage limit (2GB configured)
3. Must stay within AWS Free Tier for all services except Bedrock
4. Must maintain backward compatibility with existing API contracts
5. Must follow project structure with no circular imports (utils → models → services → agents → api)
6. Must use Python 3.12 with type hints required
7. Must use Pydantic v2 for all data models

### Business Constraints

1. Must reduce costs while improving quality (cannot increase per-repo cost)
2. Must complete analysis within 30 minutes for 50 repositories (organizer expectation)
3. Must maintain 95%+ evidence verification rate (trust requirement)
4. Must provide value to three stakeholders: organizers (hiring intelligence), participants (growth feedback), sponsors (API insights)
5. Must differentiate from competitors (first platform with human-centric intelligence)

## Success Metrics

### Technical Metrics

1. Cost reduction: 42% (from $0.086 to $0.050 per repo)
2. Findings increase: 3x (from ~15 to ~45 findings per repo)
3. Evidence verification rate: ≥95%
4. Analysis time: ≤90 seconds per repo
5. Static analysis coverage: 11+ tools integrated
6. Test execution success rate: ≥80% (tests run successfully when framework detected)

### Business Metrics

1. Organizer satisfaction: Hiring intelligence provided for ≥80% of teams
2. Participant satisfaction: Individual scorecards generated for ≥90% of contributors
3. Sponsor value: API usage insights and hiring leads provided for all sponsors
4. Differentiation: First platform with team dynamics analysis and individual recognition
5. Scalability: Support 500 repositories in <2 hours (vs 3 days manual judging)

### Quality Metrics

1. Red flag detection: ≥90% of toxic patterns identified
2. Strategic thinking recognition: Context provided for ≥80% of technical decisions
3. Brand voice consistency: ≥95% of feedback follows warm, educational tone
4. Actionable feedback: ≥90% of findings include code examples and learning resources
5. Round-trip property: parse(pretty_print(data)) produces equivalent structure for all data types
