"""Configuration management using Pydantic Settings."""

import os
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    
    # AWS Configuration
    aws_region: str = "us-east-1"
    aws_profile: Optional[str] = None
    
    # DynamoDB
    dynamodb_table_name: str = "VibeJudgeTable"
    
    # S3
    s3_bucket_name: Optional[str] = None
    
    # Bedrock Models (can override defaults)
    bedrock_model_bug_hunter: str = "amazon.nova-lite-v1:0"
    bedrock_model_performance: str = "amazon.nova-lite-v1:0"
    bedrock_model_innovation: str = "anthropic.claude-sonnet-4-20250514"
    bedrock_model_ai_detection: str = "amazon.nova-micro-v1:0"
    
    # Bedrock Inference
    bedrock_max_tokens: int = 4096
    bedrock_temperature: float = 0.3
    
    # API Configuration
    api_version: str = "1.0.0"
    cors_origins: str = "*"
    
    # Logging
    log_level: str = "INFO"
    structured_logging: bool = True
    
    # GitHub API
    github_token: Optional[str] = None
    
    # Analysis Configuration
    max_repo_size_mb: int = 500
    analysis_timeout_seconds: int = 600
    max_context_files: int = 50
    max_lines_per_file: int = 500
    
    # Cost Limits
    default_budget_limit_usd: float = 50.00
    max_cost_per_submission_usd: float = 1.00
    
    # Local Development
    api_port: int = 8000
    api_reload: bool = True
    debug: bool = False
    
    # Testing
    moto_mock_aws: bool = False
    test_dynamodb_table_name: str = "VibeJudgeTable-Test"


# Global settings instance
settings = Settings()
