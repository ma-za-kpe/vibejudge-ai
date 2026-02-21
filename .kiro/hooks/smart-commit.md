# Smart Commit Hook

## Trigger
**Event:** Manual invocation (not automatic)
**Command:** User triggers this hook when ready to commit

## Action
Intelligently analyze staged changes, run tests, and create a well-formatted conventional commit if tests pass.

## Instructions
When invoked, perform the following steps:

1. **Check for staged changes:**
   ```bash
   git diff --cached --name-only
   ```
   - If no changes staged, prompt user to stage changes first
   - If changes exist, continue to next step

2. **Run test suite:**
   ```bash
   pytest tests/ -v
   ```
   - If tests fail, report failures and **stop** (do not commit)
   - If tests pass, continue to next step

3. **Analyze changes and generate commit message:**
   - Review all staged changes
   - Identify the type of change:
     - `feat`: New feature
     - `fix`: Bug fix
     - `refactor`: Code refactoring
     - `test`: Adding/updating tests
     - `docs`: Documentation changes
     - `chore`: Build/tooling changes
     - `perf`: Performance improvements
   - Identify the scope (e.g., `agents`, `api`, `models`, `infrastructure`)
   - Write a concise subject line (max 72 characters)
   - Write a detailed body explaining:
     - What changed and why
     - Any breaking changes
     - Related issues or PRs

4. **Format commit message** (Conventional Commits):
   ```
   <type>(<scope>): <subject>

   <body>
   ```

5. **Create the commit:**
   ```bash
   git commit -m "$(cat <<'EOF'
   <generated message>
   EOF
   )"
   ```

6. **Report success:**
   - Show commit hash
   - Display git log summary
   - Suggest next steps (push, continue working, etc.)

## Example

**Staged changes:**
```
src/agents/bug_hunter.py
tests/unit/test_agents.py
```

**Generated commit:**
```
feat(agents): implement BugHunter agent with Nova Lite

- Add BugHunter agent class with code quality scoring
- Integrate Amazon Bedrock Nova Lite model for cost efficiency
- Implement evidence collection with file:line citations
- Add comprehensive test coverage with mocked Bedrock responses
- Configure agent for $0.002 per repo analysis cost

Tests: 47 passed in 3.2s
```

## Error Handling

**If tests fail:**
```
❌ Tests failed - commit aborted

Failed tests:
  - tests/unit/test_agents.py::test_bug_hunter_validates_evidence FAILED
  - tests/unit/test_agents.py::test_bug_hunter_handles_errors FAILED

Fix the failing tests before committing.
```

**If no changes staged:**
```
⚠️  No changes staged

Stage your changes first:
  git add <files>

Then run this hook again.
```

## Benefits
- **Saves time** on writing commit messages (5-10 min per commit)
- **Enforces quality** by running tests before every commit
- **Maintains consistency** with conventional commit format
- **Creates helpful history** with detailed commit messages
- **Prevents broken commits** from entering the repository

## Configuration
- **Manual trigger only** (prevents accidental commits)
- **Requires tests to pass** before committing
- **Uses conventional commits** format
