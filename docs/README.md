# VibeJudge AI Documentation

This directory contains all technical documentation for the VibeJudge AI platform.

## Directory Structure

### Core Documentation (Current Directory)

- **02-architecture-decision-records.md** - Key architectural decisions and rationale
- **03-dynamodb-data-model.md** - Single-table DynamoDB design with 16 access patterns
- **04-agent-prompt-library.md** - AI agent system prompts and versioning
- **05-api-specification.md** - REST API endpoints and schemas
- **06-sam-template.md** - AWS SAM infrastructure documentation
- **07-pydantic-models.md** - Data model schemas and validation
- **08-git-analysis-spec.md** - Repository analysis specifications
- **09-project-structure.md** - Codebase organization and module dependencies
- **10-test-scenarios.md** - Test coverage and scenarios
- **performance-optimization.md** - Performance tuning and optimization strategies
- **VIBEJUDGE_FRONTEND_BACKEND_SEPARATION.md** - Frontend/backend architecture
- **VIBEJUDGE_HUMAN_LAYER_ADDENDUM.md** - Human-in-the-loop features
- **VIBEJUDGE_SELF_SERVICE_PORTAL_CONCEPT.md** - Self-service portal design
- **VIBEJUDGE_STRATEGIC_ENHANCEMENT_PLAN.md** - Future enhancements roadmap

### deployment/

Production deployment guides and operational procedures:

- **DEPLOYMENT.md** - Main deployment guide
- **DEPLOYMENT_GUIDE.md** - Step-by-step deployment instructions
- **DEPLOYMENT_2026-02-25.md** - Deployment session notes
- **QUICK_START.md** - Quick start guide for new developers
- **RUNBOOK.md** - Operational runbook for production issues
- **cloudwatch-queries.md** - CloudWatch Logs Insights queries for monitoring

### testing/

Test documentation and results:

- **TESTING.md** - Main testing guide (unit, integration, E2E)
- **E2E_TEST_RESULTS.md** - End-to-end test execution results
- **E2E_TEST_SUMMARY.md** - E2E test summary and coverage
- **STREAMLIT_TEST_COVERAGE_ANALYSIS.md** - Streamlit UI test coverage analysis
- **STREAMLIT_TEST_COVERAGE_SUMMARY.md** - Streamlit test coverage summary
- **SECURITY_TEST_STATUS.md** - Security testing status and findings
- **PERFORMANCE_VERIFICATION.md** - Performance test results and benchmarks

### development/

Development planning and technical analysis:

- **API_KEY_CONSOLIDATION_PLAN.md** - API key management consolidation plan
- **COST_REDUCTION_ANALYSIS.md** - Cost optimization analysis
- **FRONTEND_FLOWS_ANALYSIS.md** - Frontend user flow analysis
- **PUBLIC_ENDPOINT_FIX.md** - Public endpoint security fixes
- **RESULTS_PAGE_FIXES_SUMMARY.md** - Results page bug fixes
- **SECURITY_ENHANCEMENTS.md** - Security enhancement implementations

### archive/

Historical session summaries and progress tracking:

- **PROJECT_PROGRESS.md** - Overall project progress tracking
- **SESSION_REVIEW.md** - Development session reviews
- **SESSION_SUMMARY_2026-02-25.md** - Session summary from Feb 25, 2026
- **RUFF_LINTING_SESSION_REVIEW.md** - Ruff linting cleanup session
- **FINAL_SESSION_SUMMARY.md** - Final session summary

### operations/

Operational guides and monitoring (currently empty, reserved for future use):

- CloudWatch dashboards
- Alerting configurations
- Incident response procedures
- Capacity planning

## Quick Links

### Getting Started
1. Read [README.md](../README.md) in the root directory
2. Follow [QUICK_START.md](deployment/QUICK_START.md) for local setup
3. Review [09-project-structure.md](09-project-structure.md) for codebase layout

### Deployment
1. [DEPLOYMENT_GUIDE.md](deployment/DEPLOYMENT_GUIDE.md) - Full deployment process
2. [RUNBOOK.md](deployment/RUNBOOK.md) - Production operations

### Development
1. [TESTING.md](testing/TESTING.md) - How to run tests
2. [05-api-specification.md](05-api-specification.md) - API reference
3. [03-dynamodb-data-model.md](03-dynamodb-data-model.md) - Database schema

### Architecture
1. [02-architecture-decision-records.md](02-architecture-decision-records.md) - Why we made key decisions
2. [VIBEJUDGE_FRONTEND_BACKEND_SEPARATION.md](VIBEJUDGE_FRONTEND_BACKEND_SEPARATION.md) - System architecture
3. [performance-optimization.md](performance-optimization.md) - Performance strategies

## Contributing

When adding new documentation:

1. **Core specs** → Place in `docs/` root (numbered files for specs, named files for concepts)
2. **Deployment guides** → Place in `docs/deployment/`
3. **Test documentation** → Place in `docs/testing/`
4. **Development plans** → Place in `docs/development/`
5. **Session summaries** → Place in `docs/archive/`
6. **Operational guides** → Place in `docs/operations/`

Keep root directory clean - only README.md, CONTRIBUTING.md, and LICENSE should remain there.
