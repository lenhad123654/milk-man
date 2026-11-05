import json
from pathlib import Path
from sender import sending
from milk_man import work_path


def test_make_templates_creates_clean_tester_file(fake_project, seed_endpoints):
    seed_endpoints([
        {
            "route": "/api/users",
            "method": "POST",
            "body": {"name": "Alice"},
            "response_status": 201,
        },
        {
            "route": "/health",
            "method": "GET",
            "body": {},
            "response_status": 200,
        },
    ])

    result = sending.make_templates()
    assert "Test templates created" in result

    tester_file = Path(work_path.path) / "milk-man" / "tester.json"
    assert tester_file.exists()

    content = json.loads(tester_file.read_text(encoding="utf-8"))
    assert "api-users-post" in content
    assert content["api-users-post"]["method"] == "POST"
    assert content["api-users-post"]["expected"]["status_code"] == 201

    assert "health-get" in content
    assert content["health-get"]["method"] == "GET"
    assert content["health-get"]["expected"]["status_code"] == 200


def test_make_templates_missing_endpoints(fake_project):
    endpoints_file = Path(work_path.path) / "milk-man" / "endpoints.json"
    if endpoints_file.exists():
        endpoints_file.unlink()

    result = sending.make_templates()
    assert "Error: No endpoints.json found" in result


def test_validate_expected_response():
    # Matching status code
    msg = sending.validate_expected_response("test-1", 200, {"status_code": 200})
    assert "PASSED" in msg

    # Mismatch status code
    msg = sending.validate_expected_response("test-2", 200, {"status_code": 500})
    assert "FAILED" in msg

    # Dict expected response
    expected = {"status_code": 200, "body": {"status": "ok"}}
    actual = {"status_code": 200, "body": {"status": "ok"}}
    assert "PASSED" in sending.validate_expected_response("test-3", expected, actual)

    mismatch = {"status_code": 200, "body": {"status": "error"}}
    assert "FAILED" in sending.validate_expected_response("test-4", expected, mismatch)
