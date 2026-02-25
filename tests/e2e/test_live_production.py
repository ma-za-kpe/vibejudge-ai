"""End-to-End Test for VibeJudge AI Live Production API.

Tests the complete user flow against the live API:
1. Register organizer → get API key
2. Create hackathon with rubric
3. Submit GitHub repositories (batch)
4. Trigger analysis
5. Poll for completion (max 10 minutes)
6. GET /submissions/{sub_id}/scorecard → Validate human-centric intelligence fields
7. GET /submissions/{sub_id}/individual-scorecards → Check endpoint
8. GET /hackathons/{hack_id}/intelligence → Check dashboard

Live API: https://2nu0j4n648.execute-api.us-east-1.amazonaws.com/dev
Docs: https://2nu0j4n648.execute-api.us-east-1.amazonaws.com/dev/docs
"""

import time
from datetime import UTC, datetime, timedelta

import httpx
import pytest

# Configuration
BASE_URL = "https://2nu0j4n648.execute-api.us-east-1.amazonaws.com/dev/api/v1"
TIMEOUT = 30.0
MAX_POLL_MINUTES = 10

# Test repositories with CI/CD
TEST_REPOS = [
    {
        "team_name": "VibeJudge Team",
        "repo_url": "https://github.com/ma-za-kpe/vibejudge-ai",
    },
    {
        "team_name": "Flask Team",
        "repo_url": "https://github.com/pallets/flask",
    },
]


class TestLiveProduction:
    """End-to-end test suite for live production API."""

    @pytest.fixture(scope="class")
    def http_client(self) -> httpx.Client:
        """Create HTTP client for API requests."""
        return httpx.Client(base_url=BASE_URL, timeout=TIMEOUT)

    @pytest.fixture(scope="class")
    def organizer_credentials(self, http_client: httpx.Client) -> dict[str, str]:
        """Register organizer and return credentials."""
        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        org_data = {
            "name": f"E2E Test Org {timestamp}",
            "email": f"test+{timestamp}@vibejudge.ai",
            "organization": "E2E Testing",
        }

        response = http_client.post("/organizers", json=org_data)
        assert response.status_code == 201, f"Failed to register: {response.text}"

        data = response.json()
        assert "org_id" in data, "Missing org_id in response"
        assert "api_key" in data, "Missing api_key in response"

        print(f"\n✅ Organizer registered: {data['org_id']}")
        return {"org_id": data["org_id"], "api_key": data["api_key"]}

    @pytest.fixture(scope="class")
    def hackathon_id(self, http_client: httpx.Client, organizer_credentials: dict[str, str]) -> str:
        """Create hackathon and return hack_id."""
        headers = {"X-API-Key": organizer_credentials["api_key"]}
        start_date = datetime.now(UTC)
        end_date = start_date + timedelta(days=2)

        hackathon_data = {
            "name": f"E2E Test Hackathon {start_date.strftime('%Y%m%d_%H%M%S')}",
            "description": "E2E test hackathon for human-centric intelligence validation",
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "rubric": {
                "name": "E2E Test Rubric",
                "dimensions": [
                    {"name": "Code Quality", "agent": "bug_hunter", "weight": 0.25},
                    {"name": "Performance", "agent": "performance", "weight": 0.30},
                    {"name": "Innovation", "agent": "innovation", "weight": 0.30},
                    {"name": "Authenticity", "agent": "ai_detection", "weight": 0.15},
                ],
            },
            "agents_enabled": ["bug_hunter", "performance", "innovation", "ai_detection"],
            "ai_policy_mode": "ai_assisted",
            "budget_limit_usd": 10.0,
        }

        response = http_client.post("/hackathons", headers=headers, json=hackathon_data)
        assert response.status_code == 201, f"Failed to create hackathon: {response.text}"

        data = response.json()
        assert "hack_id" in data, "Missing hack_id in response"

        print(f"✅ Hackathon created: {data['hack_id']}")
        return data["hack_id"]

    @pytest.fixture(scope="class")
    def submission_ids(
        self,
        http_client: httpx.Client,
        organizer_credentials: dict[str, str],
        hackathon_id: str,
    ) -> list[str]:
        """Submit repositories and return submission IDs."""
        headers = {"X-API-Key": organizer_credentials["api_key"]}

        submissions_data = {
            "submissions": [
                {"team_name": repo["team_name"], "repo_url": repo["repo_url"]}
                for repo in TEST_REPOS
            ]
        }

        response = http_client.post(
            f"/hackathons/{hackathon_id}/submissions",
            headers=headers,
            json=submissions_data,
        )
        assert response.status_code == 201, f"Failed to submit repos: {response.text}"

        data = response.json()
        assert "created" in data, "Missing created count in response"
        assert data["created"] == len(TEST_REPOS), "Not all submissions created"

        # Get submission IDs from the response
        submissions = data.get("submissions", [])
        sub_ids = [s["sub_id"] for s in submissions]

        assert len(sub_ids) == len(TEST_REPOS), "Missing submission IDs"

        print(f"✅ Submissions created: {len(sub_ids)}")
        for sub_id in sub_ids:
            print(f"   - {sub_id}")

        return sub_ids

    def test_01_trigger_analysis(
        self,
        http_client: httpx.Client,
        organizer_credentials: dict[str, str],
        hackathon_id: str,
        submission_ids: list[str],
    ) -> None:
        """Test triggering batch analysis."""
        headers = {"X-API-Key": organizer_credentials["api_key"]}

        response = http_client.post(
            f"/hackathons/{hackathon_id}/analyze",
            headers=headers,
            json={},  # Empty body triggers analysis for all submissions
        )

        assert response.status_code == 202, f"Failed to trigger analysis: {response.text}"

        data = response.json()
        assert "status" in data, "Missing status in response"
        print(f"✅ Analysis triggered: {data.get('status')}")

    def test_02_poll_until_complete(
        self,
        http_client: httpx.Client,
        organizer_credentials: dict[str, str],
        submission_ids: list[str],
    ) -> None:
        """Test polling submission status until all analyzed."""
        headers = {"X-API-Key": organizer_credentials["api_key"]}
        start_time = time.time()
        max_wait_seconds = MAX_POLL_MINUTES * 60

        print(f"\n⏳ Polling every 30 seconds (max {MAX_POLL_MINUTES} minutes)...")

        while (time.time() - start_time) < max_wait_seconds:
            all_complete = True
            statuses = []

            for sub_id in submission_ids:
                response = http_client.get(f"/submissions/{sub_id}", headers=headers)
                assert response.status_code == 200, f"Failed to get status: {response.text}"

                data = response.json()
                status = data.get("status", "unknown")
                statuses.append(f"{sub_id[:8]}: {status}")

                if status not in ["completed", "failed", "disqualified"]:
                    all_complete = False

            elapsed = int(time.time() - start_time)
            print(f"[{elapsed}s] {', '.join(statuses)}")

            if all_complete:
                print(f"✅ All submissions analyzed in {elapsed}s")
                return

            time.sleep(30)

        pytest.fail(f"Timeout: Analysis did not complete in {MAX_POLL_MINUTES} minutes")

    def test_03_validate_scorecard_human_centric_fields(
        self,
        http_client: httpx.Client,
        organizer_credentials: dict[str, str],
        submission_ids: list[str],
    ) -> None:
        """Test GET /submissions/{sub_id}/scorecard - validate human-centric intelligence fields.

        CRITICAL TEST: This validates that team_dynamics, strategy_analysis, and
        actionable_feedback are populated in production.
        """
        headers = {"X-API-Key": organizer_credentials["api_key"]}

        for sub_id in submission_ids:
            print(f"\n📊 Validating scorecard for {sub_id[:8]}...")

            response = http_client.get(f"/submissions/{sub_id}/scorecard", headers=headers)
            assert response.status_code == 200, f"Failed to get scorecard: {response.text}"

            scorecard = response.json()

            # Core platform validation (should pass)
            assert scorecard["status"] == "completed", f"Status: {scorecard['status']}"
            assert scorecard["overall_score"] > 0, "Overall score is 0"
            assert len(scorecard.get("agent_scores", [])) >= 4, "Missing agent scores"

            print(
                f"✅ Core platform: status={scorecard['status']}, score={scorecard['overall_score']:.2f}"
            )

            # Human-centric intelligence validation (CRITICAL - currently FAILING in production)
            team_dynamics = scorecard.get("team_dynamics")
            strategy_analysis = scorecard.get("strategy_analysis")
            actionable_feedback = scorecard.get("actionable_feedback", [])

            # Detailed diagnostics
            print("\n🔍 Human-Centric Intelligence Fields:")
            print(f"   team_dynamics: {type(team_dynamics).__name__} = {team_dynamics is not None}")
            print(
                f"   strategy_analysis: {type(strategy_analysis).__name__} = {strategy_analysis is not None}"
            )
            print(
                f"   actionable_feedback: {type(actionable_feedback).__name__} (len={len(actionable_feedback)})"
            )

            # CRITICAL ASSERTIONS
            assert team_dynamics is not None, (
                "❌ DEPLOYMENT GAP: team_dynamics is null! "
                "TeamAnalyzer results not being stored in DynamoDB."
            )

            assert strategy_analysis is not None, (
                "❌ DEPLOYMENT GAP: strategy_analysis is null! "
                "StrategyDetector results not being stored in DynamoDB."
            )

            assert len(actionable_feedback) > 0, (
                "❌ DEPLOYMENT GAP: actionable_feedback is empty! "
                "BrandVoiceTransformer results not being stored in DynamoDB."
            )

            # Validate team_dynamics structure
            if team_dynamics:
                assert "workload_distribution" in team_dynamics, "Missing workload_distribution"
                assert "team_dynamics_grade" in team_dynamics, "Missing team_dynamics_grade"
                assert "red_flags" in team_dynamics, "Missing red_flags"
                print(
                    f"✅ team_dynamics: grade={team_dynamics.get('team_dynamics_grade')}, red_flags={len(team_dynamics.get('red_flags', []))}"
                )

            # Validate strategy_analysis structure
            if strategy_analysis:
                assert "test_strategy" in strategy_analysis, "Missing test_strategy"
                assert "maturity_level" in strategy_analysis, "Missing maturity_level"
                print(f"✅ strategy_analysis: maturity={strategy_analysis.get('maturity_level')}")

            # Validate actionable_feedback structure
            if actionable_feedback:
                first_feedback = actionable_feedback[0]
                assert "finding" in first_feedback, "Missing finding in feedback"
                assert "effort_estimate" in first_feedback, "Missing effort_estimate"
                print(f"✅ actionable_feedback: {len(actionable_feedback)} items")

    def test_04_validate_individual_scorecards_endpoint(
        self,
        http_client: httpx.Client,
        organizer_credentials: dict[str, str],
        submission_ids: list[str],
    ) -> None:
        """Test GET /submissions/{sub_id}/individual-scorecards endpoint."""
        headers = {"X-API-Key": organizer_credentials["api_key"]}

        for sub_id in submission_ids[:1]:  # Test first submission only
            print(f"\n👥 Validating individual scorecards for {sub_id[:8]}...")

            response = http_client.get(
                f"/submissions/{sub_id}/individual-scorecards", headers=headers
            )

            # Check if endpoint exists
            if response.status_code == 404:
                pytest.fail(
                    "❌ DEPLOYMENT GAP: /individual-scorecards endpoint not found! "
                    "Route may not be registered in production."
                )

            assert response.status_code == 200, f"Failed to get scorecards: {response.text}"

            data = response.json()
            assert "scorecards" in data, "Missing scorecards field"
            assert "total_count" in data, "Missing total_count field"

            scorecards = data["scorecards"]
            print(f"✅ Individual scorecards: {len(scorecards)} contributors")

            # Validate scorecard structure if any exist
            if scorecards:
                first_scorecard = scorecards[0]
                assert "contributor_name" in first_scorecard, "Missing contributor_name"
                assert "role" in first_scorecard, "Missing role"
                assert "hiring_signals" in first_scorecard, "Missing hiring_signals"
                print(
                    f"   Sample: {first_scorecard.get('contributor_name')} - {first_scorecard.get('role')}"
                )

    def test_05_validate_intelligence_dashboard_endpoint(
        self,
        http_client: httpx.Client,
        organizer_credentials: dict[str, str],
        hackathon_id: str,
    ) -> None:
        """Test GET /hackathons/{hack_id}/intelligence endpoint."""
        headers = {"X-API-Key": organizer_credentials["api_key"]}

        print(f"\n📈 Validating intelligence dashboard for {hackathon_id[:8]}...")

        response = http_client.get(f"/hackathons/{hackathon_id}/intelligence", headers=headers)

        # Check if endpoint exists
        if response.status_code == 404:
            pytest.fail(
                "❌ DEPLOYMENT GAP: /intelligence endpoint not found! "
                "Route may not be registered in production."
            )

        assert response.status_code == 200, f"Failed to get dashboard: {response.text}"

        dashboard = response.json()

        # Validate dashboard structure
        assert "hack_id" in dashboard, "Missing hack_id"
        assert "total_submissions" in dashboard, "Missing total_submissions"
        assert "hiring_intelligence" in dashboard, "Missing hiring_intelligence"
        assert "technology_trends" in dashboard, "Missing technology_trends"
        assert "common_issues" in dashboard, "Missing common_issues"

        print("✅ Intelligence dashboard retrieved")
        print(f"   Total submissions: {dashboard.get('total_submissions')}")
        print(f"   Common issues: {len(dashboard.get('common_issues', []))}")

        # Validate hiring intelligence structure
        hiring = dashboard.get("hiring_intelligence", {})
        if hiring:
            must_interview = hiring.get("must_interview", [])
            print(f"   Must interview: {len(must_interview)} candidates")

    def test_06_validate_cost_tracking(
        self,
        http_client: httpx.Client,
        organizer_credentials: dict[str, str],
        submission_ids: list[str],
    ) -> None:
        """Test cost tracking and validate 42% cost reduction target."""
        headers = {"X-API-Key": organizer_credentials["api_key"]}
        total_cost = 0.0

        print("\n💰 Validating cost tracking...")

        for sub_id in submission_ids:
            response = http_client.get(f"/submissions/{sub_id}", headers=headers)
            assert response.status_code == 200, f"Failed to get submission: {response.text}"

            data = response.json()
            cost = data.get("total_cost_usd", 0.0)
            tokens = data.get("total_tokens", 0)
            total_cost += cost

            print(f"   {sub_id[:8]}: ${cost:.4f} ({tokens:,} tokens)")

        # Validate cost reduction target (42% from requirements)
        baseline_cost_per_submission = 0.108440  # Original cost per submission
        avg_cost = total_cost / len(submission_ids)
        reduction = ((baseline_cost_per_submission - avg_cost) / baseline_cost_per_submission) * 100

        print(f"\n✅ Total cost: ${total_cost:.4f}")
        print(f"   Avg per submission: ${avg_cost:.4f}")
        print(f"   Cost reduction: {reduction:.1f}%")

        assert reduction >= 30, f"Cost reduction {reduction:.1f}% below 30% minimum target"

        if reduction >= 42:
            print("🎯 Cost reduction target (42%) exceeded!")


# Standalone execution for manual testing
if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
