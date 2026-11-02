"""
Shared test fixtures for the milk-man test suite.

=== WHAT IS conftest.py? ===
pytest automatically discovers this file and makes any fixtures defined here
available to ALL test files in this directory (and subdirectories) without
needing to import them. Think of it as "shared setup code for tests."

=== WHAT IS A FIXTURE? ===
A fixture is a function decorated with @pytest.fixture that provides test
data, configuration, or setup/teardown logic. Tests request fixtures by
naming them as parameters — pytest handles the wiring automatically.

=== KEY CONCEPTS ===
- Fixtures can depend on other fixtures (just name them as parameters).
- `yield` fixtures run code before AND after the test (setup/teardown).
- `tmp_path` is a built-in pytest fixture that gives you a fresh temp dir.
- `monkeypatch` is a built-in fixture for safely modifying objects during a test.
"""

import json
import pytest
from pathlib import Path


@pytest.fixture
def fake_project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """
    Creates a fake project directory with a milk-man/endpoints.json file
    and patches work_path.path to point to it.

    WHY: Most of the codebase reads/writes endpoints.json relative to
    work_path.path. By patching it to a temp dir, tests don't touch real
    files and each test gets a clean slate.

    PATTERN: "Fixture composition" — this fixture uses two built-in
    fixtures (tmp_path, monkeypatch) to build something higher-level.
    """
    from milk_man import work_path

    milk_man_dir = tmp_path / "milk-man"
    milk_man_dir.mkdir()

    # monkeypatch.setattr replaces an attribute for the duration of the
    # test, then automatically restores the original value afterward.
    # This is safer than manually assigning and cleaning up.
    monkeypatch.setattr(work_path, "path", str(tmp_path))

    return tmp_path


@pytest.fixture
def endpoints_file(fake_project: Path) -> Path:
    """
    Returns the path to the endpoints.json file inside the fake project.

    WHY SEPARATE FROM fake_project: Some tests need just the directory,
    others need direct access to the JSON file. Keeping fixtures small
    and composable is a best practice — compose them rather than making
    one giant fixture.
    """
    return fake_project / "milk-man" / "endpoints.json"


@pytest.fixture
def seed_endpoints(endpoints_file: Path):
    """
    Returns a helper function that writes endpoint data to the JSON file.

    WHY A FUNCTION FIXTURE: Sometimes you want a fixture that's callable —
    a "factory fixture." This lets each test seed different data without
    needing separate fixtures for each scenario.

    Usage in a test:
        def test_something(seed_endpoints):
            seed_endpoints([{"route": "/api/users", "method": "GET"}])
    """

    def _seed(data: list[dict]) -> None:
        endpoints_file.parent.mkdir(parents=True, exist_ok=True)
        endpoints_file.write_text(json.dumps(data, indent=4) + "\n")

    return _seed
