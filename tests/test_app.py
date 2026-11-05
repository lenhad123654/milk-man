import sys
from milk_man import app


def test_scan_requests_default_to_django(monkeypatch):
    monkeypatch.setattr(
        app,
        "command_main",
        lambda command, args: (command, args),
    )

    assert app.execute_request("scan this project") == ("scan", ["django"])
    assert app.execute_request("scan") == ("scan", ["django"])
    assert app.execute_request("/scan django") == ("scan", ["django"])


def test_execute_request_handles_windows_paths(monkeypatch):
    monkeypatch.setattr(sys, "platform", "win32")
    recorded = []
    monkeypatch.setattr(
        app,
        "command_main",
        lambda command, args: recorded.append((command, args)),
    )

    # Standard Windows path with backslashes
    app.execute_request(r"path C:\Users\lenhad\my_project")
    assert recorded[-1] == ("path", [r"C:\Users\lenhad\my_project"])

    # Trailing backslash on Windows should not raise ValueError
    app.execute_request(r"path C:\test\\")
    assert recorded[-1] == ("path", [r"C:\test\\"])

    # Quoted path with spaces
    app.execute_request('path "C:\\Program Files\\app"')
    assert recorded[-1] == ("path", ["C:\\Program Files\\app"])
