# VibeJudge AI — Makefile
# Common development and deployment commands

.PHONY: help install install-dev test test-cov lint format type-check build deploy-dev deploy-staging deploy-prod local clean

# Default target
.DEFAULT_GOAL := help

# ============================================================
# HELP
# ============================================================

help: ## Show this help message
	@echo "VibeJudge AI — Available Commands"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ============================================================
# INSTALLATION
# ============================================================

install: ## Install production dependencies
	pip install -r requirements.txt

install-dev: ## Install all dependencies (production + development)
	pip install -r requirements.txt
	pip install -r requirements-dev.txt

# ============================================================
# TESTING
# ============================================================

test: ## Run tests
	pytest tests/ -v

test-cov: ## Run tests with coverage report
	pytest tests/ -v --cov=src --cov-report=html --cov-report=term

test-unit: ## Run unit tests only
	pytest tests/unit/ -v

test-integration: ## Run integration tests only
	pytest tests/integration/ -v

test-watch: ## Run tests in watch mode
	pytest-watch tests/ -v

# ============================================================
# CODE QUALITY
# ============================================================

lint: ## Run linter (ruff)
	ruff check src/ tests/

lint-fix: ## Run linter and auto-fix issues
	ruff check --fix src/ tests/

format: ## Format code with black
	black src/ tests/

format-check: ## Check code formatting without changes
	black --check src/ tests/

type-check: ## Run type checker (mypy)
	mypy src/ --strict --ignore-missing-imports

quality: lint format-check type-check ## Run all code quality checks

# ============================================================
# AWS SAM BUILD & DEPLOY
# ============================================================

build: ## Build SAM application
	sam build

validate: ## Validate SAM template
	sam validate

deploy-dev: build ## Deploy to dev environment
	sam deploy --config-env dev --no-confirm-changeset

deploy-staging: build ## Deploy to staging environment
	sam deploy --config-env staging --no-confirm-changeset

deploy-prod: build ## Deploy to production environment
	sam deploy --config-env prod --no-confirm-changeset

# ============================================================
# LOCAL DEVELOPMENT
# ============================================================

run-local: ## Run API locally with uvicorn (recommended for development)
	@echo "Starting FastAPI with uvicorn on http://localhost:8000"
	@echo "API docs available at http://localhost:8000/docs"
	uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

local-api: ## Run API locally with SAM
	sam local start-api --env-vars env.json

local-invoke-api: ## Invoke API Lambda function locally
	sam local invoke ApiFunction --event events/test-api-event.json

local-invoke-analyzer: ## Invoke Analyzer Lambda function locally
	sam local invoke AnalyzerFunction --event events/test-analysis.json

test-analysis: ## Test analysis endpoint with sample repo
	@echo "Testing analysis endpoint with anthropic-quickstarts repo..."
	curl -X POST http://localhost:8000/api/v1/analysis/analyze \
		-H "Content-Type: application/json" \
		-H "X-API-Key: test-api-key" \
		-d @events/test-analysis-request.json

# ============================================================
# DATABASE
# ============================================================

dynamodb-local: ## Start local DynamoDB (requires Docker)
	docker run -p 8000:8000 amazon/dynamodb-local

create-table-local: ## Create DynamoDB table locally
	aws dynamodb create-table \
		--table-name VibeJudgeTable \
		--attribute-definitions \
			AttributeName=PK,AttributeType=S \
			AttributeName=SK,AttributeType=S \
			AttributeName=GSI1PK,AttributeType=S \
			AttributeName=GSI1SK,AttributeType=S \
			AttributeName=GSI2PK,AttributeType=S \
			AttributeName=GSI2SK,AttributeType=S \
		--key-schema \
			AttributeName=PK,KeyType=HASH \
			AttributeName=SK,KeyType=RANGE \
		--provisioned-throughput \
			ReadCapacityUnits=5,WriteCapacityUnits=5 \
		--global-secondary-indexes \
			'[{"IndexName":"GSI1","KeySchema":[{"AttributeName":"GSI1PK","KeyType":"HASH"},{"AttributeName":"GSI1SK","KeyType":"RANGE"}],"Projection":{"ProjectionType":"ALL"},"ProvisionedThroughput":{"ReadCapacityUnits":5,"WriteCapacityUnits":5}},{"IndexName":"GSI2","KeySchema":[{"AttributeName":"GSI2PK","KeyType":"HASH"},{"AttributeName":"GSI2SK","KeyType":"RANGE"}],"Projection":{"ProjectionType":"ALL"},"ProvisionedThroughput":{"ReadCapacityUnits":5,"WriteCapacityUnits":5}}]' \
		--endpoint-url http://localhost:8000

# ============================================================
# LOGS
# ============================================================

logs-api: ## Tail API Lambda logs
	sam logs -n ApiFunction --stack-name vibejudge-dev --tail

logs-analyzer: ## Tail Analyzer Lambda logs
	sam logs -n AnalyzerFunction --stack-name vibejudge-dev --tail

# ============================================================
# CLEANUP
# ============================================================

clean: ## Clean build artifacts
	rm -rf .aws-sam/
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.coverage" -delete
	rm -rf htmlcov/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/

clean-repos: ## Clean cloned test repositories
	rm -rf cloned_repos/
	rm -rf test_repos/

# ============================================================
# DOCUMENTATION
# ============================================================

docs: ## Generate API documentation
	@echo "Opening Swagger UI at http://localhost:8000/docs"
	@echo "Run 'make local' first to start the API server"

# ============================================================
# UTILITIES
# ============================================================

env: ## Create .env file from template
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "Created .env file from template. Please update with your values."; \
	else \
		echo ".env file already exists. Skipping."; \
	fi

check-deps: ## Check for outdated dependencies
	pip list --outdated

update-deps: ## Update dependencies (use with caution)
	pip install --upgrade -r requirements.txt
	pip install --upgrade -r requirements-dev.txt

# ============================================================
# CI/CD
# ============================================================

ci: quality test ## Run CI checks (quality + tests)

pre-commit: format lint test-unit ## Run pre-commit checks
