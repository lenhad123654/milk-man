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
