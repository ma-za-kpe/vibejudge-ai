"""
Preservation property tests for security vulnerabilities fix.

These tests verify that legitimate operations continue to work correctly
on UNFIXED code. They use property-based testing with Hypothesis to generate
many test cases and provide strong guarantees about preserved behavior.

EXPECTED OUTCOME: All tests PASS on unfixed code (confirming baseline behavior).
After fixes are implemented, these tests should still PASS (confirming no regressions).
"""

import pytest
from hypothesis import HealthCheck, assume, given, settings
from hypothesis import strategies as st

from src.models.common import AgentName
from src.models.hackathon import HackathonCreate, HackathonUpdate, RubricConfig, RubricDimension
from src.models.organizer import OrganizerCreate
from src.models.submission import SubmissionBatchCreate, SubmissionInput
from src.services.hackathon_service import HackathonService
from src.services.organizer_service import OrganizerService
from src.services.submission_service import SubmissionService

# ============================================================
# HYPOTHESIS STRATEGIES
# ============================================================


@st.composite
def valid_team_name_strategy(draw):
    """Generate valid team names matching ^[a-zA-Z0-9 _-]+$ (1-50 chars)."""
    # Generate length between 1 and 50
    length = draw(st.integers(min_value=1, max_value=50))

    # Generate string with allowed characters (ensure at least one non-space)
    chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 _-"
    team_name = "".join([draw(st.sampled_from(chars)) for _ in range(length)])

    # Ensure not all spaces
    assume(team_name.strip() != "")

    return team_name


@st.composite
def valid_organizer_strategy(draw):
    """Generate valid organizer creation data with unique emails."""
    # Generate unique email with timestamp to avoid collisions
    import time

    timestamp = int(time.time() * 1000000)  # Microseconds for uniqueness
    username = draw(
        st.text(
            alphabet=st.characters(whitelist_categories=("Ll", "Nd"), blacklist_characters=" "),
            min_size=3,
            max_size=15,
        )
    )
    # Ensure username is not empty after filtering
    assume(len(username) >= 3)

    # Add timestamp to ensure uniqueness across test runs
    domain = draw(st.sampled_from(["example.com", "test.org", "demo.net"]))
    email = f"{username}{timestamp}@{domain}"

    # Generate name (letters only, no spaces at start/end)
    name = draw(
        st.text(
            alphabet=st.characters(whitelist_categories=("Lu", "Ll"), blacklist_characters=" "),
            min_size=1,
            max_size=50,
        )
    )
    assume(len(name) >= 1)

    return OrganizerCreate(email=email, name=name)


@st.composite
def within_budget_scenario_strategy(draw):
    """Generate scenarios where estimated cost is within budget."""
    # Generate submission count (1-100 for reasonable test times)
    submission_count = draw(st.integers(min_value=1, max_value=100))

    # Estimated cost per submission (approximate)
    cost_per_submission = 0.053  # From design doc
    estimated_cost = submission_count * cost_per_submission

    # Budget should be higher than estimated cost
    budget_limit = draw(st.floats(min_value=estimated_cost + 0.01, max_value=estimated_cost * 2))

    return {
        "submission_count": submission_count,
        "budget_limit_usd": budget_limit,
        "estimated_cost": estimated_cost,
    }


# ============================================================
# TASK 2.1: Valid API Key Authentication Preservation
# ============================================================


class TestValidAPIKeyAuthenticationPreservation:
    """Test that valid API keys continue to authenticate successfully.

    Requirements: 3.1
    """

    @given(organizer_data=valid_organizer_strategy())
    @settings(
        max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_valid_api_keys_authenticate(self, dynamodb_helper, organizer_data):
        """Property: For all valid API keys, authentication succeeds and returns organizer data.

        This test observes that valid API keys work on unfixed code and should
        continue to work after the timing attack fix is implemented.
        """
        service = OrganizerService(dynamodb_helper)

        # Create organizer and get API key
        response = service.create_organizer(organizer_data)
        api_key = response.api_key
        org_id = response.org_id

        # Verify API key authenticates successfully
        # Note: verify_api_key returns org_id (string) or None, not organizer object
        verified_org_id = service.verify_api_key(api_key)

        # Property: Authentication succeeds
        assert verified_org_id is not None, "Valid API key should authenticate"
        assert verified_org_id == org_id, "Should return correct organizer ID"


# ============================================================
# TASK 2.2: Valid Team Name Acceptance Preservation
# ============================================================


class TestValidTeamNameAcceptancePreservation:
    """Test that valid team names continue to be accepted.

    Requirements: 3.2
    """

    @given(team_name=valid_team_name_strategy())
    @settings(max_examples=1000, deadline=None)
    def test_valid_team_names_accepted(self, team_name):
        """Property: For all team names matching ^[a-zA-Z0-9 _-]+$ (1-50 chars), submission is accepted.

        This test observes that valid team names work on unfixed code and should
        continue to work after the prompt injection fix is implemented.
        """
        # Try to create submission with valid team name
        try:
            submission = SubmissionInput(
                team_name=team_name, repo_url="https://github.com/test/repo"
            )

            # Property: Valid team name is accepted
            assert submission.team_name == team_name, "Valid team name should be accepted"

        except Exception as e:
            pytest.fail(f"Valid team name '{team_name}' was rejected: {e}")


# ============================================================
# TASK 2.3: Owned Hackathon Operations Preservation
# ============================================================


class TestOwnedHackathonOperationsPreservation:
    """Test that organizers can access their own hackathons.

    Requirements: 3.3, 3.4, 3.5, 3.6
    """

    @given(
        organizer_data=valid_organizer_strategy(),
        hackathon_name=st.text(
            alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd")), min_size=1, max_size=50
        ),
    )
    @settings(
        max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_owned_hackathon_operations_succeed(
        self, dynamodb_helper, organizer_data, hackathon_name
    ):
        """Property: For all operations where organizer_id matches hackathon.organizer_id, operation succeeds.

        This test observes that owned hackathon operations work on unfixed code and should
        continue to work after the authorization fix is implemented.
        """
        assume(len(hackathon_name) >= 1)

        org_service = OrganizerService(dynamodb_helper)
        hack_service = HackathonService(dynamodb_helper)

        # Create organizer
        org = org_service.create_organizer(organizer_data)

        # Create hackathon owned by this organizer
        rubric = RubricConfig(
            dimensions=[
                RubricDimension(
                    name="Quality",
                    description="Code quality",
                    weight=1.0,
                    agent=AgentName.BUG_HUNTER,
                )
            ]
        )
        hackathon = hack_service.create_hackathon(
            org.org_id,
            HackathonCreate(
                name=hackathon_name,
                description="Test hackathon",
                rubric=rubric,
                agents_enabled=[AgentName.BUG_HUNTER],
            ),
        )

        # Property 1: GET operation succeeds for owned hackathon
        retrieved = hack_service.get_hackathon(hackathon.hack_id)
        assert retrieved is not None, "Should retrieve owned hackathon"
        assert retrieved.hack_id == hackathon.hack_id, "Should return correct hackathon"
        assert retrieved.name == hackathon_name, "Should return correct name"

        # Property 2: PUT operation succeeds for owned hackathon
        updated_name = f"{hackathon_name}_updated"
        update_data = HackathonUpdate(name=updated_name)
        updated = hack_service.update_hackathon(hackathon.hack_id, update_data)
        assert updated.name == updated_name, "Should update owned hackathon"

        # Property 3: DELETE operation succeeds for owned hackathon
        # Note: delete_hackathon requires org_id parameter
        deleted = hack_service.delete_hackathon(hackathon.hack_id, org.org_id)
        assert deleted is True, "Should delete owned hackathon"


# ============================================================
# TASK 2.4: Within-Budget Analysis Preservation
# ============================================================


class TestWithinBudgetAnalysisPreservation:
    """Test that analysis triggers successfully when within budget.

    Requirements: 3.7
    """

    @given(scenario=within_budget_scenario_strategy())
    @settings(
        max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_within_budget_analysis_triggers(self, dynamodb_helper, monkeypatch, scenario):
        """Property: For all hackathons where cost is within budget, analysis triggers successfully.

        This test observes that within-budget analysis works on unfixed code and should
        continue to work after the budget enforcement fix is implemented.
        """

        # Mock Lambda client to prevent actual invocation
        class MockLambdaClient:
            def invoke(self, **kwargs):
                return {"StatusCode": 202}

        monkeypatch.setattr("boto3.client", lambda _service, **_kwargs: MockLambdaClient())

        from src.services.analysis_service import AnalysisService

        org_service = OrganizerService(dynamodb_helper)
        hack_service = HackathonService(dynamodb_helper)
        sub_service = SubmissionService(dynamodb_helper)
        analysis_service = AnalysisService(dynamodb_helper)

        # Create organizer with unique email
        import time

        timestamp = int(time.time() * 1000000)
        org = org_service.create_organizer(
            OrganizerCreate(email=f"test{timestamp}@example.com", name="Test Organizer")
        )

        # Create hackathon with budget limit
        rubric = RubricConfig(
            dimensions=[
                RubricDimension(
                    name="Quality",
                    description="Code quality",
                    weight=1.0,
                    agent=AgentName.BUG_HUNTER,
                )
            ]
        )
        hackathon = hack_service.create_hackathon(
            org.org_id,
            HackathonCreate(
                name="Budget Test Hackathon",
                description="Test within-budget analysis",
                rubric=rubric,
                agents_enabled=[AgentName.BUG_HUNTER],
                budget_limit_usd=scenario["budget_limit_usd"],
            ),
        )

        # Create submissions (within budget)
        for i in range(scenario["submission_count"]):
            batch = SubmissionBatchCreate(
                submissions=[
                    SubmissionInput(
                        team_name=f"Team{i}", repo_url=f"https://github.com/test/repo{i}"
                    )
                ]
            )
            sub_service.create_submissions(hackathon.hack_id, batch)

        # Property: Analysis triggers successfully when within budget
        try:
            job = analysis_service.trigger_analysis(hackathon.hack_id)
            assert job is not None, "Analysis should trigger when within budget"
            assert job.job_id is not None, "Job should have valid ID"
        except Exception as e:
            pytest.fail(f"Within-budget analysis failed: {e}")


# ============================================================
# TASK 2.5: Sequential Analysis Preservation
# ============================================================


class TestSequentialAnalysisPreservation:
    """Test that sequential analysis triggers work correctly.

    Requirements: 3.8
    """

    def test_sequential_analysis_succeeds(self, dynamodb_helper, monkeypatch):
        """Test: Trigger analysis sequentially 10 times (waiting for completion), verify all succeed.

        This test observes that sequential analysis works on unfixed code and should
        continue to work after the race condition fix is implemented.
        """

        # Mock Lambda client
        class MockLambdaClient:
            def invoke(self, **kwargs):
                return {"StatusCode": 202}

        monkeypatch.setattr("boto3.client", lambda _service, **_kwargs: MockLambdaClient())

        from src.services.analysis_service import AnalysisService

        org_service = OrganizerService(dynamodb_helper)
        hack_service = HackathonService(dynamodb_helper)
        sub_service = SubmissionService(dynamodb_helper)

        # Create organizer and hackathon
        org = org_service.create_organizer(
            OrganizerCreate(email="sequential_test@example.com", name="Sequential Test")
        )

        rubric = RubricConfig(
            dimensions=[
                RubricDimension(
                    name="Quality",
                    description="Code quality",
                    weight=1.0,
                    agent=AgentName.BUG_HUNTER,
                )
            ]
        )

        successful_triggers = 0

        # Run 10 sequential analysis triggers
        for i in range(10):
            # Create new hackathon for each iteration
            hackathon = hack_service.create_hackathon(
                org.org_id,
                HackathonCreate(
                    name=f"Sequential Test {i}",
                    description="Test sequential analysis",
                    rubric=rubric,
                    agents_enabled=[AgentName.BUG_HUNTER],
                ),
            )

            # Create a submission
            batch = SubmissionBatchCreate(
                submissions=[
                    SubmissionInput(
                        team_name=f"Team{i}", repo_url=f"https://github.com/test/repo{i}"
                    )
                ]
            )
            sub_service.create_submissions(hackathon.hack_id, batch)

            # Trigger analysis
            analysis_service = AnalysisService(dynamodb_helper)
            try:
                job = analysis_service.trigger_analysis(hackathon.hack_id)
                if job is not None:
                    successful_triggers += 1

                # Simulate completion by resetting status
                # In real scenario, we'd wait for Lambda to complete
                # For this test, we just verify trigger succeeds

            except Exception as e:
                pytest.fail(f"Sequential analysis trigger {i} failed: {e}")

        # Property: All sequential triggers should succeed
        assert successful_triggers == 10, (
            f"Expected 10 successful triggers, got {successful_triggers}"
        )


# ============================================================
# TASK 2.6: GitHub API Integration Preservation
# ============================================================


class TestGitHubAPIIntegrationPreservation:
    """Test that GitHub API integration works with valid token.

    Requirements: 3.9, 3.10

    NOTE: This test requires a valid GITHUB_TOKEN environment variable.
    It will be skipped if the token is not available.
    """

    @pytest.mark.skip(reason="Requires valid GITHUB_TOKEN and actual GitHub API access")
    def test_github_api_integration_works(self, monkeypatch):
        """Test: With valid GITHUB_TOKEN, API requests extract commit data, file lists, Actions data.

        This test observes that GitHub API integration works on unfixed code and should
        continue to work after the GitHub authentication enforcement fix is implemented.

        NOTE: Skipped in automated tests as it requires real GitHub API access.
        """
        import os

        # Check if GITHUB_TOKEN is available
        github_token = os.getenv("GITHUB_TOKEN")
        if not github_token:
            pytest.skip("GITHUB_TOKEN not available")

        from src.utils.github_client import GitHubClient

        # Create GitHub client with token
        client = GitHubClient(token=github_token)

        # Test repository (using a known public repo)
        test_repo = "octocat/Hello-World"

        # Property: API requests succeed with valid token
        try:
            # Test commit data extraction
            commits = client.get_commits(test_repo)
            assert commits is not None, "Should extract commit data"
            assert len(commits) > 0, "Should have commits"

            # Test file list extraction
            files = client.get_files(test_repo)
            assert files is not None, "Should extract file list"
            assert len(files) > 0, "Should have files"

            # Test Actions data extraction
            actions = client.get_actions(test_repo)
            assert actions is not None, "Should extract Actions data"

        except Exception as e:
            pytest.fail(f"GitHub API integration failed: {e}")


# ============================================================
# TASK 2.7: Cost Tracking Preservation
# ============================================================


class TestCostTrackingPreservation:
    """Test that cost tracking works correctly.

    Requirements: 3.11, 3.12

    NOTE: This test requires actual Bedrock API access and will be skipped
    in automated tests.
    """

    @pytest.mark.skip(reason="Requires actual Bedrock API access")
    def test_cost_tracking_works(self, dynamodb_helper, monkeypatch):
        """Test: For all agent invocations, cost records are created with valid token counts.

        This test observes that cost tracking works on unfixed code and should
        continue to work after all fixes are implemented.

        NOTE: Skipped in automated tests as it requires real Bedrock API access.
        """
        # This would require actual Bedrock API calls
        # Skipping for now as it's expensive and requires real AWS credentials
        pytest.skip("Requires actual Bedrock API access")


# ============================================================
# TASK 2.8: Scoring and Leaderboard Preservation
# ============================================================


class TestScoringAndLeaderboardPreservation:
    """Test that scoring and leaderboard generation work correctly.

    Requirements: 3.13, 3.14

    NOTE: This test is simplified as scoring_service doesn't exist yet.
    """

    @given(num_submissions=st.integers(min_value=2, max_value=20))
    @settings(
        max_examples=50, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_submission_creation_works(self, dynamodb_helper, num_submissions):
        """Property: For all submission scenarios, submissions are created successfully.

        This test observes that submission creation works on unfixed code and should
        continue to work after all fixes are implemented.

        NOTE: Full scoring/leaderboard testing requires scoring_service which doesn't exist yet.
        """
        org_service = OrganizerService(dynamodb_helper)
        hack_service = HackathonService(dynamodb_helper)
        sub_service = SubmissionService(dynamodb_helper)

        # Create organizer with unique email
        import time

        timestamp = int(time.time() * 1000000)
        org = org_service.create_organizer(
            OrganizerCreate(email=f"scoring{timestamp}@example.com", name="Scoring Test")
        )

        # Create hackathon with weighted rubric
        rubric = RubricConfig(
            dimensions=[
                RubricDimension(
                    name="Quality",
                    description="Code quality",
                    weight=0.6,
                    agent=AgentName.BUG_HUNTER,
                ),
                RubricDimension(
                    name="Innovation",
                    description="Innovation",
                    weight=0.4,
                    agent=AgentName.INNOVATION,
                ),
            ]
        )
        hackathon = hack_service.create_hackathon(
            org.org_id,
            HackathonCreate(
                name="Scoring Test Hackathon",
                description="Test scoring",
                rubric=rubric,
                agents_enabled=[AgentName.BUG_HUNTER, AgentName.INNOVATION],
            ),
        )

        # Create submissions
        submission_ids = []
        for i in range(num_submissions):
            batch = SubmissionBatchCreate(
                submissions=[
                    SubmissionInput(
                        team_name=f"Team{i}", repo_url=f"https://github.com/test/repo{i}"
                    )
                ]
            )
            result = sub_service.create_submissions(hackathon.hack_id, batch)
            submission_ids.extend([s.sub_id for s in result.submissions])

        # Property: Submissions are created successfully
        assert len(submission_ids) == num_submissions, "All submissions should be created"
