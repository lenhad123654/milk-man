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
