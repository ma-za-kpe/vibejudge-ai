"""Complete mock Bedrock responses for integration tests.

These templates include ALL required Pydantic fields to avoid validation errors.
"""

# Complete mock response that works for all agent types (generic)
GENERIC_AGENT_RESPONSE = """{
    "agent": "bug_hunter",
    "prompt_version": "v1",
    "overall_score": 8.5,
    "summary": "Test summary",
    "confidence": 0.9,
    "scores": {
        "code_quality": 8.5,
        "security": 9.0,
        "test_coverage": 7.5,
        "error_handling": 8.0,
        "dependency_hygiene": 8.5
    },
    "evidence": [],
    "ci_observations": {
        "has_ci": true,
        "has_automated_tests": true,
        "has_linting": false,
        "has_security_scanning": false
    }
}"""

# BugHunter-specific mock
BUG_HUNTER_RESPONSE = """{
    "agent": "bug_hunter",
    "prompt_version": "v1",
    "overall_score": 8.5,
    "summary": "Code quality is strong with good testing practices.",
    "confidence": 0.9,
    "scores": {
        "code_quality": 8.5,
        "security": 9.0,
        "test_coverage": 7.5,
        "error_handling": 8.0,
        "dependency_hygiene": 8.5
    },
    "evidence": [],
    "ci_observations": {
        "has_ci": true,
        "has_automated_tests": true,
        "has_linting": false,
        "has_security_scanning": false
    }
}"""

# Performance-specific mock
PERFORMANCE_RESPONSE = """{
    "agent": "performance",
    "prompt_version": "v1",
    "overall_score": 7.5,
    "summary": "Architecture is well-structured with room for optimization.",
    "confidence": 0.85,
    "scores": {
        "architecture": 8.0,
        "database_design": 7.0,
        "api_design": 7.5,
        "scalability": 7.0,
        "resource_efficiency": 8.0
    },
    "evidence": [],
    "ci_observations": {
        "has_ci": true,
        "deployment_sophistication": "basic"
    },
    "tech_stack_assessment": {
        "technologies_identified": ["Python", "FastAPI"],
        "stack_appropriateness": "Good choice for API development",
        "notable_choices": "Modern async framework"
    }
}"""

# Innovation-specific mock
INNOVATION_RESPONSE = """{
    "agent": "innovation",
    "prompt_version": "v1",
    "overall_score": 9.0,
    "summary": "Highly innovative approach with creative solutions.",
    "confidence": 0.95,
    "scores": {
        "technical_novelty": 9.0,
        "creative_problem_solving": 8.5,
        "architecture_elegance": 9.0,
        "readme_quality": 8.0,
        "demo_potential": 9.5
    },
    "evidence": [],
    "innovation_highlights": ["Novel algorithm", "Elegant design"],
    "development_story": "Team showed strong iteration",
    "hackathon_context_assessment": "Well-suited for hackathon constraints"
}"""

# AIDetection-specific mock
AI_DETECTION_RESPONSE = """{
    "agent": "ai_detection",
    "prompt_version": "v1",
    "overall_score": 8.0,
    "summary": "Development patterns indicate authentic human work.",
    "confidence": 0.9,
    "scores": {
        "commit_authenticity": 8.5,
        "development_velocity": 8.0,
        "authorship_consistency": 8.0,
        "iteration_depth": 7.5,
        "ai_generation_indicators": 8.5
    },
    "evidence": [],
    "commit_analysis": {
        "total_commits": 50,
        "avg_lines_per_commit": 45.0,
        "largest_commit_lines": 200,
        "commit_frequency_pattern": "steady",
        "meaningful_message_ratio": 0.8
    },
    "ai_policy_observation": "No significant AI generation detected"
}"""
