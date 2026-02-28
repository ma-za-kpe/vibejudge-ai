"""Pytest configuration for streamlit_ui tests."""

import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

# Add the streamlit_ui directory to the Python path
# This allows tests to import from components, pages, etc.
streamlit_ui_dir = Path(__file__).parent.parent
sys.path.insert(0, str(streamlit_ui_dir))


def create_comprehensive_api_mock() -> Any:
    """Create a comprehensive mock for all API endpoints.

    Returns:
        Function that handles GET/POST requests to all API endpoints
    """

    def mock_api_call(url: str, *args: Any, **kwargs: Any) -> MagicMock:
        """Handle API calls and return appropriate mock responses."""
        mock_response = MagicMock()
        mock_response.ok = True

        # GET /hackathons - List hackathons
        if url.endswith("/hackathons") or ("/hackathons" in url and "/stats" not in url and "/jobs" not in url and "/analyze" not in url):
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "hackathons": [
                    {
                        "hack_id": "01HXXX111",
                        "name": "Spring Hackathon 2025",
                        "status": "configured",
                        "description": "Test hackathon",
                        "submission_count": 50,
                        "created_at": "2025-03-01T00:00:00Z"
                    },
                    {
                        "hack_id": "01HXXX222",
                        "name": "Summer Hackathon 2025",
                        "status": "configured",
                        "description": "Another test",
                        "submission_count": 25,
                        "created_at": "2025-06-01T00:00:00Z"
                    }
                ],
                "next_cursor": None,
                "has_more": False
            }

        # GET /hackathons/{id}/stats - Hackathon statistics
        elif "/stats" in url:
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "hack_id": "01HXXX111",
                "submission_count": 50,
                "verified_count": 45,
                "pending_count": 5,
                "participant_count": 150,
                "analysis_status": "not_started",
                "last_updated": "2025-03-04T12:00:00Z"
            }

        # GET /hackathons/{id}/analyze/status - Check for active job
        elif "/analyze/status" in url:
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "status": "not_started",
                "job_id": None
            }

        # POST /hackathons/{id}/analyze/estimate - Cost estimate
        elif "/estimate" in url:
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "estimate": {
                    "total_cost_usd": {
                        "expected": 1.25,
                        "min": 1.00,
                        "max": 1.50
                    },
                    "submission_count": 50,
                    "per_submission_cost": 0.025
                }
            }

        # POST /hackathons/{id}/analyze - Trigger analysis
        elif "/analyze" in url and kwargs.get("json") is not None:
            mock_response.status_code = 202
            mock_response.json.return_value = {
                "job_id": "01HYYY123456789",
                "estimated_cost_usd": 1.25,
                "status": "queued",
                "message": "Analysis job queued successfully"
            }

        # GET /hackathons/{id}/jobs/{job_id} - Job progress
        elif "/jobs/" in url:
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "job_id": "01HYYY123456789",
                "status": "running",
                "progress_percent": 45.5,
                "completed_submissions": 22,
                "failed_submissions": 1,
                "total_submissions": 50,
                "current_cost_usd": 0.55,
                "estimated_cost_usd": 1.25,
                "estimated_completion": "2025-03-04T13:30:00Z"
            }

        # Default fallback
        else:
            mock_response.status_code = 404
            mock_response.ok = False
            mock_response.json.return_value = {"detail": f"Endpoint not mocked: {url}"}

        return mock_response

    return mock_api_call
