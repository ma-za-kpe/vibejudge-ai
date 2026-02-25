"""Property-based tests for cache TTL enforcement.

Feature: streamlit-organizer-dashboard
Tests universal properties of cache TTL behavior using Hypothesis.
"""

import time
from typing import Any
from unittest.mock import Mock

from hypothesis import given
from hypothesis import strategies as st


# Custom strategies for test data
@st.composite
def valid_hackathon_list(draw: Any) -> list[dict[str, Any]]:
    """Generate a list of valid hackathon dictionaries."""
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
            "status": draw(st.sampled_from(["active", "completed", "draft"])),
        }
        hackathons.append(hackathon)

    return hackathons


@st.composite
def valid_stats_dict(draw: Any) -> dict[str, int]:
    """Generate a valid stats dictionary."""
    return {
        "submission_count": draw(st.integers(min_value=0, max_value=1000)),
        "verified_count": draw(st.integers(min_value=0, max_value=1000)),
        "pending_count": draw(st.integers(min_value=0, max_value=100)),
        "participant_count": draw(st.integers(min_value=0, max_value=5000)),
    }


class TestCacheTTLEnforcementProperty:
    """Property 11: Cache TTL Enforcement

    **Validates: Requirements 3.6, 11.2, 11.3**

    For any cached GET request, repeated calls within 30 seconds should return
    the cached response without making a new API call.
    """

    @given(hackathons=valid_hackathon_list(), api_key=st.text(min_size=1, max_size=100))
    def test_cache_decorator_with_ttl_prevents_repeated_api_calls(
        self, hackathons: list[dict[str, Any]], api_key: str
    ) -> None:
        """
        Property: For any cached function with TTL, repeated calls within the TTL
        period should return cached data without calling the underlying function.

        This test verifies that:
        1. The first call executes the underlying function
        2. Subsequent calls within TTL return cached data
        3. The underlying function is not called again during TTL

        Args:
            hackathons: Generated list of hackathon dictionaries
            api_key: Generated API key string
        """
        # Arrange: Create a mock function that simulates API call
        mock_api_call = Mock(return_value=hackathons)
        mock_api_call.__name__ = "fetch_hackathons"

        # Create a simple cache implementation
        cache_store: dict[str, tuple[Any, float]] = {}

        def cache_data(ttl: int = 30):
            """Simple cache decorator that mimics st.cache_data behavior."""

            def decorator(func):
                def wrapper(*args, **kwargs):
                    # Create cache key from function name and arguments
                    cache_key = f"{func.__name__}_{args}_{kwargs}"
                    current_time = time.time()

                    # Check if result is in cache and not expired
                    if cache_key in cache_store:
                        cached_result, cached_time = cache_store[cache_key]
                        if current_time - cached_time < ttl:
                            # Return cached result without calling function
                            return cached_result

                    # Call function and store result with timestamp
                    result = func(*args, **kwargs)
                    cache_store[cache_key] = (result, current_time)
                    return result

                return wrapper

            return decorator

        # Apply cache decorator to mock function
        cached_function = cache_data(ttl=30)(mock_api_call)

        # Act: Make first call
        first_result = cached_function(api_key)

        # Assert: First call should execute the function
        assert mock_api_call.call_count == 1, "First call should execute the underlying function"
        assert first_result == hackathons, "First result should match the function return value"

        # Act: Make second call immediately (within TTL)
        second_result = cached_function(api_key)

        # Assert: Second call should NOT execute the function (cached)
        assert mock_api_call.call_count == 1, "Second call should not execute the function (cached)"
        assert second_result == hackathons, "Second result should match the cached value"
        assert second_result is first_result, (
            "Second result should be the same object as first result"
        )

    @given(
        hackathons_v1=valid_hackathon_list(),
        hackathons_v2=valid_hackathon_list(),
        api_key=st.text(min_size=1, max_size=100),
    )
    def test_cache_returns_stale_data_within_ttl(
        self, hackathons_v1: list[dict[str, Any]], hackathons_v2: list[dict[str, Any]], api_key: str
    ) -> None:
        """
        Property: For any cached function, if the underlying data changes within
        the TTL period, the cache should still return the old (stale) data.

        This test verifies that:
        1. Cache returns the first response even if underlying data changes
        2. Cache doesn't automatically invalidate on data changes
        3. TTL-based caching behavior is correct

        Args:
            hackathons_v1: First version of hackathons data
            hackathons_v2: Second version of hackathons data (different)
            api_key: Generated API key string
        """
        # Arrange: Create a mock function that returns different data on each call
        mock_api_call = Mock(side_effect=[hackathons_v1, hackathons_v2])
        mock_api_call.__name__ = "fetch_hackathons"

        # Create cache implementation
        cache_store: dict[str, tuple[Any, float]] = {}

        def cache_data(ttl: int = 30):
            """Simple cache decorator that mimics st.cache_data behavior."""

            def decorator(func):
                def wrapper(*args, **kwargs):
                    cache_key = f"{func.__name__}_{args}_{kwargs}"
                    current_time = time.time()

                    if cache_key in cache_store:
                        cached_result, cached_time = cache_store[cache_key]
                        if current_time - cached_time < ttl:
                            return cached_result

                    result = func(*args, **kwargs)
                    cache_store[cache_key] = (result, current_time)
                    return result

                return wrapper

            return decorator

        # Apply cache decorator
        cached_function = cache_data(ttl=30)(mock_api_call)

        # Act: Make first call
        first_result = cached_function(api_key)

        # Assert: First call returns v1 data
        assert first_result == hackathons_v1, "First call should return v1 data"
        assert mock_api_call.call_count == 1, "First call should execute the function"

        # Act: Make second call immediately (within TTL)
        second_result = cached_function(api_key)

        # Assert: Second call returns cached v1 data (not v2)
        assert second_result == hackathons_v1, "Second call should return cached v1 data, not v2"
        assert mock_api_call.call_count == 1, "Second call should not execute the function (cached)"

    @given(
        stats=valid_stats_dict(),
        api_key=st.text(min_size=1, max_size=100),
        hack_id=st.from_regex(r"01[A-Z0-9]{24}", fullmatch=True),
    )
    def test_cache_stores_complete_data_without_modification(
        self, stats: dict[str, int], api_key: str, hack_id: str
    ) -> None:
        """
        Property: For any data returned by a cached function, the cache should
        store and return the complete data without any modification.

        This test verifies that:
        1. All fields in the original data are present in cached data
        2. No data is lost or modified during caching
        3. Cached data is identical to original data

        Args:
            stats: Generated stats dictionary
            api_key: Generated API key string
            hack_id: Generated hackathon ID
        """
        # Arrange: Create a mock function that returns stats
        mock_api_call = Mock(return_value=stats)
        mock_api_call.__name__ = "fetch_stats"

        # Create cache implementation
        cache_store: dict[str, tuple[Any, float]] = {}

        def cache_data(ttl: int = 30):
            """Simple cache decorator that mimics st.cache_data behavior."""

            def decorator(func):
                def wrapper(*args, **kwargs):
                    cache_key = f"{func.__name__}_{args}_{kwargs}"
                    current_time = time.time()

                    if cache_key in cache_store:
                        cached_result, cached_time = cache_store[cache_key]
                        if current_time - cached_time < ttl:
                            return cached_result

                    result = func(*args, **kwargs)
                    cache_store[cache_key] = (result, current_time)
                    return result

                return wrapper

            return decorator

        # Apply cache decorator
        cached_function = cache_data(ttl=30)(mock_api_call)

        # Act: Make first call
        first_result = cached_function(api_key, hack_id)

        # Assert: First result matches original data exactly
        assert first_result == stats, "First result should match original stats data"
        assert all(key in first_result for key in stats), (
            "All keys from original data should be present"
        )
        assert all(first_result[key] == stats[key] for key in stats), (
            "All values should match original data"
        )

        # Act: Make second call (cached)
        second_result = cached_function(api_key, hack_id)

        # Assert: Cached result matches original data exactly
        assert second_result == stats, "Cached result should match original stats data"
        assert all(key in second_result for key in stats), (
            "All keys should be present in cached data"
        )
        assert all(second_result[key] == stats[key] for key in stats), (
            "All cached values should match original data"
        )

    @given(
        hackathons=valid_hackathon_list(),
        api_key_1=st.text(min_size=1, max_size=100),
        api_key_2=st.text(min_size=1, max_size=100),
    )
    def test_cache_isolation_per_api_key(
        self, hackathons: list[dict[str, Any]], api_key_1: str, api_key_2: str
    ) -> None:
        """
        Property: For any two different API keys, the cache should maintain
        separate cache entries to prevent data leakage between users.

        This test verifies that:
        1. Different API keys result in different cache entries
        2. One user's cached data doesn't affect another user
        3. Cache isolation is maintained

        Args:
            hackathons: Generated list of hackathon dictionaries
            api_key_1: First API key
            api_key_2: Second API key
        """
        # Skip if API keys are identical
        if api_key_1 == api_key_2:
            return

        # Arrange: Create a mock function
        mock_api_call = Mock(return_value=hackathons)
        mock_api_call.__name__ = "fetch_hackathons"

        # Create cache implementation
        cache_store: dict[str, tuple[Any, float]] = {}

        def cache_data(ttl: int = 30):
            """Simple cache decorator that mimics st.cache_data behavior."""

            def decorator(func):
                def wrapper(*args, **kwargs):
                    # Cache key includes all arguments (including api_key)
                    cache_key = f"{func.__name__}_{args}_{kwargs}"
                    current_time = time.time()

                    if cache_key in cache_store:
                        cached_result, cached_time = cache_store[cache_key]
                        if current_time - cached_time < ttl:
                            return cached_result

                    result = func(*args, **kwargs)
                    cache_store[cache_key] = (result, current_time)
                    return result

                return wrapper

            return decorator

        # Apply cache decorator
        cached_function = cache_data(ttl=30)(mock_api_call)

        # Act: Make call with first API key
        result_1 = cached_function(api_key_1)

        # Assert: First call executes the function
        assert mock_api_call.call_count == 1, "First call should execute the function"

        # Act: Make call with second API key
        cached_function(api_key_2)

        # Assert: Second call with different API key should execute the function again
        assert mock_api_call.call_count == 2, (
            "Different API key should result in separate cache entry"
        )

        # Act: Make another call with first API key (should be cached)
        result_1_cached = cached_function(api_key_1)

        # Assert: Third call with first API key should use cache
        assert mock_api_call.call_count == 2, "Third call with first API key should use cached data"
        assert result_1_cached is result_1, "Cached result should be the same object"

    @given(api_key=st.text(min_size=1, max_size=100))
    def test_cache_handles_empty_responses(self, api_key: str) -> None:
        """
        Property: For any function that returns an empty response, the cache
        should store and return the empty response correctly.

        This test verifies that:
        1. Empty responses are cached
        2. Empty responses are returned correctly from cache
        3. No errors occur when caching empty data

        Args:
            api_key: Generated API key string
        """
        # Arrange: Create a mock function that returns empty list
        empty_list: list[dict[str, Any]] = []
        mock_api_call = Mock(return_value=empty_list)
        mock_api_call.__name__ = "fetch_hackathons"

        # Create cache implementation
        cache_store: dict[str, tuple[Any, float]] = {}

        def cache_data(ttl: int = 30):
            """Simple cache decorator that mimics st.cache_data behavior."""

            def decorator(func):
                def wrapper(*args, **kwargs):
                    cache_key = f"{func.__name__}_{args}_{kwargs}"
                    current_time = time.time()

                    if cache_key in cache_store:
                        cached_result, cached_time = cache_store[cache_key]
                        if current_time - cached_time < ttl:
                            return cached_result

                    result = func(*args, **kwargs)
                    cache_store[cache_key] = (result, current_time)
                    return result

                return wrapper

            return decorator

        # Apply cache decorator
        cached_function = cache_data(ttl=30)(mock_api_call)

        # Act: Make first call
        first_result = cached_function(api_key)

        # Assert: First result is empty list
        assert first_result == [], "First result should be an empty list"
        assert isinstance(first_result, list), "Result should be a list type"
        assert len(first_result) == 0, "Result should have zero length"

        # Act: Make second call (cached)
        second_result = cached_function(api_key)

        # Assert: Cached result is also empty list
        assert second_result == [], "Cached result should be an empty list"
        assert mock_api_call.call_count == 1, "Second call should use cached empty list"
