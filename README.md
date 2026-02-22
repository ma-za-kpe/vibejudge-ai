# VibeJudge AI 🤖⚖️

> AI-powered hackathon judging platform using Amazon Bedrock

[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-green.svg)](https://fastapi.tiangolo.com/)
[![AWS SAM](https://img.shields.io/badge/AWS%20SAM-Serverless-orange.svg)](https://aws.amazon.com/serverless/sam/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 🎯 Overview

VibeJudge AI automates hackathon judging using 4 specialized AI agents on Amazon Bedrock, providing:

- **Speed:** Judge 500 submissions in < 2 hours (vs 3 days manual)
- **Cost:** $11.50 for 500 repos (vs $1,500-7,500 for manual judging)
- **Quality:** Evidence-based scoring with specific file:line citations
- **Fairness:** Consistent rubric application, zero human bias

## 🤖 AI Agents

1. **BugHunter** (Nova Lite) — Code quality, security, testing
2. **PerformanceAnalyzer** (Nova Lite) — Architecture, scalability, design
3. **InnovationScorer** (Claude Sonnet 4) — Creativity, novelty, documentation
4. **AIDetection** (Nova Micro) — Development authenticity, AI usage patterns

## 🏗️ Architecture

- **API Lambda:** FastAPI + Mangum (1024MB, 30s timeout)
- **Analyzer Lambda:** Batch processor (2048MB, 900s timeout, 2GB ephemeral)
- **Database:** Single-table DynamoDB (5 RCU/5 WCU provisioned)
- **AI:** Amazon Bedrock Converse API (token tracking)
- **Storage:** S3 for artifacts (optional)

## 🚀 Quick Start

### 🎉 NEW: Ready to Deploy!

**All development complete!** 48/48 tests passing, all features implemented.

**Deploy in 5 minutes:**

```bash
# 1. Deploy to AWS
make deploy-dev

# 2. Test deployment (replace with your API URL)
export API_URL="https://xxxxxxxxxx.execute-api.us-east-1.amazonaws.com"
./test_deployment.sh
```

**See [NEXT_STEPS.md](NEXT_STEPS.md) for detailed deployment instructions.**

**Documentation:**
- [READY_FOR_DEPLOYMENT.md](READY_FOR_DEPLOYMENT.md) — Complete deployment checklist
- [DEPLOYMENT.md](DEPLOYMENT.md) — Detailed deployment guide
- [QUICK_START.md](QUICK_START.md) — 5-minute quick start

### Prerequisites

- Python 3.12+
- AWS CLI configured
- AWS SAM CLI
- Docker (for local testing)
- Bedrock model access enabled (see deployment guide)

### Installation

```bash
# Clone repository
git clone https://github.com/vibecoders/vibejudge-ai.git
cd vibejudge-ai

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
make install-dev

# Create environment file
make env
# Edit .env with your AWS configuration
```

### Local Development

```bash
# Run API locally
make local

# API will be available at http://localhost:8000
# Swagger docs at http://localhost:8000/docs
```

### Testing

```bash
# Run all tests
make test

# Run with coverage
make test-cov

# Run only unit tests
make test-unit
```

### Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for complete deployment guide.

```bash
# Quick deploy to dev environment
make deploy-dev

# Deploy to staging
make deploy-staging

# Deploy to production
make deploy-prod
```

**Important:** Enable Bedrock model access before deploying! See deployment guide for details.

## 📚 API Documentation

Once deployed or running locally, visit:

- **Swagger UI:** `https://your-api-url/docs`
- **ReDoc:** `https://your-api-url/redoc`
- **OpenAPI JSON:** `https://your-api-url/openapi.json`

### Key Endpoints

```
POST   /api/v1/organizers              # Create account
POST   /api/v1/organizers/login        # Login (regenerate API key)
GET    /api/v1/organizers/me           # Get profile

POST   /api/v1/hackathons              # Create hackathon
GET    /api/v1/hackathons              # List hackathons
GET    /api/v1/hackathons/{id}         # Get hackathon details

POST   /api/v1/hackathons/{id}/submissions  # Add submissions (batch)
GET    /api/v1/hackathons/{id}/submissions  # List submissions

POST   /api/v1/hackathons/{id}/analyze      # Trigger analysis
GET    /api/v1/hackathons/{id}/analyze/status  # Check status
GET    /api/v1/hackathons/{id}/leaderboard    # Get leaderboard

GET    /api/v1/submissions/{id}        # Get submission details
GET    /api/v1/submissions/{id}/costs  # Get cost breakdown

GET    /health                         # Health check
```

## 🧪 Development

### Code Quality

```bash
# Run linter
make lint

# Auto-fix linting issues
make lint-fix

# Format code
make format

# Type checking
make type-check

# Run all quality checks
make quality
```

### Project Structure

```
vibejudge/
├── src/
│   ├── api/              # FastAPI application
│   ├── agents/           # AI agents (Bedrock)
│   ├── analysis/         # Analysis engine
│   ├── models/           # Pydantic schemas
│   ├── prompts/          # Agent system prompts
│   ├── services/         # Business logic
│   └── utils/            # Shared utilities
├── tests/
│   ├── unit/             # Unit tests
│   ├── integration/      # Integration tests
│   └── fixtures/         # Test data
├── template.yaml         # SAM infrastructure
└── Makefile              # Common commands
```

## 💰 Cost Optimization

VibeJudge AI is designed to stay within AWS Free Tier:

- **Lambda:** 1M requests/month, 400K GB-seconds
- **DynamoDB:** 25 RCU/WCU (provisioned mode)
- **API Gateway:** 1M calls/month (HTTP API)
- **S3:** 5GB storage
- **CloudWatch:** 5GB logs, 10 alarms

**Only Bedrock incurs costs** (~$0.023 per repo with default agent mix).

## 📊 Success Metrics

- ✅ Analyze 50 repos in < 30 minutes
- ✅ Cost < $0.025 per repo
- ✅ 95%+ evidence verification rate
- ✅ Zero Lambda timeouts
- ✅ API response time < 200ms

## 📖 Documentation

- [QUICK_START.md](QUICK_START.md) — 5-minute deployment guide
- [DEPLOYMENT.md](DEPLOYMENT.md) — Complete deployment guide
- [TESTING.md](TESTING.md) — Local development and testing
- [PROJECT_STATUS.md](PROJECT_STATUS.md) — Current project status
- [docs/](docs/) — Technical specifications

## 🤝 Contributing

This project was built for the AWS 10,000 AIdeas competition. Contributions welcome after March 13, 2026!

## 📝 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with [Kiro](https://kiro.dev) AI IDE
- Powered by [Amazon Bedrock](https://aws.amazon.com/bedrock/)
- Part of [AWS 10,000 AIdeas](https://aws.amazon.com/10000ideas/) competition

## 📧 Contact

- **Author:** Maku Mazakpe
- **Organization:** Vibe Coders
- **Email:** maku@vibecoders.com
- **GitHub:** [@vibecoders](https://github.com/vibecoders)

---

**Built with ❤️ using Kiro AI IDE**
