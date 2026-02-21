# VibeJudge AI — Product Specification

## Product Vision
VibeJudge AI is an automated hackathon judging platform that uses 4 specialized AI agents on Amazon Bedrock to evaluate code submissions in minutes instead of days.

## Target Users
1. **Hackathon Organizers** — Need fair, scalable, unbiased judging for 50-500 teams
2. **Hackathon Participants** — Want detailed feedback beyond just rankings
3. **Platform Administrators** — Require cost transparency and budget control

## Core Value Proposition
- **Speed:** Judge 500 submissions in < 2 hours (vs 3 days manual)
- **Cost:** $11.50 for 500 repos (vs $1,500-7,500 for manual judging)
- **Quality:** Evidence-based scoring with specific file:line citations
- **Fairness:** Consistent rubric application, zero human bias

## MVP Scope (What We're Building)

### IN SCOPE ✅
1. REST API (20 endpoints) with auto-generated Swagger docs
2. Post-submission batch analysis (NOT real-time)
3. 4 specialized AI agents:
   - BugHunter: Code quality, security, testing
   - PerformanceAnalyzer: Architecture, scalability, design
   - InnovationScorer: Creativity, novelty, documentation
   - AIDetection: Development authenticity, AI usage patterns
4. Evidence validation (verify file:line citations exist)
5. Per-agent cost tracking (transparent billing)
6. Weighted scoring based on custom rubric
7. Leaderboard generation
8. GitHub repo analysis (commits, files, Actions data)

### OUT OF SCOPE ❌ (MVP)
1. Frontend/dashboard (API-first for MVP)
2. Real-time webhooks (post-submission batch only)
3. User authentication beyond API keys
4. Email notifications
5. PDF report generation
6. GitHub App installation

### PHASE 2 (Post-Competition)
- React dashboard
- Real-time GitHub webhooks
- Premium tier with custom agents
- Email notifications
- PDF scorecards

## Success Metrics (MVP)
- ✅ Analyze 50 repos in < 30 minutes
- ✅ Cost < $0.025 per repo
- ✅ 95%+ evidence verification rate (no hallucinations)
- ✅ Zero Lambda timeouts (15min limit)
- ✅ 100% AWS Free Tier compliance (except Bedrock)
- ✅ API response time < 200ms (except /analyze endpoint)

## Competition Requirements
- Must use Kiro for development ✅
- Must stay within AWS Free Tier ✅
- Must publish article by March 13, 2026 ✅
- Must build working demo ✅

## Business Model (For Article)
- **Free Tier:** 3 hackathons/year, 50 submissions each, 2 agents
- **Premium:** $99/month, unlimited hackathons, all 4 agents
- **Enterprise:** Custom pricing, dedicated agents, white-label

## Key Differentiators
1. **First platform built for AI-assisted coding era** (AI policy modes)
2. **Evidence-based scoring** (file:line citations, validated)
3. **Cost transparency** (per-agent token tracking)
4. **GitHub Actions analysis** (CI/CD sophistication scoring)
5. **Multi-agent architecture** (specialized experts, not general chatbot)
