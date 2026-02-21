# VibeJudge AI — Architecture Decision Records (ADRs)

> **Version:** 1.0  
> **Date:** February 2026  
> **Author:** Maku Mazakpe / Vibe Coders  
> **Status:** APPROVED — All decisions locked for MVP build  
> **Competition:** AWS 10,000 AIdeas (Semi-Finalist)

---

## ADR Index

| # | Decision | Status | Impact |
|---|----------|--------|--------|
| 001 | Bedrock Converse API over Bedrock Agents | ✅ Accepted | Critical — Core AI architecture |
| 002 | AWS SAM over CDK for IaC | ✅ Accepted | High — Deployment pipeline |
| 003 | FastAPI + Mangum on Lambda | ✅ Accepted | High — API layer |
| 004 | Single-Table DynamoDB Design | ✅ Accepted | High — Data layer |
| 005 | httpx over PyGithub for GitHub API | ✅ Accepted | Medium — GitHub integration |
| 006 | Post-Submission Batch Analysis Model | ✅ Accepted | Critical — Cost/architecture |
| 007 | Python Monorepo with SAM | ✅ Accepted | Medium — Project structure |
| 008 | Converse API with Manual Orchestration | ✅ Accepted | High — Agent coordination |
| 009 | GitPython + Ephemeral /tmp for Repo Cloning | ✅ Accepted | Medium — Git analysis |
| 010 | Structured JSON Scoring Output | ✅ Accepted | Medium — Scorecard format |
| 011 | CloudWatch Native over Third-Party Observability | ✅ Accepted | Medium — Monitoring |
| 012 | No Frontend for MVP — API-First | ✅ Accepted | High — Scope control |

---

## ADR-001: Bedrock Converse API over Bedrock Agents

### Status
Accepted

### Context
VibeJudge AI uses a multi-agent system with 4 specialized AI judges (BugHunter, PerformanceAnalyzer, InnovationScorer, AI Detection). We need to decide between:

- **Option A — Amazon Bedrock Agents (Managed):** AWS-managed agent framework with supervisor/sub-agent routing, action groups backed by Lambda functions, and built-in conversation memory.
- **Option B — Amazon Bedrock Converse API (Direct):** We build a lightweight Python orchestrator that calls `bedrock-runtime.converse()` directly with specialized system prompts per agent.

### Decision
**Option B — Bedrock Converse API with manual orchestration.**

### Rationale

**1. Token Cost Transparency (Critical for our billing intelligence layer)**
The Converse API returns `usage.inputTokens`, `usage.outputTokens`, and `usage.totalTokens` in every single response. We capture these directly and log them to DynamoDB per agent, per submission. With Bedrock Agents, the managed orchestration makes multiple internal model calls (planning, routing, tool use, summarization) — a single user query can consume 5-10x more tokens than expected, and we don't get per-step token breakdowns. Since our entire LLM Billing Intelligence Layer depends on granular cost tracking, the Converse API is the only option that gives us the data we need.

**2. Model Flexibility**
The Converse API is model-agnostic — same code works with Claude Sonnet, Nova Lite, Nova Micro. We switch models per agent with a single `modelId` parameter change:
```python
# BugHunter uses cheap Nova Lite
response = client.converse(modelId="amazon.nova-lite-v1:0", ...)

# InnovationScorer uses Claude Sonnet for deeper reasoning
response = client.converse(modelId="anthropic.claude-sonnet-4-20250514", ...)
```
With Bedrock Agents, the model is bound to the agent at creation time and changing it requires API calls to update the agent configuration.

**3. Simpler Lambda Architecture**
Bedrock Agents require each tool to be a separate Lambda function with specific input/output schemas. For 4 agents with 2-3 tools each, that's 8-12 Lambda functions plus the orchestration overhead. With the Converse API, our entire analysis pipeline is a single Lambda function that calls the Bedrock API 4-5 times sequentially.

**4. Debugging and Reproducibility**
With direct Converse API calls, we control exactly what goes in (system prompt + repo data) and what comes out (scored JSON). We can log, replay, and unit-test every agent call. Bedrock Agents add an opaque orchestration layer that makes debugging harder.

**5. Cold Start Performance**
Bedrock Agents add latency — the supervisor must plan, route, and aggregate. For batch post-submission analysis, latency per submission is less critical, but when we process 500 submissions, even 5 extra seconds per submission adds 40+ minutes to total analysis time.

**6. Competition Narrative**
We can still tell the "multi-agent system on Bedrock" story in the article. The architecture IS multi-agent — we're just orchestrating in application code rather than the managed framework. We mention Bedrock Agents as the production roadmap for when we need real-time conversational agents in the premium tier.

### Consequences
- **Positive:** Full token tracking, model flexibility, simpler code, easier debugging, lower costs.
- **Negative:** We own the orchestration logic (routing, aggregation, error handling). More code to write and maintain.
- **Migration Path:** The agent prompts and scoring schemas are designed to be portable. Moving to Bedrock Agents later means wrapping each agent function as a Lambda tool and creating agent definitions — no prompt rewrite needed.

### References
- [Bedrock Converse API — boto3 docs](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/bedrock-runtime/client/converse.html)
- [Bedrock Agents multi-agent collaboration](https://aws.amazon.com/blogs/machine-learning/design-multi-agent-orchestration-with-reasoning-using-amazon-bedrock-and-open-source-frameworks/)
- [invoke_model serviceTier parameter](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/bedrock-runtime/client/invoke_model.html) — supports `flex` tier for batch discounts

---

## ADR-002: AWS SAM over CDK for Infrastructure as Code

### Status
Accepted

### Context
We need Infrastructure as Code to define and deploy: Lambda functions, API Gateway (HTTP API), DynamoDB table, S3 bucket, CloudWatch alarms, IAM roles. Options:

- **AWS SAM** — YAML-based, purpose-built for serverless, extends CloudFormation.
- **AWS CDK** — Python-based, general-purpose, compiles to CloudFormation.
- **Serverless Framework** — Third-party, YAML-based, multi-cloud support.
- **Terraform** — Third-party, HCL-based, multi-cloud.

### Decision
**AWS SAM.**

### Rationale

**1. Purpose-Built for Our Exact Stack**
SAM has first-class support for Lambda + API Gateway + DynamoDB — exactly our stack. The `AWS::Serverless::Function` resource type reduces Lambda definitions from ~40 lines of CloudFormation to ~15 lines of SAM. API Gateway event sources are defined inline with the function.

**2. Local Testing**
`sam local invoke` and `sam local start-api` let us test Lambda functions locally before deploying. CDK requires `cdk synth` + SAM CLI as a secondary tool to achieve the same thing. SAM does it natively.

**3. Faster to Build**
For an MVP with 2-3 Lambda functions, 1 DynamoDB table, 1 S3 bucket, and 1 HTTP API, SAM is faster. CDK shines for complex infrastructure with mixed resources (EC2, RDS, VPCs) — we don't have that. Our entire infrastructure fits in a single `template.yaml` under 200 lines.

**4. AWS Competition Alignment**
SAM is an AWS-native tool. The competition judges understand SAM templates. The article can show the full `template.yaml` and readers can deploy it themselves.

**5. Claude Code Compatibility**
Claude Code can generate SAM YAML templates very effectively — it's declarative and well-documented. CDK Python code has more surface area for errors (imports, construct IDs, prop objects).

### Consequences
- **Positive:** Fast iteration, local testing, readable templates, competition-friendly.
- **Negative:** Less expressive than CDK for complex logic (no loops, conditionals). If we need to add non-serverless resources later (e.g., OpenSearch for Knowledge Bases), CDK would be more appropriate.
- **Migration Path:** SAM templates are CloudFormation-compatible. CDK can import existing CloudFormation resources. Migration to CDK is incremental if needed post-MVP.

### References
- [AWS SAM Developer Guide](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/)
- [SAM vs CDK comparison](https://aws.amazon.com/cdk/faqs/) — "If you prefer defining your serverless infrastructure in concise declarative templates, SAM is the better fit."

---

## ADR-003: FastAPI + Mangum on Lambda

### Status
Accepted

### Context
We need an API layer to handle: hackathon configuration, analysis triggering, result retrieval, GitHub webhooks, cost estimates. Options:

- **FastAPI + Mangum** — Full ASGI framework wrapped for Lambda via Mangum adapter.
- **Raw Lambda handlers** — Direct `def handler(event, context)` functions per endpoint.
- **Flask + Zappa** — Older WSGI approach.
- **API Gateway direct integrations** — No Lambda at all; API Gateway talks directly to DynamoDB/S3.

### Decision
**FastAPI + Mangum as a single Lambda function behind API Gateway HTTP API.**

### Rationale

**1. Auto-Generated OpenAPI Docs**
FastAPI generates Swagger/OpenAPI docs at `/docs` automatically. This is critical for the competition article — we get a professional interactive API explorer for free. It also serves as living API documentation.

**2. Pydantic Validation**
Request/response validation via Pydantic models. When an organizer submits a hackathon config, Pydantic validates the rubric schema, repo URLs, agent selection — before any processing begins. This eliminates an entire class of bugs.

**3. Dependency Injection**
FastAPI's DI system lets us inject Bedrock clients, DynamoDB resources, and configuration cleanly:
```python
async def get_bedrock_client():
    return boto3.client("bedrock-runtime", region_name="us-east-1")

@router.post("/analyze")
async def analyze(config: HackathonConfig, bedrock=Depends(get_bedrock_client)):
    ...
```
This makes testing trivial — inject mock clients in tests.

**4. Mangum Is Production-Proven**
Mangum wraps FastAPI as a Lambda handler with one line: `handler = Mangum(app)`. It handles API Gateway HTTP API events, REST API events, ALB events, and Function URLs. The package is 50KB, actively maintained, and used in production by thousands of projects.

**5. Single Lambda for All Routes**
All API routes live in one Lambda function. API Gateway proxies `/{proxy+}` to it. This means one cold start covers all endpoints. For our low-traffic MVP, this is more cost-effective than per-route Lambda functions.

### Consequences
- **Positive:** OpenAPI docs, validation, DI, proven pattern, developer-friendly.
- **Negative:** Single Lambda means cold starts affect all endpoints. Package size is larger than raw handlers (~5-10MB with dependencies). 
- **Cold Start Mitigation:** Configure Lambda with 1GB memory (which proportionally increases CPU), keep dependencies lean, use `--exclude boto3` in packaging since Lambda runtime already includes it.

### References
- [Mangum documentation](https://mangum.fastapiexpert.com/)
- [Mangum GitHub](https://github.com/Kludex/mangum) — ASGI adapter for Lambda
- [FastAPI serverless patterns](https://circleci.com/blog/building-a-serverless-genai-api/)

---

## ADR-004: Single-Table DynamoDB Design

### Status
Accepted

### Context
VibeJudge needs to store: hackathon configurations, submission metadata, agent scorecards, cost tracking records, and organizer accounts. Options:

- **Single-table design** — All entities in one DynamoDB table with composite keys and GSIs.
- **Multi-table design** — Separate tables per entity type.

### Decision
**Single-table design with composite primary keys and 2 GSIs.**

### Rationale

**1. Access Pattern Alignment**
DynamoDB is optimized for known access patterns. Our patterns are:
- Get all submissions for a hackathon → `PK=HACK#<id>`, `SK begins_with SUB#`
- Get all scores for a submission → `PK=SUB#<id>`, `SK begins_with SCORE#`
- Get cost records for a hackathon → `PK=HACK#<id>`, `SK begins_with COST#`
- Get hackathon by organizer → GSI1: `GSI1PK=ORG#<id>`, `GSI1SK=HACK#<id>`
- Get recent hackathons → GSI2: `GSI2PK=STATUS#active`, `GSI2SK=<created_at>`

All of these map cleanly to a single-table design with partition key + sort key queries.

**2. Free Tier Efficiency**
DynamoDB free tier gives 25 RCU and 25 WCU — **total across the account, not per table.** With a single table, all capacity goes to one place. With 5 tables at 5 RCU/5 WCU each, we'd use 25 RCU/25 WCU and have zero headroom. Single table lets us allocate capacity more efficiently.

**3. Transactional Writes**
When an analysis completes, we need to write the scorecard AND update the submission status AND record cost data atomically. DynamoDB `TransactWriteItems` works across items in the same table efficiently. Cross-table transactions are possible but more expensive and complex.

**4. AWS Best Practice**
Amazon's own DynamoDB documentation and re:Invent talks consistently recommend single-table design for serverless applications. The data model document (Deliverable #3) will define the full entity schema.

### Consequences
- **Positive:** Free tier efficient, transactional, all access patterns served, one table to monitor.
- **Negative:** Entity relationships are harder to reason about visually. Queries require understanding the key schema. GSI costs count against free tier RCU/WCU.
- **Mitigation:** The data model document will include a clear entity-relationship diagram and access pattern table.

### Key Schema Preview
```
Table: VibeJudgeTable
PK (Partition Key)     | SK (Sort Key)              | Entity
-----------------------|----------------------------|--------
HACK#<hackathon_id>    | META                       | Hackathon config
HACK#<hackathon_id>    | SUB#<submission_id>        | Submission record
SUB#<submission_id>    | SCORE#<agent_name>         | Agent scorecard
SUB#<submission_id>    | COST#<agent_name>          | Cost record per agent
ORG#<organizer_id>     | PROFILE                    | Organizer account
HACK#<hackathon_id>    | COST#SUMMARY               | Hackathon cost summary
```

---

## ADR-005: httpx over PyGithub for GitHub API

### Status
Accepted

### Context
VibeJudge needs to call GitHub REST API v3 for: repository metadata, commit history, file contents, GitHub Actions workflow runs, workflow job details, and workflow logs. Options:

- **PyGithub** — Typed Python wrapper for GitHub API v3. 6.8k stars, actively maintained.
- **httpx** — Modern async HTTP client. We make direct REST calls.
- **requests** — Synchronous HTTP client. Industry standard.

### Decision
**httpx for direct GitHub REST API calls.**

### Rationale

**1. GitHub Actions API Coverage**
PyGithub doesn't fully cover the Actions API — particularly `GET /repos/{owner}/{repo}/actions/runs/{run_id}/logs` (download workflow logs) and some newer endpoints. Since Actions intelligence is a key differentiator for VibeJudge, we need full API access.

**2. Async Support**
httpx supports both sync and async. If we later move to async Lambda handlers or need concurrent API calls (fetching multiple repos simultaneously), httpx is ready. PyGithub is synchronous-only.

**3. Dependency Size**
In Lambda, every MB of dependencies adds to cold start time. httpx is ~70KB. PyGithub pulls in `requests`, `pyjwt`, `cryptography`, `Deprecated`, and `pynacl` — adding ~15MB. For a Lambda function that also includes boto3, FastAPI, and GitPython, keeping the GitHub client lean matters.

**4. Rate Limit Control**
GitHub API has a 60 requests/hour limit for unauthenticated calls (public repos) and 5,000/hour for authenticated. With httpx, we control retry logic, backoff, and rate limit header parsing (`X-RateLimit-Remaining`, `X-RateLimit-Reset`) directly. With PyGithub, rate limit handling is built-in but less configurable.

**5. Consistent HTTP Client**
Using httpx for all external HTTP calls (GitHub API, potential webhook deliveries) means one HTTP client to configure, one connection pool, one retry policy.

### Consequences
- **Positive:** Full API coverage, async ready, lightweight, full control.
- **Negative:** No type hints for GitHub API responses — we define our own Pydantic models. No pagination helpers — we implement cursor-based pagination ourselves.
- **Mitigation:** We create a thin `GitHubClient` class that wraps httpx with GitHub-specific helpers (auth headers, pagination, rate limit tracking). This becomes a reusable module.

### Example Pattern
```python
class GitHubClient:
    def __init__(self, token: str | None = None):
        headers = {"Accept": "application/vnd.github+json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        self.client = httpx.Client(
            base_url="https://api.github.com",
            headers=headers,
            timeout=30.0
        )
    
    def get_workflow_runs(self, owner: str, repo: str) -> list[dict]:
        """Fetch all GitHub Actions workflow runs for a repo."""
        runs = []
        url = f"/repos/{owner}/{repo}/actions/runs"
        while url:
            resp = self.client.get(url, params={"per_page": 100})
            resp.raise_for_status()
            data = resp.json()
            runs.extend(data["workflow_runs"])
            url = resp.links.get("next", {}).get("url")
        return runs
```

---

## ADR-006: Post-Submission Batch Analysis Model

### Status
Accepted

### Context
VibeJudge can analyze code either:
- **Real-time:** Trigger analysis on every `git push` during the hackathon (webhook-driven).
- **Post-submission:** Analyze all repos after the submission deadline closes (batch-driven).

### Decision
**Post-submission batch analysis for Free/Core tier. Real-time reserved for Premium tier (Phase 2).**

### Rationale
This is documented extensively in the Strategy Document, Section 6. Summary of key points:

| Dimension | Real-Time | Post-Submission |
|-----------|-----------|-----------------|
| Cost per 500 teams | $1,500 - $7,500 | $50 - $250 |
| Analyses per team | ~30 (per push) | 1 (deep analysis) |
| Participant friction | Must install GitHub App | Zero (organizer provides URLs) |
| Analysis depth | Current snapshot | Full git history = richer |
| Infrastructure complexity | Webhook handling, burst scaling, SQS queues | Simple batch loop |
| MVP build time | 3-4 weeks | 1-2 weeks |

### Implementation
```
Organizer submits list of repo URLs via API
    → Lambda receives list
    → For each repo:
        1. Clone to /tmp (Lambda ephemeral storage)
        2. Extract git history, file tree, README, Actions data
        3. Run 4 agents sequentially via Converse API
        4. Write scorecard + cost data to DynamoDB
        5. Clean up /tmp
    → Return aggregate results
```

### Consequences
- **Positive:** 10-30x cheaper, simpler to build, richer analysis, zero participant friction.
- **Negative:** No real-time feedback during hackathon. Participants don't see scores until after deadline. Live leaderboard not possible in MVP.
- **Migration Path:** Adding real-time mode means: (1) GitHub App with webhook receiver, (2) SQS queue for buffering push events, (3) diff-only analysis instead of full repo scan. The agent code and scoring logic are identical — only the trigger mechanism changes.

---

## ADR-007: Python Monorepo with SAM

### Status
Accepted

### Context
Should we use:
- **Monorepo** — All code (API, agents, analysis engine, IaC) in one repository.
- **Multi-repo** — Separate repos for API, agent definitions, infrastructure.

### Decision
**Monorepo. Single repository, single SAM template, shared Python modules.**

### Rationale

**1. MVP Speed**
For a competition with a March 6 deadline, managing multiple repos is overhead with no benefit. One repo, one deploy command.

**2. Shared Code**
The agent modules, Pydantic models, DynamoDB helpers, and Bedrock client are used by both the API Lambda and the analysis Lambda. In a monorepo, they're just Python imports. In multi-repo, they'd need to be a published package or duplicated.

**3. SAM Compatibility**
SAM expects all Lambda code and the template in the same directory tree. The `CodeUri` property points to a local path. This is native to monorepo.

**4. Claude Code Compatibility**
Claude Code works best when it can see the full project context. A monorepo means one `/init` and full visibility across all modules.

### Project Structure (Preview — Full detail in Deliverable #9)
```
vibejudge/
├── template.yaml           # SAM IaC
├── samconfig.toml           # SAM deployment config
├── requirements.txt         # Shared Python deps
├── src/
│   ├── api/                 # FastAPI app (Lambda 1)
│   ├── agents/              # 4 judging agents
│   ├── analysis/            # Orchestrator, git analyzer
│   ├── models/              # Pydantic models
│   └── utils/               # Bedrock client, DynamoDB helpers
├── tests/
├── prompts/                 # Agent system prompts (versioned)
└── docs/                    # ADRs, specs, deliverables
```

---

## ADR-008: Manual Agent Orchestration over Framework

### Status
Accepted

### Context
For coordinating the 4 agents, should we use:
- **LangChain/LangGraph** — Popular Python framework for LLM orchestration.
- **CrewAI** — Multi-agent framework with role-based agents.
- **Custom Python orchestrator** — We write the routing and aggregation logic ourselves.

### Decision
**Custom Python orchestrator. No LLM framework dependencies.**

### Rationale

**1. Our Orchestration Is Simple**
VibeJudge's agent flow is: run 4 agents sequentially (or in parallel), collect their JSON outputs, aggregate into a scorecard. There's no conversational back-and-forth, no tool use loops, no memory between turns. LangChain/CrewAI are designed for complex multi-turn agent interactions — that's overkill here.

**2. Dependency Weight**
LangChain pulls in ~50+ transitive dependencies. On Lambda with a 250MB package limit, every dependency matters. Our custom orchestrator is <200 lines of Python with zero additional dependencies beyond boto3.

**3. Bedrock-Native**
The Converse API IS our interface to the models. Adding LangChain's `ChatBedrock` wrapper on top of boto3's `converse()` adds abstraction with no value — it's wrapping a wrapper.

**4. Token Tracking**
With a custom orchestrator, we capture token usage from every Converse API response and log it immediately. LangChain's callback system can do this, but it's more complex to configure correctly and harder to guarantee completeness.

**5. Reproducibility for Competition**
The article needs to show clean, understandable code. A 50-line orchestrator that calls Bedrock directly is more compelling than a LangChain chain-of-chains that obscures the logic.

### Orchestrator Pattern
```python
class AnalysisOrchestrator:
    def __init__(self, bedrock_client, config: HackathonConfig):
        self.agents = [
            BugHunterAgent(bedrock_client, model="amazon.nova-lite-v1:0"),
            PerformanceAgent(bedrock_client, model="amazon.nova-lite-v1:0"),
            InnovationAgent(bedrock_client, model="anthropic.claude-sonnet-4-20250514"),
            AIDetectionAgent(bedrock_client, model="amazon.nova-micro-v1:0"),
        ]
        self.cost_tracker = CostTracker()
    
    async def analyze(self, repo_data: RepoData) -> Scorecard:
        results = []
        for agent in self.agents:
            result = agent.evaluate(repo_data)
            self.cost_tracker.record(agent.name, result.usage)
            results.append(result)
        return Scorecard.aggregate(results, self.cost_tracker.summary())
```

### Consequences
- **Positive:** Lightweight, debuggable, fast cold starts, full control, clean article code.
- **Negative:** If we need complex multi-turn agent interactions (Phase 2 premium real-time mode), we may want a framework then.
- **Migration Path:** Each agent's `evaluate()` method is self-contained. Wrapping them as LangGraph nodes or CrewAI agents later is straightforward.

---

## ADR-009: GitPython + Ephemeral /tmp for Repo Cloning

### Status
Accepted

### Context
VibeJudge needs to clone git repositories and extract: commit history, file diffs, file tree, README content, language composition. Options:

- **GitPython** — Python wrapper around git CLI. Provides Repo objects, commit iterators, diff generation.
- **subprocess + git CLI** — Direct shell calls to git.
- **GitHub API only** — Fetch everything via REST API without cloning.
- **pygit2/libgit2** — Low-level git library (C bindings).

Storage options:
- **Lambda /tmp** — 512MB default, up to 10GB configurable ephemeral storage.
- **EFS** — Persistent filesystem mounted to Lambda.
- **S3** — Clone to S3, process from there.

### Decision
**GitPython for repo operations. Lambda /tmp (configured to 2GB) for ephemeral clone storage.**

### Rationale

**1. GitPython Gives Us What We Need**
```python
repo = git.Repo.clone_from(url, "/tmp/repo", depth=None)
commits = list(repo.iter_commits("main", max_count=500))
for commit in commits:
    diffs = commit.diff(commit.parents[0] if commit.parents else git.NULL_TREE)
```
Commit history, diffs, file trees, blame data — all accessible via Python objects.

**2. Why Not GitHub API Only?**
The GitHub API has rate limits (5,000/hour authenticated) and requires pagination for large repos. Getting full commit history with diffs via API would require hundreds of API calls per repo. Cloning is one operation regardless of repo size. Also, some hackathon repos may be on GitLab or Bitbucket in future — git clone works everywhere.

**3. Lambda /tmp Is Sufficient**
Most hackathon repos are small: 1-50MB. Lambda's ephemeral storage (configurable up to 10GB) handles this easily. We configure 2GB to be safe, which costs an additional ~$0.000000034 per GB-second — negligible. After analysis, we delete the clone.

**4. Why Not EFS?**
EFS requires VPC configuration, which means NAT Gateway ($33/month) for outbound internet access. For a free-tier MVP, this is prohibitively expensive. EFS is the right choice for the enterprise tier where repos might be large and persistence is needed.

### Lambda /tmp Lifecycle
```
1. Lambda invoked with repo URL
2. Clone to /tmp/repos/<submission_id>/  (GitPython)
3. Extract git metadata into RepoData object (in-memory)
4. Delete clone: shutil.rmtree("/tmp/repos/<submission_id>/")
5. Pass RepoData to agents (no filesystem access needed)
6. Lambda execution completes, /tmp is recycled
```

### Consequences
- **Positive:** Fast cloning, full git history access, no API rate limit concerns, no VPC needed.
- **Negative:** Lambda has 15-minute timeout. Very large repos (>2GB) won't fit in /tmp. GitPython depends on git CLI being available in Lambda runtime (it is in Amazon Linux 2023).
- **Mitigation:** For repos exceeding /tmp limits, we fall back to shallow clone (`depth=50`) and supplement with GitHub API calls for older history.

---

## ADR-010: Structured JSON Scoring Output

### Status
Accepted

### Context
Each agent produces a scorecard. What format should the output take?

### Decision
**Structured JSON with a defined schema. Agents are prompted to return ONLY valid JSON.**

### Rationale
Every agent receives a system prompt that ends with a strict output schema. The Converse API response is parsed as JSON. If parsing fails, we retry once with a "Please respond only with valid JSON" follow-up. This ensures:

1. **Machine-readable scores** — Dashboard, API, and aggregation logic can process results without NLP.
2. **Evidence-based** — Every score includes `evidence` fields citing specific files, line numbers, and commit hashes.
3. **Consistent across agents** — All agents use the same outer schema, with agent-specific `details` blocks.

### Schema Preview (Full definition in Deliverable #4 — Agent Prompt Library)
```json
{
  "agent": "bug_hunter",
  "model": "amazon.nova-lite-v1:0",
  "scores": {
    "code_quality": 7.5,
    "security": 6.0,
    "test_coverage": 8.0,
    "error_handling": 5.5
  },
  "overall_score": 6.75,
  "evidence": [
    {
      "finding": "SQL injection vulnerability",
      "file": "src/api/users.py",
      "line": 42,
      "severity": "high",
      "recommendation": "Use parameterized queries"
    }
  ],
  "summary": "The codebase demonstrates solid structure but has critical security gaps..."
}
```

---

## ADR-011: CloudWatch Native over Third-Party Observability

### Status
Accepted

### Context
We need monitoring, logging, and alerting. Options include CloudWatch (native), Datadog, New Relic, or open-source (Grafana + Prometheus).

### Decision
**CloudWatch for everything. No third-party observability tools.**

### Rationale

1. **Free Tier:** 10 custom metrics, 10 alarms, 5GB log ingestion, 3 dashboards — more than enough for MVP.
2. **Bedrock Integration:** Bedrock automatically publishes metrics to CloudWatch (InvocationCount, InputTokenCount, OutputTokenCount, InvocationLatency). No setup required.
3. **Lambda Integration:** Lambda logs go to CloudWatch automatically. Structured JSON logs (via `structlog`) are queryable with CloudWatch Log Insights.
4. **Cost Alerts:** CloudWatch Alarms + AWS Budgets provide budget guardrails for Bedrock spend — the exact feature our cost dashboard needs.
5. **Competition Requirement:** Using only AWS services is cleaner for the article narrative.

### Consequences
- **Positive:** Zero additional cost, native integration, competition-aligned.
- **Negative:** CloudWatch dashboards are less polished than Datadog/Grafana. Log Insights queries are powerful but verbose.
- **Future:** For production enterprise tier, we may add Datadog for APM and distributed tracing.

---

## ADR-012: No Frontend for MVP — API-First

### Status
Accepted

### Context
The organizer dashboard needs to show scorecards, cost breakdowns, and leaderboards. Should we build a frontend for the MVP?

### Decision
**No frontend for MVP. API-first with Swagger UI as the interactive interface. Static HTML scorecard viewer as stretch goal.**

### Rationale

**1. Scope Control**
The March 6 deadline is tight. A React/Next.js dashboard is 40-60 hours of work minimum. The API + agent logic is the core innovation — that's where development time should go.

**2. Swagger UI IS a UI**
FastAPI's auto-generated `/docs` page is an interactive API explorer. An organizer can submit a hackathon config, trigger analysis, and view results — all through Swagger. For the competition demo, this is sufficient.

**3. The Article Doesn't Need a Dashboard**
The competition article is about the AI judging system, the multi-agent architecture, and the AWS integration. Screenshots of API responses and scorecard JSON are more technically compelling than a React dashboard.

**4. Stretch Goal: Static Scorecard Viewer**
If time permits, we build a single-page HTML/JS app on S3 that fetches scorecard data from the API and renders it. No React, no build tooling — just vanilla HTML with Tailwind CSS and fetch() calls. This gives us a visual demo without the frontend overhead.

### Consequences
- **Positive:** Focus on core innovation, faster delivery, less surface area for bugs.
- **Negative:** Less visually impressive for demos. Organizers must interact via API.
- **Phase 2:** Build a proper React dashboard with real-time leaderboard, cost analytics, and rubric builder. This is a Phase 2 deliverable, not MVP.

---

## Decision Summary Matrix

| Decision | Chosen | Runner-Up | Key Reason |
|----------|--------|-----------|------------|
| AI Interface | Converse API | Bedrock Agents | Token tracking transparency |
| IaC | SAM | CDK | Serverless-native, faster |
| API Framework | FastAPI + Mangum | Raw Lambda handlers | OpenAPI docs, validation |
| Database | Single-table DynamoDB | Multi-table | Free tier efficiency |
| GitHub Client | httpx | PyGithub | Actions API coverage, size |
| Analysis Mode | Post-submission batch | Real-time webhooks | 10-30x cheaper, simpler |
| Project Structure | Monorepo | Multi-repo | MVP speed, shared code |
| Orchestration | Custom Python | LangChain/CrewAI | Lightweight, debuggable |
| Git Operations | GitPython + /tmp | GitHub API only | Full history, no rate limits |
| Output Format | Structured JSON | Free-text | Machine-readable, consistent |
| Observability | CloudWatch | Datadog | Free tier, native Bedrock |
| Frontend | API-first (no UI) | React dashboard | Scope control, deadline |

---

*End of Architecture Decision Records v1.0*
*Next deliverable: #3 — DynamoDB Data Model*
