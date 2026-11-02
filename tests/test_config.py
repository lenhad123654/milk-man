"""
Tests for milk_man.config — port configuration management.

=== TESTING STRATEGY ===
config.py is small but demonstrates important testing concepts:
  1. Testing default values
  2. Testing valid state changes
  3. Testing boundary values (edge cases)
  4. Testing error handling (invalid input)
  5. Testing environment variable overrides

=== NAMING CONVENTION ===
Test names should read like sentences: test_<what>_<condition>_<expected>.
Good:  test_set_port_with_negative_number_raises_error
Bad:   test_port_1, test_port_2
"""

import pytest
from milk_man.config import get_client_port, set_client_port, DEFAULT_CLIENT_PORT


class TestGetClientPort:
    """
    Group related tests in a class for organization.
    pytest doesn't require classes, but they help when you have many tests.
    No __init__ needed — pytest handles instantiation.
    """

    def test_default_port_is_8000(self):
        """
        Always test that defaults are what you expect.
        If someone changes the default accidentally, this catches it.
        """
        assert DEFAULT_CLIENT_PORT == 8000

    def test_get_port_returns_integer(self):
        """Test the return type — catches bugs where strings leak through."""
        port = get_client_port()
        assert isinstance(port, int)


class TestSetClientPort:
    """
    === TESTING BOUNDARIES ===
    When a function validates a range (1-65535), always test:
    - Just below the lower bound (0)
    - The lower bound itself (1)
    - A normal value in the middle (8080)
    - The upper bound itself (65535)
    - Just above the upper bound (65536)
    This is called "boundary value analysis."
    """

    def test_set_valid_port(self):
        """
        The simplest happy-path test. After setting, getting should
        return the same value.

        === ARRANGE-ACT-ASSERT (AAA) PATTERN ===
        Every test should have three clear sections:
        - Arrange: Set up any preconditions (here: nothing needed)
        - Act: Do the thing you're testing
        - Assert: Verify the result
        """
        # Act
        set_client_port(3000)

        # Assert
        assert get_client_port() == 3000

    # === @pytest.mark.parametrize ===
    # When you want to run the SAME test logic with DIFFERENT inputs,
    # use parametrize instead of copy-pasting the test. Each tuple
    # becomes a separate test case with its own pass/fail status.
    @pytest.mark.parametrize("port", [1, 80, 443, 8080, 8000, 65535])
    def test_set_common_valid_ports(self, port: int):
        """Test various well-known valid ports."""
        set_client_port(port)
        assert get_client_port() == port

    @pytest.mark.parametrize(
        "port, reason",
        [
            (0, "zero is not a valid port"),
            (-1, "negative ports don't exist"),
            (65536, "port numbers are 16-bit, max is 65535"),
            (100_000, "way above valid range"),
        ],
    )
    def test_set_invalid_port_raises_value_error(self, port: int, reason: str):
        """
        === TESTING EXCEPTIONS ===
        Use pytest.raises() as a context manager to verify that a
        function raises the expected exception. The test FAILS if no
        exception is raised or a different exception type is raised.

        The 'reason' parameter in parametrize is just documentation —
        it helps you understand WHY each case matters when reading tests.
        """
        with pytest.raises(ValueError):
            set_client_port(port)

    def test_set_boundary_lower(self):
        """Port 1 should be the minimum valid port."""
        set_client_port(1)
        assert get_client_port() == 1

    def test_set_boundary_upper(self):
        """Port 65535 should be the maximum valid port."""
        set_client_port(65535)
        assert get_client_port() == 65535

    def test_invalid_port_does_not_change_current_value(self):
        """
        === TEST SIDE EFFECTS ===
        When an operation fails, it shouldn't have changed any state.
        This test verifies that a rejected set_client_port() doesn't
        corrupt the current port value. This catches a common bug where
        the global is updated BEFORE validation.
        """
        set_client_port(9999)
        with pytest.raises(ValueError):
            set_client_port(-1)
        assert get_client_port() == 9999  # Should still be 9999
