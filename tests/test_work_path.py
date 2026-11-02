"""
Tests for work_path — working directory and Python executable detection.

=== TESTING FILESYSTEM OPERATIONS ===
When code touches the filesystem (os.chdir, file existence checks),
use pytest's `tmp_path` fixture for isolation. It gives you a unique
temp directory per test that's automatically cleaned up.

=== DANGER: os.chdir() ===
Changing the working directory is process-global — it affects ALL code
running in the process. Tests that call os.chdir() can interfere with
each other. We use monkeypatch to restore the original cwd after each test.
"""

import os
import sys
import pytest
from milk_man import work_path


class TestChangePath:
    @pytest.fixture(autouse=True)
    def preserve_cwd(self, monkeypatch: pytest.MonkeyPatch):
        """
        === autouse=True ===
        When a fixture has autouse=True, it runs for EVERY test in
        this class automatically — no need to name it as a parameter.
        Use sparingly: only for setup that truly every test needs.

        This saves and restores the cwd so tests don't leak side effects.
        """
        original = os.getcwd()
        yield
        os.chdir(original)
        monkeypatch.setattr(work_path, "path", original)

    def test_change_to_valid_directory(self, tmp_path):
        """
        Happy path: changing to an existing directory should work
        and update both os.getcwd() and work_path.path.
        """
        result = work_path.change_path(str(tmp_path))

        assert result == str(tmp_path)
        assert os.getcwd() == str(tmp_path)
        assert work_path.path == str(tmp_path)

    def test_change_to_nonexistent_directory_returns_error(self):
        """
        === TEST ERROR MESSAGES ===
        When a function returns an error string instead of raising,
        test that the error message is helpful. Here we just check
        it starts with "Error" — don't over-specify the exact wording
        or the test becomes brittle (breaks on minor rewording).
        """
        result = work_path.change_path("/this/does/not/exist/at/all")

        assert isinstance(result, str)
        assert result.startswith("Error")

    def test_change_path_does_not_update_on_failure(self):
        """
        Verify that a failed path change doesn't corrupt the state.
        The path should remain unchanged after an error.
        """
        original = work_path.path
        work_path.change_path("/nonexistent/garbage/path")

        assert work_path.path == original


class TestGetExecPath:
    """
    === TESTING WITH MOCKED FILESYSTEM ===
    get_exec_path() checks for venv/bin/python in the working dir.
    Instead of creating a real venv, we just create the file structure
    that the function looks for. This is faster and more reliable.
    """

    def test_returns_venv_python_when_present(self, tmp_path, monkeypatch):
        """
        Create a fake venv/bin/python file and verify it's found.
        """
        monkeypatch.setattr(work_path, "path", str(tmp_path))

        venv_bin = tmp_path / ".venv" / "bin"
        venv_bin.mkdir(parents=True)
        venv_python = venv_bin / "python"
        venv_python.touch()

        result = work_path.get_exec_path()
        assert result == str(venv_python)

    def test_falls_back_to_sys_executable_without_venv(self, tmp_path, monkeypatch):
        """
        When no venv exists, it should fall back to sys.executable.

        === TESTING FALLBACK BEHAVIOR ===
        Many functions have a "try A, fall back to B" pattern.
        Always test both branches:
        1. Test that A is used when available (test above)
        2. Test that B is used when A is missing (this test)
        """
        monkeypatch.setattr(work_path, "path", str(tmp_path))

        result = work_path.get_exec_path()
        assert result == sys.executable

    def test_returns_string_path(self, tmp_path, monkeypatch):
        """Return type should always be a string, regardless of which path is used."""
        monkeypatch.setattr(work_path, "path", str(tmp_path))
        assert isinstance(work_path.get_exec_path(), str)
