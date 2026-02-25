"""Property-based tests for Live Dashboard page.

Feature: streamlit-organizer-dashboard
Tests universal properties of Live Dashboard behavior using Hypothesis.
"""

from typing import Any
from unittest.mock import Mock, patch

from components.api_client import APIClient
from hypothesis import given
from hypothesis import strategies as st


# Custom strategies for hackathon data
@st.composite
def valid_hackathon_list(draw: Any) -> list[dict[str, Any]]:
    """Generate a list of valid hackathon dictionaries.

    Each hackathon has:
    - hack_id: ULID string
    - name: Non-empty string (1-200 chars)
    - description: Optional string
    - status: One of active, completed, draft
    """
    # Generate 1-20 hackathons
    num_hackathons = draw(st.integers(min_value=1, max_value=20))

    hackathons = []
    for _i in range(num_hackathons):
        hackathon = {
            "hack_id": draw(st.from_regex(r"01[A-Z0-9]{24}", fullmatch=True)),
            "name": draw(
                st.text(
                    min_size=1,
                    max_size=200,
                    alphabet=st.characters(
                        blacklist_categories=("Cs", "Cc"),
                        blacklist_characters=("\x00", "\n", "\r", "\t"),
                    ),
                )
            ),
            "description": draw(st.one_of(st.none(), st.text(max_size=500))),
            "status": draw(st.sampled_from(["active", "completed", "draft"])),
        }
        hackathons.append(hackathon)

    return hackathons


class TestDropdownPopulationProperty:
    """Property 8: Dropdown Population

    **Validates: Requirements 3.1**

    For any list of hackathons returned from GET /hackathons, the dropdown
    should contain all hackathon names as options.
    """

    @given(
        hackathons=valid_hackathon_list(),
        base_url=st.from_regex(r"https?://[a-z0-9\-\.]+(?::\d+)?", fullmatch=True),
        api_key=st.text(min_size=1, max_size=100),
    )
    @patch("components.api_client.requests.Session")
    def test_dropdown_contains_all_hackathon_names(
        self,
        mock_session_class: Mock,
        hackathons: list[dict[str, Any]],
        base_url: str,
        api_key: str,
    ) -> None:
        """
        Property: For any list of hackathons returned from the API, the dropdown
        should contain all unique hackathon names as options.

        This test verifies that:
        1. All unique hackathon names from the API response are present in dropdown options
        2. The dropdown has the correct number of unique options
        3. Each hackathon name appears exactly once (duplicates are handled by dict)

        Args:
            mock_session_class: Mocked requests.Session class
            hackathons: Generated list of hackathon dictionaries
            base_url: Generated base URL string
            api_key: Generated API key string
        """
        # Arrange: Mock session instance and response
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = hackathons
        mock_session.get.return_value = mock_response

        # Act: Fetch hackathons using APIClient
        client = APIClient(base_url, api_key)
        response = client.get("/hackathons")

        # Simulate dropdown population logic
        # In the actual page, this is: hackathon_options = {h["name"]: h["hack_id"] for h in hackathons}
        hackathon_options = {h["name"]: h["hack_id"] for h in response}
        dropdown_names = list(hackathon_options.keys())

        # Assert: All unique hackathon names are in the dropdown
        # Note: If there are duplicate names, dict will only keep the last one
        unique_names = {h["name"] for h in hackathons}

        assert len(dropdown_names) == len(unique_names), (
            f"Dropdown should have {len(unique_names)} unique options, but has {len(dropdown_names)}"
        )

        for expected_name in unique_names:
            assert expected_name in dropdown_names, (
                f"Hackathon name '{expected_name}' should be in dropdown options"
            )

        # Assert: No extra names in dropdown
        for dropdown_name in dropdown_names:
            assert dropdown_name in unique_names, (
                f"Dropdown contains unexpected name '{dropdown_name}'"
            )

    @given(
        hackathons=valid_hackathon_list(),
        base_url=st.from_regex(r"https?://[a-z0-9\-\.]+(?::\d+)?", fullmatch=True),
        api_key=st.text(min_size=1, max_size=100),
    )
    @patch("components.api_client.requests.Session")
    def test_dropdown_maps_names_to_hack_ids_correctly(
        self,
        mock_session_class: Mock,
        hackathons: list[dict[str, Any]],
        base_url: str,
        api_key: str,
    ) -> None:
        """
        Property: For any list of hackathons, the dropdown should correctly map
        each hackathon name to its corresponding hack_id (last one wins for duplicates).

        This test verifies that:
        1. Each name in the dropdown maps to a hack_id from the API response
        2. For duplicate names, the last hackathon's hack_id is used (dict behavior)
        3. All mappings are valid

        Args:
            mock_session_class: Mocked requests.Session class
            hackathons: Generated list of hackathon dictionaries
            base_url: Generated base URL string
            api_key: Generated API key string
        """
        # Arrange: Mock session instance and response
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = hackathons
        mock_session.get.return_value = mock_response

        # Act: Fetch hackathons and create dropdown mapping
        client = APIClient(base_url, api_key)
        response = client.get("/hackathons")

        # Simulate dropdown mapping logic
        hackathon_options = {h["name"]: h["hack_id"] for h in response}

        # Build expected mapping (last one wins for duplicate names)
        expected_mapping = {}
        for hackathon in hackathons:
            expected_mapping[hackathon["name"]] = hackathon["hack_id"]

        # Assert: Dropdown mapping matches expected mapping
        assert hackathon_options == expected_mapping, (
            "Dropdown mapping should match expected mapping"
        )

        # Assert: All hack_ids in dropdown are valid (from the API response)
        valid_hack_ids = {h["hack_id"] for h in hackathons}
        for name, hack_id in hackathon_options.items():
            assert hack_id in valid_hack_ids, (
                f"Dropdown maps '{name}' to invalid hack_id '{hack_id}'"
            )

    @given(
        hackathons=valid_hackathon_list(),
        base_url=st.from_regex(r"https?://[a-z0-9\-\.]+(?::\d+)?", fullmatch=True),
        api_key=st.text(min_size=1, max_size=100),
    )
    @patch("components.api_client.requests.Session")
    def test_dropdown_preserves_order_of_hackathons(
        self,
        mock_session_class: Mock,
        hackathons: list[dict[str, Any]],
        base_url: str,
        api_key: str,
    ) -> None:
        """
        Property: For any list of hackathons, the dropdown should preserve the
        order of hackathons as returned by the API.

        This test verifies that:
        1. The order of names in the dropdown matches the API response order
        2. No reordering occurs during dropdown population

        Args:
            mock_session_class: Mocked requests.Session class
            hackathons: Generated list of hackathon dictionaries
            base_url: Generated base URL string
            api_key: Generated API key string
        """
        # Arrange: Mock session instance and response
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = hackathons
        mock_session.get.return_value = mock_response

        # Act: Fetch hackathons and create dropdown
        client = APIClient(base_url, api_key)
        response = client.get("/hackathons")

        # Simulate dropdown creation (preserving order)
        # Note: In Python 3.7+, dict maintains insertion order
        hackathon_options = {h["name"]: h["hack_id"] for h in response}
        dropdown_names = list(hackathon_options.keys())

        # Assert: Order is preserved
        expected_names = [h["name"] for h in hackathons]

        # Note: If there are duplicate names, the dict will only keep the last one
        # So we need to account for that in our assertion
        expected_names_unique = []
        seen_names = set()
        for name in expected_names:
            if name not in seen_names:
                expected_names_unique.append(name)
                seen_names.add(name)

        assert dropdown_names == expected_names_unique, (
            f"Dropdown order should match API response order. Expected {expected_names_unique}, got {dropdown_names}"
        )

    @given(
        base_url=st.from_regex(r"https?://[a-z0-9\-\.]+(?::\d+)?", fullmatch=True),
        api_key=st.text(min_size=1, max_size=100),
    )
    @patch("components.api_client.requests.Session")
    def test_empty_hackathon_list_results_in_empty_dropdown(
        self, mock_session_class: Mock, base_url: str, api_key: str
    ) -> None:
        """
        Property: When the API returns an empty list of hackathons, the dropdown
        should be empty (no options).

        This test verifies that:
        1. Empty API response results in empty dropdown
        2. No placeholder or default options are added

        Args:
            mock_session_class: Mocked requests.Session class
            base_url: Generated base URL string
            api_key: Generated API key string
        """
        # Arrange: Mock session instance with empty response
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_session.get.return_value = mock_response

        # Act: Fetch hackathons and create dropdown
        client = APIClient(base_url, api_key)
        response = client.get("/hackathons")

        # Simulate dropdown creation
        hackathon_options = {h["name"]: h["hack_id"] for h in response}
        dropdown_names = list(hackathon_options.keys())

        # Assert: Dropdown is empty
        assert len(dropdown_names) == 0, (
            f"Dropdown should be empty when API returns no hackathons, but has {len(dropdown_names)} options"
        )

    @given(
        hackathons=valid_hackathon_list(),
        base_url=st.from_regex(r"https?://[a-z0-9\-\.]+(?::\d+)?", fullmatch=True),
        api_key=st.text(min_size=1, max_size=100),
    )
    @patch("components.api_client.requests.Session")
    def test_dropdown_handles_duplicate_names_correctly(
        self,
        mock_session_class: Mock,
        hackathons: list[dict[str, Any]],
        base_url: str,
        api_key: str,
    ) -> None:
        """
        Property: When the API returns hackathons with duplicate names, the
        dropdown should handle them correctly (last one wins in dict).

        This test verifies that:
        1. Duplicate names are handled without errors
        2. The last hackathon with a duplicate name is used
        3. The dropdown doesn't crash or produce invalid state

        Args:
            mock_session_class: Mocked requests.Session class
            hackathons: Generated list of hackathon dictionaries
            base_url: Generated base URL string
            api_key: Generated API key string
        """
        # Arrange: Create hackathons with at least one duplicate name
        if len(hackathons) >= 2:
            # Make the second hackathon have the same name as the first
            hackathons[1]["name"] = hackathons[0]["name"]

        mock_session = Mock()
        mock_session_class.return_value = mock_session

        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = hackathons
        mock_session.get.return_value = mock_response

        # Act: Fetch hackathons and create dropdown
        client = APIClient(base_url, api_key)
        response = client.get("/hackathons")

        # Simulate dropdown creation (dict will keep last value for duplicate keys)
        hackathon_options = {h["name"]: h["hack_id"] for h in response}
        dropdown_names = list(hackathon_options.keys())

        # Assert: Dropdown is created without errors
        assert isinstance(dropdown_names, list), (
            "Dropdown should be a list even with duplicate names"
        )

        # Assert: Number of unique names matches dropdown length
        unique_names = {h["name"] for h in hackathons}
        assert len(dropdown_names) == len(unique_names), (
            f"Dropdown should have {len(unique_names)} unique names, but has {len(dropdown_names)}"
        )

        # Assert: For duplicate names, the last hack_id is used
        if len(hackathons) >= 2 and hackathons[0]["name"] == hackathons[1]["name"]:
            duplicate_name = hackathons[0]["name"]
            # Find the last hackathon with this name
            last_hack_id = None
            for h in hackathons:
                if h["name"] == duplicate_name:
                    last_hack_id = h["hack_id"]

            assert hackathon_options[duplicate_name] == last_hack_id, (
                f"For duplicate name '{duplicate_name}', dropdown should use the last hack_id"
            )

    @given(
        hackathons=st.lists(
            st.fixed_dictionaries(
                {
                    "hack_id": st.from_regex(r"01[A-Z0-9]{24}", fullmatch=True),
                    "name": st.just("Test Hackathon"),  # All have the same name
                    "status": st.sampled_from(["active", "completed", "draft"]),
                }
            ),
            min_size=2,
            max_size=5,
        ),
        base_url=st.from_regex(r"https?://[a-z0-9\-\.]+(?::\d+)?", fullmatch=True),
        api_key=st.text(min_size=1, max_size=100),
    )
    @patch("components.api_client.requests.Session")
    def test_all_duplicate_names_results_in_single_dropdown_option(
        self,
        mock_session_class: Mock,
        hackathons: list[dict[str, Any]],
        base_url: str,
        api_key: str,
    ) -> None:
        """
        Property: When all hackathons have the same name, the dropdown should
        contain exactly one option (the last hackathon's mapping).

        This test verifies that:
        1. Multiple hackathons with identical names collapse to one dropdown option
        2. The last hackathon's hack_id is used

        Args:
            mock_session_class: Mocked requests.Session class
            hackathons: Generated list of hackathons with identical names
            base_url: Generated base URL string
            api_key: Generated API key string
        """
        # Arrange: Mock session instance and response
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = hackathons
        mock_session.get.return_value = mock_response

        # Act: Fetch hackathons and create dropdown
        client = APIClient(base_url, api_key)
        response = client.get("/hackathons")

        # Simulate dropdown creation
        hackathon_options = {h["name"]: h["hack_id"] for h in response}
        dropdown_names = list(hackathon_options.keys())

        # Assert: Only one option in dropdown
        assert len(dropdown_names) == 1, (
            f"Dropdown should have exactly 1 option when all names are identical, but has {len(dropdown_names)}"
        )

        # Assert: The option is the shared name
        assert dropdown_names[0] == "Test Hackathon", (
            f"Dropdown should contain 'Test Hackathon', but contains '{dropdown_names[0]}'"
        )

        # Assert: The hack_id is from the last hackathon
        last_hack_id = hackathons[-1]["hack_id"]
        assert hackathon_options["Test Hackathon"] == last_hack_id, (
            f"Dropdown should map to the last hack_id '{last_hack_id}'"
        )
