"""
E2E tests for Category 3: Submission Management Flows (6 flows).

Tests:
- 3.1: Public Submission Flow (participant)
- 3.2: Submission Verification Flow (organizer)
- 3.3: Submission Rejection Flow (organizer)
- 3.4: Submission Filtering Flow
- 3.5: Bulk Submission Actions Flow
- 3.6: Submission Export Flow
"""

import pytest
from pages.submissions_page import SubmissionsPage
from pages.submit_page import SubmitPage
from playwright.sync_api import Page


@pytest.mark.critical
def test_public_submission_flow(page: Page, mock_api):
    """Test Flow 3.1: Public Submission Flow (participant perspective)."""
    hack_id = "test_hack_001"

    # Mock hackathons list and submission creation
    mock_api.mock_hackathons_list(
        [{"hack_id": hack_id, "name": "Test Hackathon", "status": "active"}]
    )
    mock_api.mock_post(
        f"**/hackathons/{hack_id}/submissions",
        status=201,
        body={"sub_id": "sub_001", "team_name": "E2E Test Team", "status": "pending"},
    )

    submit_page = SubmitPage(page)
    submit_page.navigate()

    # Select hackathon
    submit_page.select_hackathon("Test Hackathon")

    # Fill submission form
    submit_page.fill_team_name("E2E Test Team")
    submit_page.fill_repository_url("https://github.com/test/repo")
    submit_page.fill_email("test@example.com")
    submit_page.fill_description("Test project for E2E testing")

    # Add team members
    submit_page.add_team_member("Alice", "alice_gh")
    submit_page.add_team_member("Bob", "bob_gh")

    assert submit_page.get_team_member_count() == 2

    # Accept terms
    if submit_page.has_confirmation_checkbox():
        submit_page.accept_terms()

    # Submit
    submit_page.submit()

    # Verify success
    submit_page.assert_submission_success()
    sub_id = submit_page.get_submission_id()
    assert sub_id == "sub_001"


@pytest.mark.smoke
def test_submission_validation_errors(page: Page, mock_api):
    """Test Flow 3.1: Submission form validation."""
    hack_id = "test_hack_001"

    mock_api.mock_hackathons_list(
        [{"hack_id": hack_id, "name": "Test Hackathon", "status": "active"}]
    )

    submit_page = SubmitPage(page)
    submit_page.navigate()
    submit_page.select_hackathon("Test Hackathon")

    # Try to submit without required fields
    submit_page.submit()

    # Should show validation errors
    submit_page.assert_required_field_error("Team Name")


@pytest.mark.smoke
def test_duplicate_submission_error(page: Page, mock_api):
    """Test Flow 3.1: Duplicate submission error."""
    hack_id = "test_hack_001"

    mock_api.mock_hackathons_list(
        [{"hack_id": hack_id, "name": "Test Hackathon", "status": "active"}]
    )

    # Mock 409 conflict (duplicate submission)
    mock_api.mock_post(
        f"**/hackathons/{hack_id}/submissions",
        status=409,
        body={"detail": "Team has already submitted to this hackathon"},
    )

    submit_page = SubmitPage(page)
    submit_page.navigate()
    submit_page.select_hackathon("Test Hackathon")

    submit_page.fill_team_name("Duplicate Team")
    submit_page.fill_repository_url("https://github.com/test/repo")
    submit_page.fill_email("test@example.com")
    submit_page.fill_description("Test")

    submit_page.submit()

    # Should show duplicate error
    submit_page.assert_duplicate_submission_error()


@pytest.mark.critical
def test_submission_verification_flow(authenticated_page: Page, mock_api):
    """Test Flow 3.2: Submission Verification Flow (organizer)."""
    hack_id = "test_hack_001"

    mock_api.mock_hackathons_list(
        [{"hack_id": hack_id, "name": "Test Hackathon", "status": "active"}]
    )

    # Mock submissions list with pending submission
    mock_api.mock_get(
        f"**/hackathons/{hack_id}/submissions",
        status=200,
        body={
            "submissions": [
                {
                    "sub_id": "sub_001",
                    "team_name": "Team Alpha",
                    "status": "pending",
                    "created_at": "2025-03-01T10:00:00Z",
                }
            ]
        },
    )

    # Mock verification endpoint
    mock_api.mock_post(
        f"**/hackathons/{hack_id}/submissions/sub_001/verify",
        status=200,
        body={"sub_id": "sub_001", "status": "verified"},
    )

    submissions = SubmissionsPage(authenticated_page)
    submissions.navigate()
    submissions.select_hackathon("Test Hackathon")

    # Verify first submission
    submissions.verify_submission(0)

    # Should show success
    submissions.assert_verification_success()


@pytest.mark.critical
def test_submission_rejection_flow(authenticated_page: Page, mock_api):
    """Test Flow 3.3: Submission Rejection Flow."""
    hack_id = "test_hack_001"

    mock_api.mock_hackathons_list(
        [{"hack_id": hack_id, "name": "Test Hackathon", "status": "active"}]
    )

    mock_api.mock_get(
        f"**/hackathons/{hack_id}/submissions",
        status=200,
        body={
            "submissions": [
                {
                    "sub_id": "sub_002",
                    "team_name": "Team Beta",
                    "status": "pending",
                    "created_at": "2025-03-01T11:00:00Z",
                }
            ]
        },
    )

    # Mock rejection endpoint
    mock_api.mock_post(
        f"**/hackathons/{hack_id}/submissions/sub_002/reject",
        status=200,
        body={"sub_id": "sub_002", "status": "rejected"},
    )

    submissions = SubmissionsPage(authenticated_page)
    submissions.navigate()
    submissions.select_hackathon("Test Hackathon")

    # Reject submission with reason
    submissions.reject_submission(0, reason="Repository is empty")

    # Should show success
    submissions.assert_rejection_success()


@pytest.mark.smoke
def test_submission_filtering_flow(authenticated_page: Page, mock_api):
    """Test Flow 3.4: Submission Filtering Flow."""
    hack_id = "test_hack_001"

    mock_api.mock_hackathons_list(
        [{"hack_id": hack_id, "name": "Test Hackathon", "status": "active"}]
    )

    # Mock mixed submissions
    mock_api.mock_get(
        f"**/hackathons/{hack_id}/submissions",
        status=200,
        body={
            "submissions": [
                {"sub_id": "sub_001", "team_name": "Team 1", "status": "verified"},
                {"sub_id": "sub_002", "team_name": "Team 2", "status": "pending"},
                {"sub_id": "sub_003", "team_name": "Team 3", "status": "verified"},
            ]
        },
    )

    submissions = SubmissionsPage(authenticated_page)
    submissions.navigate()
    submissions.select_hackathon("Test Hackathon")

    # Initial: all 3 visible
    initial_count = submissions.get_submission_count()
    assert initial_count == 3

    # Filter by verified
    submissions.filter_by_verification(verified=True)

    # Should show 2 verified
    filtered_count = submissions.get_submission_count()
    assert filtered_count == 2, f"Expected 2 verified submissions, got {filtered_count}"


@pytest.mark.critical
def test_bulk_submission_actions_flow(authenticated_page: Page, mock_api):
    """Test Flow 3.5: Bulk Submission Actions Flow."""
    hack_id = "test_hack_001"

    mock_api.mock_hackathons_list(
        [{"hack_id": hack_id, "name": "Test Hackathon", "status": "active"}]
    )

    mock_api.mock_get(
        f"**/hackathons/{hack_id}/submissions",
        status=200,
        body={
            "submissions": [
                {"sub_id": "sub_001", "team_name": "Team 1", "status": "pending"},
                {"sub_id": "sub_002", "team_name": "Team 2", "status": "pending"},
                {"sub_id": "sub_003", "team_name": "Team 3", "status": "pending"},
            ]
        },
    )

    # Mock bulk verify
    mock_api.mock_post(
        f"**/hackathons/{hack_id}/submissions/bulk/verify", status=200, body={"verified_count": 2}
    )

    submissions = SubmissionsPage(authenticated_page)
    submissions.navigate()
    submissions.select_hackathon("Test Hackathon")

    # Select 2 submissions
    submissions.select_submission(0)
    submissions.select_submission(1)

    selected_count = submissions.get_selected_count()
    assert selected_count == 2

    # Bulk verify
    submissions.bulk_verify()

    # Should show success
    submissions.assert_verification_success()


@pytest.mark.smoke
def test_submission_export_flow(authenticated_page: Page, mock_api):
    """Test Flow 3.6: Submission Export Flow."""
    hack_id = "test_hack_001"

    mock_api.mock_hackathons_list(
        [{"hack_id": hack_id, "name": "Test Hackathon", "status": "active"}]
    )

    mock_api.mock_get(
        f"**/hackathons/{hack_id}/submissions",
        status=200,
        body={
            "submissions": [
                {"sub_id": "sub_001", "team_name": "Team 1", "status": "verified"},
            ]
        },
    )

    submissions = SubmissionsPage(authenticated_page)
    submissions.navigate()
    submissions.select_hackathon("Test Hackathon")

    # Export as CSV
    submissions.export_submissions(format="csv")

    # Should trigger download (no error)
    # In real browser automation, we'd verify download file


@pytest.mark.smoke
def test_submissions_empty_state(authenticated_page: Page, mock_api):
    """Test empty state: No submissions."""
    hack_id = "test_hack_001"

    mock_api.mock_hackathons_list(
        [{"hack_id": hack_id, "name": "Test Hackathon", "status": "active"}]
    )

    mock_api.mock_get(f"**/hackathons/{hack_id}/submissions", status=200, body={"submissions": []})

    submissions = SubmissionsPage(authenticated_page)
    submissions.navigate()
    submissions.select_hackathon("Test Hackathon")

    # Should show empty state
    submissions.assert_no_submissions_message()

    count = submissions.get_submission_count()
    assert count == 0
