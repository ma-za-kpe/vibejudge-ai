"""VibeJudge AI — Constants and Configuration.

Model rates, tier limits, file priorities, and other constants.
"""

# ============================================================
# BEDROCK MODEL RATES (USD per token)
# ============================================================

MODEL_RATES = {
    "amazon.nova-micro-v1:0": {
        "input": 0.000000035,
        "output": 0.000000140,
    },
    "amazon.nova-lite-v1:0": {
        "input": 0.000000060,
        "output": 0.000000240,
    },
    "amazon.nova-pro-v1:0": {
        "input": 0.000000800,
        "output": 0.000003200,
    },
    "anthropic.claude-3-haiku-20240307-v1:0": {
        "input": 0.000000250,
        "output": 0.000001250,
    },
    # Claude Sonnet 4.6 - Latest version (Feb 2026), optimized for coding and agents
    "us.anthropic.claude-sonnet-4-6": {
        "input": 0.000003000,
        "output": 0.000015000,
    },
}

# ============================================================
# AGENT MODEL ASSIGNMENTS
# ============================================================

AGENT_MODELS = {
    "bug_hunter": "amazon.nova-lite-v1:0",
    "performance": "amazon.nova-lite-v1:0",
    "innovation": "us.anthropic.claude-sonnet-4-6",  # Latest Claude Sonnet 4.6 (Feb 2026)
    "ai_detection": "amazon.nova-micro-v1:0",
}

# ============================================================
# AGENT INFERENCE CONFIGS
# ============================================================

AGENT_CONFIGS = {
    "bug_hunter": {
        "model_id": "amazon.nova-lite-v1:0",
        "temperature": 0.1,
        "max_tokens": 2048,
        "top_p": 0.9,
        "timeout_seconds": 120,
    },
    "performance": {
        "model_id": "amazon.nova-lite-v1:0",
        "temperature": 0.1,
        "max_tokens": 2048,
        "top_p": 0.9,
        "timeout_seconds": 120,
    },
    "innovation": {
        "model_id": "us.anthropic.claude-sonnet-4-6",  # Latest Claude Sonnet 4.6 (Feb 2026)
        "temperature": 0.3,
        "max_tokens": 3000,
        "top_p": 0.95,
        "timeout_seconds": 180,
    },
    "ai_detection": {
        "model_id": "amazon.nova-micro-v1:0",
        "temperature": 0.0,
        "max_tokens": 1500,
        "top_p": 0.9,
        "timeout_seconds": 90,
    },
}

# ============================================================
# FILE PRIORITIES FOR CONTEXT SELECTION
# ============================================================

FILE_PRIORITIES = {
    # Entry points (highest priority)
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
    "go.mod": 90,
    "Dockerfile": 85,
    "docker-compose.yml": 85,
    "docker-compose.yaml": 85,
    # IaC
    "template.yaml": 80,
    "template.yml": 80,
    "serverless.yml": 80,
    "cdk.json": 80,
    "terraform.tf": 80,
}

# ============================================================
# SOURCE FILE EXTENSIONS
# ============================================================

SOURCE_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".rs",
    ".java", ".kt", ".cs", ".rb", ".php", ".swift",
    ".c", ".cpp", ".h", ".hpp", ".sql", ".sh",
}

CONFIG_EXTENSIONS = {
    ".json", ".yaml", ".yml", ".toml", ".env.example",
    ".cfg", ".ini", ".xml",
}

# ============================================================
# IGNORE PATTERNS
# ============================================================

IGNORE_PATTERNS = {
    ".git", "__pycache__", "node_modules", ".venv", "venv",
    ".env", ".DS_Store", "*.pyc", "*.pyo", "*.egg-info",
    "dist", "build", ".next", ".nuxt", "coverage",
    ".terraform", ".serverless", ".aws-sam",
}

# ============================================================
# ANALYSIS LIMITS
# ============================================================

MAX_FILE_LINES = 200
MAX_FILES = 25
MAX_COMMITS = 100
MAX_DIFFS = 30
MAX_WORKFLOW_RUNS = 50
MAX_README_CHARS = 12000
MAX_FILE_TREE_LINES = 200
MAX_FILE_TREE_DEPTH = 4

# ============================================================
# CLONE CONFIGURATION
# ============================================================

CLONE_TIMEOUT_SECONDS = 120
CLONE_SHALLOW_DEPTH = 100
MAX_REPO_SIZE_MB = 500

# ============================================================
# TIER LIMITS
# ============================================================

TIER_LIMITS = {
    "free": {
        "hackathons_per_year": 3,
        "submissions_per_hackathon": 50,
        "agents_available": ["bug_hunter", "performance"],
        "max_budget_usd": 5.00,
    },
    "premium": {
        "hackathons_per_year": None,  # Unlimited
        "submissions_per_hackathon": 500,
        "agents_available": ["bug_hunter", "performance", "innovation", "ai_detection"],
        "max_budget_usd": 100.00,
    },
    "enterprise": {
        "hackathons_per_year": None,
        "submissions_per_hackathon": None,
        "agents_available": ["bug_hunter", "performance", "innovation", "ai_detection"],
        "max_budget_usd": None,
    },
}

# ============================================================
# SCORING THRESHOLDS
# ============================================================

RECOMMENDATION_THRESHOLDS = {
    "strong_contender": 8.0,
    "solid_submission": 6.5,
    "needs_improvement": 4.5,
    "concerns_flagged": 0.0,
}

# ============================================================
# CONTEXT WINDOW BUDGETS
# ============================================================

CONTEXT_BUDGETS = {
    "amazon.nova-micro-v1:0": {
        "total": 128000,
        "system_prompt": 1500,
        "response": 1500,
        "repo_data": 125000,
    },
    "amazon.nova-lite-v1:0": {
        "total": 300000,
        "system_prompt": 2000,
        "response": 2048,
        "repo_data": 295952,
    },
    "us.anthropic.claude-sonnet-4-6": {  # Latest Claude Sonnet 4.6 with 1M context
        "total": 200000,  # Conservative limit for cost control
        "system_prompt": 2500,
        "response": 3000,
        "repo_data": 194500,
    },
}

# ============================================================
# LANGUAGE DETECTION
# ============================================================

LANGUAGE_MAP = {
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
    ".h": "C/C++ Header",
    ".hpp": "C++ Header",
    ".sql": "SQL",
    ".sh": "Shell",
    ".json": "JSON",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".toml": "TOML",
    ".xml": "XML",
    ".html": "HTML",
    ".css": "CSS",
    ".scss": "SCSS",
}

# ============================================================
# RETRY CONFIGURATION
# ============================================================

BEDROCK_RETRY_ATTEMPTS = 3
BEDROCK_RETRY_WAIT_SECONDS = 2
BEDROCK_RETRY_BACKOFF_MULTIPLIER = 2

# ============================================================
# TTL CONFIGURATION
# ============================================================

ANALYSIS_JOB_TTL_DAYS = 30
