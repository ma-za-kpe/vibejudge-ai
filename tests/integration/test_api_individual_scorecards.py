"""Integration tests for individual scorecards endpoint."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch

from src.api.main import app
from src.models.common import SubmissionStatus
from src.models.submission import SubmissionResponse, RepoMeta
from src.models.team_dynamics import (
    ContributorRole,
    ExpertiseArea,
    IndividualScorecard,
    WorkStyle,
    HiringSignals,
)


@pytest.fixture
def mock_services():
    """Mock all service dependencies."""
    with patch("src.api.dependencies.get_submission_service") as mock_sub_service, \
         patch("src.api.dependencies.get_hackathon_service") as mock_hack_service, \
         patch("src.api.dependencies.get_organizer_service") as mock_org_service:
        
        # Mock organizer service for auth
        org_service = MagicMock()
        org_service.verify_api_key.return_value = "org_123"
        org_service.get_organizer.return_value = MagicMock(
            org_id="org_123",
            email="test@example.com",
            model_dump=lambda: {"org_id": "org_123", "email": "test@example.com"}
        )
        mock_org_service.return_value = org_service
        
        # Mock hackathon service
        hack_service = MagicMock()
        hack_service.get_hackathon.return_value = MagicMock(
            hack_id="hack_123",
            org_id="org_123",
            name="Test Hackathon"
        )
        mock_hack_service.return_value = hack_service
        
        # Mock submission service
        sub_service = MagicMock()
        mock_sub_service.return_value = sub_service
        
        yield {
            "submission": sub_service,
            "hackathon": hack_service,
            "organizer": org_service,
        }


def test_get_individual_scorecards_success(mock_services):
    """Test successful retrieval of individual scorecards."""
    # Setup mock submission
    submission = SubmissionResponse(
        sub_id="sub_123",
        hack_id="hack_123",
        team_name="Test Team",
        repo_url="https://github.com/test/repo",
        status=SubmissionStatus.COMPLETED,
        overall_score=85.5,
        created_at="2024-01-01T00:00:00Z",
        updated_at="2024-01-01T00:00:00Z",
    )
    mock_services["submission"].get_submission.return_value = submission
    
    # Setup mock scorecards
    scorecards = [
        {
            "contributor_name": "Alice",
            "contributor_email": "alice@example.com",
            "role": "backend",
            "expertise_areas": ["database", "api"],
            "commit_count": 50,
            "lines_added": 1000,
            "lines_deleted": 200,
            "files_touched": ["src/api.py", "src/db.py"],
            "notable_contributions": ["Implemented authentication system"],
            "strengths": ["Strong backend skills", "Good code quality"],
            "weaknesses": ["Limited frontend experience"],
            "growth_areas": ["Learn React"],
            "work_style": {
                "commit_frequency": "frequent",
                "avg_commit_size": 50,
                "active_hours": [9, 10, 11, 14, 15, 16],
                "late_night_commits": 2,
                "weekend_commits": 5,
            },
            "hiring_signals": {
                "recommended_role": "Backend Engineer",
                "seniority_level": "mid",
                "salary_range_usd": "$80k-$100k",
                "must_interview": True,
                "sponsor_interest": ["TechCorp"],
                "rationale": "Strong backend skills with production experience",
            },
        }
    ]
    mock_services["submission"].get_individual_scorecards.return_value = scorecards
    
    # Make request
    client = TestClient(app)
    response = client.get(
        "/api/v1/submissions/sub_123/individual-scorecards",
        headers={"X-API-Key": "test_key"}
    )
    
    # Verify response
    assert response.status_code == 200
    data = response.json()
    assert data["sub_id"] == "sub_123"
    assert data["hack_id"] == "hack_123"
    assert data["team_name"] == "Test Team"
    assert data["total_count"] == 1
    assert len(data["scorecards"]) == 1
    assert data["scorecards"][0]["contributor_name"] == "Alice"


def test_get_individual_scorecards_not_found(mock_services):
    """Test 404 when submission not found."""
    mock_services["submission"].get_submission.return_value = None
    
    client = TestClient(app)
    response = client.get(
        "/api/v1/submissions/sub_999/individual-scorecards",
        headers={"X-API-Key": "test_key"}
    )
    
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_get_individual_scorecards_forbidden(mock_services):
    """Test 403 when organizer doesn't own the hackathon."""
    # Setup submission with different org_id
    submission = SubmissionResponse(
        sub_id="sub_123",
        hack_id="hack_123",
        team_name="Test Team",
        repo_url="https://github.com/test/repo",
        status=SubmissionStatus.COMPLETED,
        created_at="2024-01-01T00:00:00Z",
        updated_at="2024-01-01T00:00:00Z",
    )
    mock_services["submission"].get_submission.return_value = submission
    
    # Hackathon owned by different organizer
    mock_services["hackathon"].get_hackathon.return_value = MagicMock(
        hack_id="hack_123",
        org_id="org_999",  # Different org
        name="Test Hackathon"
    )
    
    client = TestClient(app)
    response = client.get(
        "/api/v1/submissions/sub_123/individual-scorecards",
        headers={"X-API-Key": "test_key"}
    )
    
    assert response.status_code == 403
    assert "permission" in response.json()["detail"].lower()


def test_get_individual_scorecards_no_auth(mock_services):
    """Test 401 when no API key provided."""
    client = TestClient(app)
    response = client.get("/api/v1/submissions/sub_123/individual-scorecards")
    
    assert response.status_code == 401


def test_get_individual_scorecards_empty(mock_services):
    """Test successful response with empty scorecards."""
    submission = SubmissionResponse(
        sub_id="sub_123",
        hack_id="hack_123",
        team_name="Test Team",
        repo_url="https://github.com/test/repo",
        status=SubmissionStatus.COMPLETED,
        created_at="2024-01-01T00:00:00Z",
        updated_at="2024-01-01T00:00:00Z",
    )
    mock_services["submission"].get_submission.return_value = submission
    mock_services["submission"].get_individual_scorecards.return_value = []
    
    client = TestClient(app)
    response = client.get(
        "/api/v1/submissions/sub_123/individual-scorecards",
        headers={"X-API-Key": "test_key"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] == 0
    assert data["scorecards"] == []
