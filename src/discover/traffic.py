import os
import pathlib
import re
import signal
import socket
import subprocess
import sys
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Path, Request, Response
import httpx
from db.database import update_endpoint
from milk_man import work_path

client: httpx.AsyncClient | None = None
proxy_process: subprocess.Popen[bytes] | None = None
DEFAULT_PROXY_PORT = 12345
DEFAULT_CLIENT_PORT = 8000


def proxy_port() -> int:
    return int(os.environ.get("MILK_MAN_PROXY_PORT", str(DEFAULT_PROXY_PORT)))


def proxy_is_listening(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as connection:
        connection.settimeout(0.2)
        return connection.connect_ex(("127.0.0.1", port)) == 0


def _proxy_process_id(port: int) -> int | None:
    result = subprocess.run(
        ["ss", "-ltnp", f"( sport = :{port} )"],
        check=True,
        capture_output=True,
        text=True,
    )
    match = re.search(r"pid=(\d+)", result.stdout)
    if match is None:
        return None

    process_id = int(match.group(1))
    command = subprocess.run(
        ["ps", "-p", str(process_id), "-o", "args="],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    expected = f"uvicorn discover.traffic:app"
    return process_id if expected in command and f"--port {port}" in command else None


def _close_proxy_process() -> None:
    global proxy_process
    process_id = (
        proxy_process.pid
        if proxy_process is not None and proxy_process.poll() is None
        else _proxy_process_id(proxy_port())
    )
    if process_id is None:
        proxy_process = None
        return

    if proxy_process is not None and proxy_process.pid == process_id:
        proxy_process.terminate()
        proxy_process.wait(timeout=5)
    else:
        os.kill(process_id, signal.SIGTERM)
        for _ in range(20):
            if not proxy_is_listening(proxy_port()):
                break
            time.sleep(0.1)
        else:
            raise RuntimeError(
                f"Traffic proxy process {process_id} did not stop on port "
                f"{proxy_port()}."
            )
    proxy_process = None


@asynccontextmanager
async def lifespan(_: FastAPI):
    global client
    client_port = int(os.environ.get("MILK_MAN_CLIENT_PORT", str(DEFAULT_CLIENT_PORT)))
    client = httpx.AsyncClient(base_url=f"http://127.0.0.1:{client_port}")
    try:
        yield
    finally:
        await client.aclose()
        client = None


app = FastAPI(title="OpenAPI Traffic Proxy", lifespan=lifespan)


def app_choices(choice: str, client_port: int) -> FastAPI:
    global proxy_process
    project_path = work_path.path
    source_path = pathlib.Path(__file__).resolve().parents[1]

    if choice == "open":
        if proxy_process is not None and proxy_process.poll() is None:
            return app

        env = os.environ.copy()
        env["MILK_MAN_CLIENT_PORT"] = str(client_port)
        listening_port = proxy_port()
        proxy_process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "discover.traffic:app",
                "--app-dir",
                str(source_path),
                "--host",
                "127.0.0.1",
                "--port",
                str(listening_port),
            ],
            cwd=project_path,
            env=env,
        )
        for _ in range(20):
            if proxy_process.poll() is not None:
                raise RuntimeError(
                    f"Traffic proxy exited with status {proxy_process.returncode}."
                )
            if proxy_is_listening(listening_port):
                break
            time.sleep(0.1)
        else:
            raise RuntimeError(
                f"Traffic proxy did not start listening on port {listening_port}."
            )

    elif choice == "close":
        _close_proxy_process()

    elif choice == "status":
        if (
            proxy_process is None or proxy_process.poll() is not None
        ) and not proxy_is_listening(proxy_port()):
            return "Proxy is closed"
        else:
            return "Proxy is open"

    return app


@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy_request(request: Request) -> Response:
    global client
    if client is None:
        return Response(content="Client not initialized", status_code=500)

    # Forward the request to the target service
    target_url = str(request.url).replace(str(request.base_url), "")
    headers = dict(request.headers)
    body = await request.body()

    async with client.stream(
        method=request.method, url=target_url, headers=headers, content=body
    ) as upstream_response:
        response_body = await upstream_response.aread()
        response = Response(
            content=response_body,
            status_code=upstream_response.status_code,
            headers=dict(upstream_response.headers),
        )

        update_endpoint(
            route=request.url.path,
            **{
                "method": request.method,
                "body": body.decode("utf-8") if body else {},
                "observed_by": {
                    "live_traffic": True,
                },
                "response_body": response_body.decode("utf-8")
                if response_body
                else None,
                "response_status": response.status_code,
            },
        )
        return response
