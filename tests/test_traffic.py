import asyncio

from starlette.requests import Request

from discover.traffic import build_body, upstream_headers


def make_request(
    body: bytes = b"",
    headers: list[tuple[bytes, bytes]] | None = None,
) -> Request:
    request_headers = headers or []
    sent = False

    async def receive() -> dict:
        nonlocal sent
        if sent:
            return {"type": "http.disconnect"}
        sent = True
        return {"type": "http.request", "body": body, "more_body": False}

    scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/users",
        "raw_path": b"/api/users",
        "query_string": b"page=1&page=2",
        "headers": request_headers,
        "scheme": "http",
        "server": ("127.0.0.1", 12345),
        "client": ("127.0.0.1", 54321),
    }
    return Request(scope, receive)


def test_build_body_extracts_json_payload():
    request = make_request(
        body=b'{"name": "Ada", "active": true}',
        headers=[(b"content-type", b"application/json")],
    )

    result = asyncio.run(build_body(request))

    assert result == {"page": ["1", "2"], "name": "Ada", "active": True}


def test_build_body_preserves_non_object_json_payload():
    request = make_request(
        body=b'["one", "two"]',
        headers=[(b"content-type", b"application/json")],
    )

    result = asyncio.run(build_body(request))

    assert result == {"page": ["1", "2"], "_json": ["one", "two"]}


def test_upstream_headers_remove_proxy_and_hop_by_hop_headers():
    request = make_request(
        headers=[
            (b"host", b"127.0.0.1:12345"),
            (b"content-length", b"3"),
            (b"connection", b"keep-alive"),
            (b"x-request-id", b"abc"),
        ]
    )

    result = upstream_headers(request)

    assert result == {"x-request-id": "abc"}


def test_get_listening_pid_linux_ss(monkeypatch):
    import subprocess
    from discover import traffic

    # Simulate ss output
    def fake_run(cmd, **kwargs):
        if cmd[0] == "ss":
            return subprocess.CompletedProcess(
                cmd,
                0,
                stdout='LISTEN 0 128 127.0.0.1:12345 0.0.0.0:* users:(("python",pid=9988,fd=3))\n',
            )
        raise FileNotFoundError()

    monkeypatch.setattr(traffic, "_read_proxy_pid", lambda: None)
    monkeypatch.setattr(subprocess, "run", fake_run)

    pid = traffic._get_listening_pid(12345)
    assert pid == 9988


def test_get_listening_pid_macos_lsof(monkeypatch):
    import subprocess
    from discover import traffic

    # ss not found, lsof returns process
    def fake_run(cmd, **kwargs):
        if cmd[0] == "ss":
            raise FileNotFoundError("ss not found on macOS")
        if cmd[0] == "lsof":
            return subprocess.CompletedProcess(
                cmd,
                0,
                stdout="COMMAND   PID USER   FD   TYPE DEVICE SIZE/OFF NODE NAME\npython3 7766 user    3u  IPv4 ... 0t0  TCP 127.0.0.1:12345 (LISTEN)\n",
            )
        raise FileNotFoundError()

    monkeypatch.setattr(traffic, "_read_proxy_pid", lambda: None)
    monkeypatch.setattr(subprocess, "run", fake_run)

    pid = traffic._get_listening_pid(12345)
    assert pid == 7766


def test_get_listening_pid_windows_netstat(monkeypatch):
    import subprocess
    from discover import traffic

    # ss and lsof not found, netstat returns Windows connection
    def fake_run(cmd, **kwargs):
        if cmd[0] in ("ss", "lsof"):
            raise FileNotFoundError()
        if cmd[0] == "netstat":
            return subprocess.CompletedProcess(
                cmd,
                0,
                stdout="  TCP    127.0.0.1:12345        0.0.0.0:0              LISTENING       5544\n",
            )
        raise FileNotFoundError()

    monkeypatch.setattr(traffic, "_read_proxy_pid", lambda: None)
    monkeypatch.setattr(subprocess, "run", fake_run)

    pid = traffic._get_listening_pid(12345)
    assert pid == 5544


def test_get_listening_pid_pid_file_fallback(tmp_path, monkeypatch):
    from milk_man import work_path
    from discover import traffic

    monkeypatch.setattr(work_path, "path", str(tmp_path))
    monkeypatch.setattr(traffic, "proxy_is_listening", lambda port: True)
    monkeypatch.setattr(traffic, "_is_process_alive", lambda pid: True)

    traffic._save_proxy_pid(1234)
    assert traffic._read_proxy_pid() == 1234
    assert traffic._get_listening_pid(traffic.proxy_port()) == 1234

    traffic._remove_proxy_pid()
    assert traffic._read_proxy_pid() is None
