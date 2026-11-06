"""
Tests for db.database — JSON endpoint persistence, merging, and deduplication.

=== WHY THIS FILE HAS THE MOST TESTS ===
database.py contains the most complex logic in the project (~170 lines of
merge/dedup code). Complex logic = more ways to break = more tests needed.

A good rule of thumb: the harder code is to understand by reading it,
the more tests it needs. If you can't immediately tell whether a function
is correct, write tests until you can.

=== TESTING PURE FUNCTIONS vs. STATEFUL FUNCTIONS ===
- Pure functions (_route_key, _method_key): Easy to test. Same input always
  gives same output. No setup needed. Test many inputs via parametrize.
- Stateful functions (save_endpoints_to_file, update_endpoint): Need
  filesystem setup/teardown. Use fixtures for this.

=== TESTING INTERNAL/PRIVATE FUNCTIONS ===
Functions starting with _ are "private" by convention, but you CAN and
SHOULD test them directly when they contain important logic. In Python,
nothing is truly private. Testing internals is better than having bugs.
"""

import json
import pytest
from pathlib import Path
from db.database import (
    _route_key,
    _method_key,
    _merge_dicts,
    _merge_endpoint_data,
    _deduplicate_endpoints,
    save_endpoints_to_file,
    update_endpoint,
    get_dict_from_file,
)


# ============================================================================
# Tests for _route_key — route normalization
# ============================================================================


class TestRouteKey:
    """
    === PARAMETRIZE FOR DATA-DRIVEN TESTS ===
    When a function is a pure transformation (input → output), parametrize
    is perfect. List all the input/output pairs you care about, and pytest
    generates one test per pair. If one fails, you see exactly which case
    broke — much better than a single test with 10 assertions.
    """

    @pytest.mark.parametrize(
        "raw, expected",
        [
            # Basic normalization
            ("/api/users", "/api/users"),
            ("api/users", "/api/users"),
            ("/api/users/", "/api/users"),
            ("api/users/", "/api/users"),
            # Root path
            ("/", "/"),
            ("", "/"),
            # Trailing and leading slashes stripped
            ("///foo///", "/foo"),
        ],
        # ids= makes test output readable: test_route_key[/api/users -> /api/users]
        ids=lambda pair: f"{pair}" if isinstance(pair, str) else None,
    )
    def test_route_key(self, raw: str, expected: str):
        assert _route_key(raw) == expected


# ============================================================================
# Tests for _method_key — HTTP method normalization
# ============================================================================


class TestMethodKey:

    @pytest.mark.parametrize(
        "raw, expected",
        [
            ("get", "GET"),
            ("GET", "GET"),
            ("Post", "POST"),
            (None, None),
        ],
    )
    def test_method_key(self, raw, expected):
        assert _method_key(raw) == expected


# ============================================================================
# Tests for _merge_dicts — generic dict merging
# ============================================================================


class TestMergeDicts:
    """
    === TESTING MUTATION ===
    _merge_dicts modifies 'existing' in place. When testing mutation:
    1. Create the input dict
    2. Call the function
    3. Assert the input dict has changed as expected

    Don't just check the return value — _merge_dicts returns None.
    The side effect IS the purpose of the function.
    """

    def test_simple_key_override(self):
        existing = {"a": 1, "b": 2}
        _merge_dicts(existing, {"b": 99, "c": 3})
        assert existing == {"a": 1, "b": 99, "c": 3}

    def test_nested_dict_merge(self):
        """Nested dicts should be merged recursively, not replaced."""
        existing = {"meta": {"source": "scan", "version": 1}}
        _merge_dicts(existing, {"meta": {"version": 2}})
        # "source" should still be there — it was merged, not overwritten
        assert existing == {"meta": {"source": "scan", "version": 2}}

    def test_observed_by_boolean_or(self):
        """
        observed_by flags use OR logic: once something is observed,
        it stays observed even if a later merge says False.
        """
        existing = {"observed_by": {"source_code": True, "live_traffic": False}}
        _merge_dicts(existing, {"observed_by": {"live_traffic": True}})

        assert existing["observed_by"]["source_code"] is True
        assert existing["observed_by"]["live_traffic"] is True

    def test_observed_by_does_not_unset_true(self):
        """A True flag should never be overwritten to False."""
        existing = {"observed_by": {"live_traffic": True}}
        _merge_dicts(existing, {"observed_by": {"live_traffic": False}})

        assert existing["observed_by"]["live_traffic"] is True

    def test_empty_updates(self):
        """Merging nothing should change nothing."""
        existing = {"a": 1}
        _merge_dicts(existing, {})
        assert existing == {"a": 1}


# ============================================================================
# Tests for _merge_endpoint_data — endpoint-specific merging
# ============================================================================


class TestMergeEndpointData:

    def test_skips_route_and_method(self):
        """route and method should never be overwritten by a merge."""
        existing = {"route": "/old", "method": "GET", "body": {}}
        _merge_endpoint_data(existing, {"route": "/new", "method": "POST", "body": {"key": "val"}})

        assert existing["route"] == "/old"
        assert existing["method"] == "GET"
        assert existing["body"] == {"key": "val"}

    def test_does_not_overwrite_with_empty(self):
        """
        Empty/None values in incoming data should not erase existing data.
        This protects against partial updates wiping out known information.
        """
        existing = {"route": "/api", "response_body": '{"ok": true}'}
        _merge_endpoint_data(existing, {"response_body": None})

        assert existing["response_body"] == '{"ok": true}'

    def test_does_set_new_keys_even_if_empty(self):
        """But if the key doesn't exist yet, even empty values should be set."""
        existing = {"route": "/api"}
        _merge_endpoint_data(existing, {"response_body": None})

        assert "response_body" in existing


# ============================================================================
# Tests for _deduplicate_endpoints — the most complex function
# ============================================================================


class TestDeduplicateEndpoints:
    """
    === TESTING COMPLEX LOGIC ===
    _deduplicate_endpoints has multiple code paths:
    1. Endpoints with unique route+method → kept as-is
    2. Duplicate route+method → merged together
    3. A methodless entry + method-specific entries → methodless is absorbed

    Test each path independently first, then test combinations.
    """

    def test_no_duplicates_returns_same(self):
        """When there are no duplicates, the list should be unchanged."""
        endpoints = [
            {"route": "/api/a", "method": "GET"},
            {"route": "/api/b", "method": "POST"},
        ]
        result = _deduplicate_endpoints(endpoints)

        assert len(result) == 2

    def test_merges_same_route_and_method(self):
        """Two endpoints with identical route+method should become one."""
        endpoints = [
            {"route": "/api/users", "method": "GET", "response_status": 200},
            {"route": "/api/users", "method": "GET", "response_body": '{"data": []}'},
        ]
        result = _deduplicate_endpoints(endpoints)

        assert len(result) == 1
        assert result[0]["response_status"] == 200
        assert result[0]["response_body"] == '{"data": []}'

    def test_different_methods_same_route_kept_separate(self):
        """GET /users and POST /users are different endpoints."""
        endpoints = [
            {"route": "/api/users", "method": "GET"},
            {"route": "/api/users", "method": "POST"},
        ]
        result = _deduplicate_endpoints(endpoints)

        assert len(result) == 2

    def test_methodless_absorbed_into_method_specific(self):
        """
        If a route has both a methodless entry AND method-specific entries,
        the methodless one's data should be merged into the method-specific
        entries, and the methodless entry removed.
        """
        endpoints = [
            {
                "route": "/api/users",
                "method": None,
                "observed_by": {"source_code": True},
            },
            {
                "route": "/api/users",
                "method": "GET",
                "observed_by": {"live_traffic": True},
            },
        ]
        result = _deduplicate_endpoints(endpoints)

        assert len(result) == 1
        assert result[0]["method"] == "GET"

    def test_route_normalization_during_dedup(self):
        """'/api/users' and '/api/users/' should be treated as the same route."""
        endpoints = [
            {"route": "/api/users", "method": "GET"},
            {"route": "/api/users/", "method": "GET"},
        ]
        result = _deduplicate_endpoints(endpoints)

        assert len(result) == 1

    def test_empty_list(self):
        """Edge case: empty input should return empty output."""
        assert _deduplicate_endpoints([]) == []

    def test_endpoint_without_route_kept_as_is(self):
        """
        Endpoints missing a 'route' key shouldn't crash the function.
        They should be kept but not deduplicated.
        """
        endpoints = [{"method": "GET"}]
        result = _deduplicate_endpoints(endpoints)

        assert len(result) == 1


# ============================================================================
# Tests for save_endpoints_to_file — integration with filesystem
# ============================================================================


class TestSaveEndpointsToFile:
    """
    === INTEGRATION TESTS ===
    These tests exercise the full write-to-disk path. They're slower than
    pure function tests but verify that the pieces work together.

    The 'fake_project' and 'endpoints_file' fixtures (from conftest.py)
    handle all the temp directory setup.
    """

    def test_creates_file_when_missing(self, fake_project, endpoints_file):
        """First scan should create the endpoints.json file."""
        save_endpoints_to_file(["/api/users", "/api/posts"])

        assert endpoints_file.exists()
        data = json.loads(endpoints_file.read_text())
        assert len(data) == 2
        routes = {ep["route"] for ep in data}
        assert routes == {"/api/users", "/api/posts"}

    def test_preserves_existing_endpoints(self, fake_project, endpoints_file, seed_endpoints):
        """
        Running a scan twice shouldn't create duplicate entries.
        This is crucial — without dedup, the file would grow forever.
        """
        seed_endpoints(
            [
                {
                    "route": "/api/users",
                    "method": None,
                    "body": {},
                    "observed_by": {"source_code": True, "live_traffic": False, "imported": False},
                    "response_body": None,
                    "response_status": None,
                }
            ]
        )

        save_endpoints_to_file(["/api/users", "/api/posts"])

        data = json.loads(endpoints_file.read_text())
        user_routes = [ep for ep in data if ep["route"] == "/api/users"]
        assert len(user_routes) == 1  # Not duplicated

    def test_new_routes_appended(self, fake_project, endpoints_file, seed_endpoints):
        """New routes from a scan should be added alongside existing ones."""
        seed_endpoints([{"route": "/api/old", "method": None, "body": {},
                         "observed_by": {"source_code": True}, "response_body": None,
                         "response_status": None}])

        save_endpoints_to_file(["/api/new"])

        data = json.loads(endpoints_file.read_text())
        routes = {ep["route"] for ep in data}
        assert "/api/old" in routes
        assert "/api/new" in routes

    def test_source_code_flag_set_on_scan(self, fake_project, endpoints_file):
        """Scanned endpoints should have observed_by.source_code = True."""
        save_endpoints_to_file(["/api/health"])

        data = json.loads(endpoints_file.read_text())
        assert data[0]["observed_by"]["source_code"] is True
        assert data[0]["observed_by"]["live_traffic"] is False

    def test_save_with_explicit_method(self, fake_project, endpoints_file):
        """When a method is provided, it should be saved uppercase."""
        save_endpoints_to_file(["/api/users"], method="get")

        data = json.loads(endpoints_file.read_text())
        assert data[0]["method"] == "GET"

    def test_save_filters_static_and_media_routes(self, fake_project, endpoints_file):
        """Generated static and media routes should not persist."""
        save_endpoints_to_file(["/api/users", "/static/app.css", "/media/logo.png"])

        data = json.loads(endpoints_file.read_text())
        assert [endpoint["route"] for endpoint in data] == ["/api/users"]


# ============================================================================
# Tests for update_endpoint — live traffic updates
# ============================================================================


class TestUpdateEndpoint:
    """
    update_endpoint is called by the traffic proxy on every request.
    It's important that it:
    1. Creates new entries for unknown routes
    2. Updates existing entries without losing data
    3. Handles the method-discovery flow (scan finds route, traffic adds method)
    """

    def test_creates_new_endpoint_for_unknown_route(self, fake_project, endpoints_file, seed_endpoints):
        """
        If traffic hits a route we haven't seen before, a new
        endpoint entry should be created.
        """
        seed_endpoints([])

        update_endpoint("/api/new", method="POST", body='{"name": "test"}')

        data = json.loads(endpoints_file.read_text())
        assert len(data) == 1
        assert data[0]["route"] == "/api/new"
        assert data[0]["method"] == "POST"
        assert data[0]["body"] == {"name": "test"}

    def test_updates_existing_endpoint(self, fake_project, endpoints_file, seed_endpoints):
        """Traffic data should enrich an existing endpoint, not replace it."""
        seed_endpoints(
            [
                {
                    "route": "/api/users",
                    "method": "GET",
                    "body": {},
                    "observed_by": {"source_code": True, "live_traffic": False},
                    "response_body": None,
                    "response_status": None,
                }
            ]
        )

        result = update_endpoint(
            "/api/users",
            method="GET",
            response_status=200,
            response_body='[{"id": 1}]',
        )

        data = json.loads(endpoints_file.read_text())
        endpoint = data[0]
        assert endpoint["response_status"] == 200
        assert endpoint["response_body"] == {"value": [{"id": 1}]}
        # source_code flag from scan should still be True
        assert endpoint["observed_by"]["source_code"] is True

    def test_assigns_method_to_methodless_endpoint(self, fake_project, endpoints_file, seed_endpoints):
        """
        Scenario: scan found /api/users but didn't know the method.
        Traffic proxy sees a GET request to /api/users.
        The methodless entry should get method=GET assigned.
        """
        seed_endpoints(
            [
                {
                    "route": "/api/users",
                    "method": None,
                    "body": {},
                    "observed_by": {"source_code": True, "live_traffic": False},
                    "response_body": None,
                    "response_status": None,
                }
            ]
        )

        update_endpoint("/api/users", method="GET", response_status=200)

        data = json.loads(endpoints_file.read_text())
        assert len(data) == 1
        assert data[0]["method"] == "GET"
        assert data[0]["response_status"] == 200

    def test_returns_none_for_unknown_route_without_method(self, fake_project, endpoints_file, seed_endpoints):
        """
        If we can't determine the method and the route is unknown,
        the function should return None (can't create a useful entry).
        """
        seed_endpoints([])
        result = update_endpoint("/api/unknown")
        assert result is None

    def test_update_filters_static_and_media_routes(
        self, fake_project, endpoints_file, seed_endpoints
    ):
        """Live traffic writes should also exclude static and media routes."""
        seed_endpoints([])

        update_endpoint("/static/app.css", method="GET")
        update_endpoint("/media/logo.png", method="GET")

        assert json.loads(endpoints_file.read_text()) == []


# ============================================================================
# Tests for get_dict_from_file — endpoint lookup
# ============================================================================


class TestGetDictFromFile:

    def test_returns_endpoint_for_known_route(self, fake_project, seed_endpoints):
        seed_endpoints(
            [
                {
                    "route": "/api/users",
                    "method": "GET",
                    "body": {},
                    "observed_by": {"source_code": True},
                }
            ]
        )

        result = get_dict_from_file("/api/users")

        assert result is not None
        assert result["route"] == "/api/users"

    def test_returns_none_for_unknown_route(self, fake_project, seed_endpoints):
        """
        === TESTING THE NEGATIVE CASE ===
        Always test what happens when the thing ISN'T found.
        Many bugs hide in the "not found" path.
        """
        seed_endpoints([{"route": "/api/users", "method": "GET"}])

        result = get_dict_from_file("/api/nonexistent")

        assert result is None

    def test_returns_none_when_no_file(self, fake_project):
        """When endpoints.json doesn't exist at all, should return None."""
        result = get_dict_from_file("/api/anything")
        assert result is None

    def test_route_normalization_on_lookup(self, fake_project, seed_endpoints):
        """
        Looking up '/api/users/' should find '/api/users' and vice versa.
        Route normalization should work consistently across read and write.
        """
        seed_endpoints([{"route": "/api/users", "method": "GET"}])

        # Trailing slash should still match
        result = get_dict_from_file("/api/users/")
        assert result is not None
