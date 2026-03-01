"""API mocking utilities for isolated E2E tests."""

import json
from collections.abc import Callable
from typing import Any

from playwright.sync_api import BrowserContext, Request, Route


class APIMock:
    """Helper class for mocking API responses."""

    def __init__(self, context: BrowserContext):
        self.context = context
        self.routes = {}
        self.call_counts = {}

    # ========================================================================
    # GENERIC MOCKING
    # ========================================================================

    def mock_get(self, url_pattern: str, status: int = 200, body: dict[str, Any] = None):
        """Mock GET request."""

        def handler(route: Route):
            if route.request.method == "GET":
                route.fulfill(
                    status=status, content_type="application/json", body=json.dumps(body or {})
                )
            else:
                route.continue_()

        self.context.route(url_pattern, handler)
        self.routes[url_pattern] = handler

    def mock_post(self, url_pattern: str, status: int = 200, body: dict[str, Any] = None):
        """Mock POST request."""

        def handler(route: Route):
            if route.request.method == "POST":
                route.fulfill(
                    status=status, content_type="application/json", body=json.dumps(body or {})
                )
            else:
                route.continue_()

        self.context.route(url_pattern, handler)
        self.routes[url_pattern] = handler

    def mock_delete(self, url_pattern: str, status: int = 204):
        """Mock DELETE request."""

        def handler(route: Route):
            if route.request.method == "DELETE":
                route.fulfill(status=status)
            else:
                route.continue_()

        self.context.route(url_pattern, handler)

    def mock_with_callback(self, url_pattern: str, callback: Callable[[Request], dict]):
        """Mock with custom callback function."""

        def handler(route: Route):
            response = callback(route.request)
            route.fulfill(
                status=response.get("status", 200),
                content_type="application/json",
                body=json.dumps(response.get("body", {})),
            )

        self.context.route(url_pattern, handler)

    # ========================================================================
    # AUTHENTICATION MOCKS
    # ========================================================================

    def mock_health_check(self, status: int = 200):
        """Mock /health endpoint."""
        self.mock_get("**/health", status=status, body={"status": "healthy"})

    def mock_login_success(self, api_key: str = "vj_test_mock_key"):
        """Mock successful login."""
        self.mock_post(
            "**/organizers/login",
            status=200,
            body={"api_key": api_key, "message": "Login successful"},
        )

    def mock_login_failure(self, status: int = 401, message: str = "Invalid credentials"):
        """Mock failed login."""
        self.mock_post("**/organizers/login", status=status, body={"detail": message})

    # ========================================================================
    # HACKATHON MOCKS
    # ========================================================================

    def mock_hackathons_list(self, hackathons: list = None):
        """Mock hackathons list endpoint."""
        if hackathons is None:
            hackathons = [
                {
                    "hack_id": "test_hack_001",
                    "name": "Test Hackathon",
                    "status": "configured",
                    "start_date": "2025-03-01T00:00:00Z",
                    "end_date": "2025-03-31T23:59:59Z",
                }
            ]

        self.mock_get(
            "**/hackathons",
            status=200,
            body={"hackathons": hackathons, "next_cursor": None, "has_more": False},
        )

    def mock_hackathon_stats(self, hack_id: str, stats: dict = None):
        """Mock hackathon stats endpoint."""
        if stats is None:
            stats = {
                "submission_count": 10,
                "verified_count": 9,
                "pending_count": 1,
                "participant_count": 30,
            }

        self.mock_get(f"**/hackathons/{hack_id}/stats", status=200, body=stats)

    def mock_create_hackathon(self, hack_id: str = "new_hack_123"):
        """Mock hackathon creation."""
        self.mock_post(
            "**/hackathons",
            status=201,
            body={"hack_id": hack_id, "name": "E2E Test Hackathon", "status": "draft"},
        )

    # ========================================================================
    # ANALYSIS LIFECYCLE MOCKS
    # ========================================================================

    def mock_cost_estimate(self, hack_id: str, cost: float = 12.45):
        """Mock cost estimate endpoint."""
        self.mock_post(
            f"**/hackathons/{hack_id}/analyze/estimate",
            status=200,
            body={
                "estimate": {
                    "total_cost_usd": {"min": cost * 0.8, "expected": cost, "max": cost * 1.2},
                    "submission_count": 10,
                }
            },
        )

    def mock_start_analysis(self, hack_id: str, job_id: str = "job_001", cost: float = 12.45):
        """Mock analysis start endpoint."""
        self.mock_post(
            f"**/hackathons/{hack_id}/analyze",
            status=202,
            body={"job_id": job_id, "estimated_cost_usd": cost, "status": "queued"},
        )

    def mock_analysis_status(self, hack_id: str, job_id: str = None, status: str = "running"):
        """Mock analysis status check."""
        response_body = {}
        if status in ["queued", "running"] and job_id:
            response_body = {"status": status, "job_id": job_id}
        # If status is completed/failed, return empty (no active job)

        self.mock_get(f"**/hackathons/{hack_id}/analyze/status", status=200, body=response_body)

    def mock_job_status(
        self, hack_id: str, job_id: str, status: str = "running", progress: float = 50.0
    ):
        """Mock job status endpoint."""
        body = {
            "job_id": job_id,
            "status": status,
            "progress_percent": progress,
            "completed_submissions": int(10 * progress / 100),
            "failed_submissions": 0,
            "total_submissions": 10,
            "current_cost_usd": 12.45 * progress / 100,
        }

        if status == "completed":
            body["progress_percent"] = 100.0
            body["completed_submissions"] = 10
            body["current_cost_usd"] = 12.45

        self.mock_get(f"**/hackathons/{hack_id}/jobs/{job_id}", status=200, body=body)

    def mock_analysis_lifecycle(self, hack_id: str, job_id: str = "job_001"):
        """
        Mock complete analysis lifecycle with state progression.

        Polls will transition: queued → running → completed
        """
        self.call_counts[f"job_{job_id}"] = 0

        def job_status_handler(request: Request):
            self.call_counts[f"job_{job_id}"] += 1
            count = self.call_counts[f"job_{job_id}"]

            if count == 1:
                # First call: queued
                return {
                    "status": 200,
                    "body": {
                        "job_id": job_id,
                        "status": "queued",
                        "progress_percent": 0.0,
                        "completed_submissions": 0,
                        "failed_submissions": 0,
                        "total_submissions": 10,
                        "current_cost_usd": 0.0,
                    },
                }
            elif count <= 3:
                # Next 2 calls: running
                progress = count * 33.3
                return {
                    "status": 200,
                    "body": {
                        "job_id": job_id,
                        "status": "running",
                        "progress_percent": progress,
                        "completed_submissions": int(10 * progress / 100),
                        "failed_submissions": 0,
                        "total_submissions": 10,
                        "current_cost_usd": 12.45 * progress / 100,
                    },
                }
            else:
                # 4th+ call: completed
                return {
                    "status": 200,
                    "body": {
                        "job_id": job_id,
                        "status": "completed",
                        "progress_percent": 100.0,
                        "completed_submissions": 10,
                        "failed_submissions": 0,
                        "total_submissions": 10,
                        "current_cost_usd": 12.45,
                    },
                }

        self.mock_with_callback(f"**/hackathons/{hack_id}/jobs/{job_id}", job_status_handler)

        # Mock /analyze/status to return job_id initially, then None when complete
        def analyze_status_handler(request: Request):
            count = self.call_counts.get(f"job_{job_id}", 0)
            if count < 4:
                return {"status": 200, "body": {"status": "running", "job_id": job_id}}
            else:
                return {"status": 200, "body": {}}

        self.mock_with_callback(f"**/hackathons/{hack_id}/analyze/status", analyze_status_handler)

    def mock_budget_exceeded(self, hack_id: str, endpoint: str = "estimate"):
        """Mock HTTP 402 budget exceeded error."""
        if endpoint == "estimate":
            url = f"**/hackathons/{hack_id}/analyze/estimate"
        else:
            url = f"**/hackathons/{hack_id}/analyze"

        self.mock_post(
            url,
            status=402,
            body={"detail": "Budget limit exceeded: $100.00 limit, estimated cost $125.50"},
        )

    def mock_analysis_conflict(self, hack_id: str):
        """Mock HTTP 409 conflict (analysis already running)."""
        self.mock_post(
            f"**/hackathons/{hack_id}/analyze",
            status=409,
            body={"detail": "Analysis already running for this hackathon"},
        )

    # ========================================================================
    # LEADERBOARD & RESULTS MOCKS
    # ========================================================================

    def mock_leaderboard_with_submissions(self, hack_id: str, count: int = 10):
        """Mock leaderboard endpoint with submissions."""
        submissions = [
            {
                "sub_id": f"sub_{i:03d}",
                "rank": i + 1,
                "team_name": f"Team {i + 1}",
                "overall_score": 95.0 - i * 2.0,
                "confidence": 0.95,
                "recommendation": "must_interview" if i < 3 else "strong_consider",
                "created_at": "2025-03-01T10:00:00Z",
            }
            for i in range(count)
        ]

        self.mock_get(
            f"**/hackathons/{hack_id}/leaderboard",
            status=200,
            body={
                "hack_id": hack_id,
                "total_submissions": count,
                "analyzed_count": count,
                "submissions": submissions,
            },
        )

    def mock_scorecard(self, hack_id: str, sub_id: str):
        """Mock scorecard endpoint."""
        self.mock_get(
            f"**/hackathons/{hack_id}/submissions/{sub_id}/scorecard",
            status=200,
            body={
                "sub_id": sub_id,
                "team_name": "Team Awesome",
                "overall_score": 92.5,
                "confidence": 0.95,
                "recommendation": "must_interview",
                "dimension_scores": {
                    "code_quality": {"raw": 90.0, "weighted": 27.0, "weight": 0.3},
                    "innovation": {"raw": 95.0, "weighted": 28.5, "weight": 0.3},
                    "performance": {"raw": 92.0, "weighted": 27.6, "weight": 0.3},
                    "authenticity": {"raw": 90.0, "weighted": 9.0, "weight": 0.1},
                },
                "agent_results": {
                    "bug_hunter": {
                        "summary": "Excellent code quality",
                        "strengths": ["Clean architecture"],
                        "improvements": ["Add more tests"],
                        "cost_usd": 0.002,
                    }
                },
                "repo_meta": {
                    "primary_language": "Python",
                    "commit_count": 45,
                    "contributor_count": 3,
                    "has_tests": True,
                    "has_ci": True,
                },
                "total_cost_usd": 0.023,
            },
        )

    def mock_individual_scorecards(self, hack_id: str, sub_id: str):
        """Mock individual scorecards endpoint."""
        self.mock_get(
            f"**/hackathons/{hack_id}/submissions/{sub_id}/individual-scorecards",
            status=200,
            body={
                "team_dynamics": {
                    "collaboration_quality": "excellent",
                    "role_distribution": "balanced",
                },
                "members": [
                    {
                        "member_name": "Alice",
                        "commit_count": 45,
                        "skill_assessment": "Senior developer",
                        "actionable_feedback": "Great work!",
                    }
                ],
            },
        )

    # ========================================================================
    # UTILITIES
    # ========================================================================

    def reset_call_counts(self):
        """Reset all call counters."""
        self.call_counts = {}

    def clear_all_mocks(self):
        """Clear all mocked routes."""
        self.routes = {}
        self.call_counts = {}
