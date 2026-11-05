import os
import pathlib
import re
import signal
import socket
import subprocess
import sys
import time
from contextlib import asynccontextmanager
from typing import Any
from fastapi import FastAPI, Path, Request, Response
import httpx
from db.database import update_endpoint
from milk_man import work_path
from milk_man.config import get_client_port
from starlette.datastructures import UploadFile

client: httpx.AsyncClient | None = None
proxy_process: subprocess.Popen[bytes] | None = None
DEFAULT_PROXY_PORT = 12345
HOP_BY_HOP_HEADERS = {
    "connection",
    "content-length",
    "host",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailer",
    "transfer-encoding",
    "upgrade",
}


def proxy_port() -> int:
    return int(os.environ.get("MILK_MAN_PROXY_PORT", str(DEFAULT_PROXY_PORT)))


def proxy_is_listening(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as connection:
        connection.settimeout(0.2)
        return connection.connect_ex(("127.0.0.1", port)) == 0


def _proxy_pid_file() -> pathlib.Path:
    return pathlib.Path(work_path.path) / "milk-man" / ".proxy.pid"


def _save_proxy_pid(pid: int) -> None:
    try:
        pid_file = _proxy_pid_file()
        pid_file.parent.mkdir(parents=True, exist_ok=True)
        pid_file.write_text(str(pid), encoding="utf-8")
    except OSError:
        pass


def _remove_proxy_pid() -> None:
    try:
        pid_file = _proxy_pid_file()
        if pid_file.exists():
            pid_file.unlink(missing_ok=True)
    except OSError:
        pass


def _read_proxy_pid() -> int | None:
    try:
        pid_file = _proxy_pid_file()
        if pid_file.exists():
            content = pid_file.read_text(encoding="utf-8").strip()
            if content.isdigit():
                return int(content)
    except OSError:
        pass
    return None


def _is_process_alive(process_id: int) -> bool:
    try:
        os.kill(process_id, 0)
        return True
    except (OSError, ProcessLookupError):
        return False


def _get_listening_pid(port: int) -> int | None:
    # 1. Check PID file if it exists and process is still alive and listening
    saved_pid = _read_proxy_pid()
    if saved_pid is not None and proxy_is_listening(port):
        if _is_process_alive(saved_pid):
            return saved_pid

    # 2. Try Linux ss
    try:
        result = subprocess.run(
            ["ss", "-ltnp", f"( sport = :{port} )"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            match = re.search(r"pid=(\d+)", result.stdout)
            if match:
                return int(match.group(1))
    except (subprocess.SubprocessError, FileNotFoundError):
        pass

    # 3. Try macOS / Unix lsof
    try:
        result = subprocess.run(
            ["lsof", f"-iTCP:{port}", "-sTCP:LISTEN", "-n", "-P"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            for line in result.stdout.strip().splitlines()[1:]:
                parts = line.split()
                if len(parts) >= 2 and parts[1].isdigit():
                    return int(parts[1])
    except (subprocess.SubprocessError, FileNotFoundError):
        pass

    # 4. Try Windows netstat
    try:
        result = subprocess.run(
            ["netstat", "-ano", "-p", "tcp"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            match = re.search(rf":{port}\s+.*?LISTENING\s+(\d+)", result.stdout, re.IGNORECASE)
            if match:
                return int(match.group(1))
    except (subprocess.SubprocessError, FileNotFoundError):
        pass

    return None


def _get_process_cmdline(process_id: int) -> str:
    # 1. On Linux, check /proc/{pid}/cmdline
    proc_cmdline = pathlib.Path(f"/proc/{process_id}/cmdline")
    if proc_cmdline.exists():
        try:
            return proc_cmdline.read_bytes().replace(b"\x00", b" ").decode("utf-8", errors="replace")
        except OSError:
            pass

    # 2. On Unix (macOS / Linux), use ps
    if sys.platform != "win32":
        try:
            res = subprocess.run(
                ["ps", "-p", str(process_id), "-o", "args="],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if res.returncode == 0:
                return res.stdout.strip()
        except (subprocess.SubprocessError, FileNotFoundError):
            pass

    # 3. On Windows, use PowerShell
    if sys.platform == "win32":
        try:
            res = subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-Command",
                    f"(Get-CimInstance Win32_Process -Filter 'ProcessId = {process_id}').CommandLine",
                ],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if res.returncode == 0 and res.stdout.strip():
                return res.stdout.strip()
        except (subprocess.SubprocessError, FileNotFoundError):
            pass

    return ""


def _proxy_process_id(port: int) -> int | None:
    process_id = _get_listening_pid(port)
    if process_id is None:
        return None

    saved_pid = _read_proxy_pid()
    if saved_pid == process_id:
        return process_id

    command = _get_process_cmdline(process_id)
    expected = "discover.traffic:app"
    if expected in command and f"--port {port}" in command:
        return process_id
    if "uvicorn" in command and expected in command:
        return process_id

    return None


def _close_proxy_process() -> None:
    global proxy_process
    process_id = (
        proxy_process.pid
        if proxy_process is not None and proxy_process.poll() is None
        else _proxy_process_id(proxy_port())
    )
    if process_id is None:
        proxy_process = None
        _remove_proxy_pid()
        return

    if proxy_process is not None and proxy_process.pid == process_id:
        proxy_process.terminate()
        try:
            proxy_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proxy_process.kill()
            proxy_process.wait(timeout=2)
    else:
        if sys.platform == "win32":
            try:
                os.kill(process_id, signal.SIGTERM)
            except OSError:
                subprocess.run(
                    ["taskkill", "/F", "/PID", str(process_id)],
                    capture_output=True,
                )
        else:
            try:
                os.kill(process_id, signal.SIGTERM)
            except OSError:
                pass

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
    _remove_proxy_pid()

async def build_body(request: Request) -> dict[str, Any]:
    body: dict[str, Any] = {}

    for key, value in request.query_params.multi_items():
        value = file_handler(value)
        if key not in body:
            body[key] = value
        elif isinstance(body[key], list):
            body[key].append(value)
        else:
            body[key] = [body[key], value]

    content_type = request.headers.get("content-type", "").lower()
    if "application/json" in content_type:
        try:
            json_data = await request.json()
        except (UnicodeDecodeError, ValueError):
            json_data = None

        if isinstance(json_data, dict):
            body.update(file_handler(json_data))
        elif json_data is not None:
            body["_json"] = file_handler(json_data)
    elif (
        "application/x-www-form-urlencoded" in content_type
        or "multipart/form-data" in content_type
    ):
        form = await request.form()
        for key, value in form.multi_items():
            value = file_handler(value)
            if key not in body:
                body[key] = value
            elif isinstance(body[key], list):
                body[key].append(value)
            else:
                body[key] = [body[key], value]

    return body


def file_handler(value: Any) -> Any:
    if isinstance(value, UploadFile):
        return value.filename
    if isinstance(value, list):
        return [file_handler(item) for item in value]
    if isinstance(value, dict):
        return {key: file_handler(item) for key, item in value.items()}
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def upstream_headers(request: Request) -> dict[str, str]:
    return {
        key: value
        for key, value in request.headers.items()
        if key.lower() not in HOP_BY_HOP_HEADERS
    }

@asynccontextmanager
async def lifespan(_: FastAPI):
    global client
    client_port = get_client_port()
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
        source_str = str(source_path)
        existing_pythonpath = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = (
            f"{source_str}{os.pathsep}{existing_pythonpath}"
            if existing_pythonpath
            else source_str
        )
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
        _save_proxy_pid(proxy_process.pid)
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


@app.api_route(
    "/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"],
)
async def proxy_request(request: Request) -> Response:
    global client
    if client is None:
        return Response(content="Client not initialized", status_code=500)

    # Forward the request to the target service
    target_url = str(request.url).replace(str(request.base_url), "")
    headers = upstream_headers(request)
    body = await request.body()
    recorded_body = await build_body(request)

    async with client.stream(
        method=request.method, url=target_url, headers=headers, content=body
    ) as upstream_response:
        response_body = await upstream_response.aread()
        response = Response(
            content=response_body,
            status_code=upstream_response.status_code,
            headers=dict(upstream_response.headers),
        )
        recorded_response_body = (
            response_body.decode("utf-8", errors="replace") if response_body else None
        )

        update_endpoint(
            route=request.url.path,
            **{
                "method": request.method,
                "body": recorded_body,
                "observed_by": {
                    "live_traffic": True,
                },
                "response_body": recorded_response_body,
                "response_status": response.status_code,
            },
        )
        return response
