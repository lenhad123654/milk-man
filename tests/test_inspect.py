"""
Tests for db.inspect — endpoint inspection and display.

=== TESTING "READ" FUNCTIONS ===
inspect.py only reads data. The testing pattern is simple:
1. Seed the JSON file with known data (using the seed_endpoints fixture)
2. Call the function
3. Assert the output matches expectations

These tests verify the output FORMAT, not just the data — because
inspect functions produce user-facing strings.
"""

import pytest
from db.inspect import get_all, get_details


class TestGetAll:

    def test_returns_empty_list_when_no_file(self, fake_project):
        """
        === ALWAYS TEST THE EMPTY STATE ===
        What happens when there's no data? This is often the first
        thing a user encounters. It should not crash.
        """
        result = get_all()
        assert result == []

    def test_returns_formatted_strings(self, fake_project, seed_endpoints):
        """Verify the output format includes route and method."""
        seed_endpoints(
            [
                {"route": "/api/users", "method": "GET"},
                {"route": "/api/posts", "method": "POST"},
            ]
        )

        result = get_all()

        assert len(result) == 2
        # Check the format matches what app.py will display
        assert any("/api/users" in item and "GET" in item for item in result)
        assert any("/api/posts" in item and "POST" in item for item in result)

    def test_results_are_sorted_by_route(self, fake_project, seed_endpoints):
        """
        Results should be alphabetically sorted by route.
        Consistent ordering makes the output predictable and testable.
        """
        seed_endpoints(
            [
                {"route": "/z-last", "method": "GET"},
                {"route": "/a-first", "method": "GET"},
                {"route": "/m-middle", "method": "GET"},
            ]
        )

        result = get_all()

        assert "/a-first" in result[0]
        assert "/m-middle" in result[1]
        assert "/z-last" in result[2]

    def test_missing_method_shows_any(self, fake_project, seed_endpoints):
        """Endpoints without a method should display 'ANY'."""
        seed_endpoints([{"route": "/api/health"}])

        result = get_all()

        assert len(result) == 1
        assert "ANY" in result[0]

    def test_returns_list_type(self, fake_project, seed_endpoints):
        """
        === TEST RETURN TYPES ===
        app.py checks `isinstance(result, list)` to decide how to render.
        If get_all() returned something else, the output would be wrong.
        """
        seed_endpoints([{"route": "/api/a", "method": "GET"}])
        assert isinstance(get_all(), list)


class TestGetDetails:

    def test_returns_full_endpoint_dict(self, fake_project, seed_endpoints):
        """Should return the complete endpoint data as a dict."""
        seed_endpoints(
            [
                {
                    "route": "/api/users",
                    "method": "GET",
                    "body": {},
                    "response_status": 200,
                    "response_body": '{"users": []}',
                    "observed_by": {"source_code": True, "live_traffic": True},
                }
            ]
        )

        result = get_details("/api/users")

        assert result is not None
        assert result["route"] == "/api/users"
        assert result["method"] == "GET"
        assert result["response_status"] == 200
        assert result["observed_by"]["live_traffic"] is True

    def test_returns_none_for_unknown_route(self, fake_project, seed_endpoints):
        seed_endpoints([{"route": "/api/users", "method": "GET"}])

        result = get_details("/api/nonexistent")

        assert result is None

    def test_returns_none_when_no_file(self, fake_project):
        """No endpoints.json at all should return None, not crash."""
        result = get_details("/api/anything")
        assert result is None

    def test_returns_dict_type(self, fake_project, seed_endpoints):
        """
        app.py renders dicts with Rich Pretty printer. Verify the type
        so the rendering path is triggered correctly.
        """
        seed_endpoints([{"route": "/api/users", "method": "GET"}])
        result = get_details("/api/users")
        assert isinstance(result, dict)
