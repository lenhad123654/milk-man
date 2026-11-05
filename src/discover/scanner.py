import json
import pathlib
import subprocess
from milk_man import work_path
from discover.scripts import (
    DJANGO_AST_SEARCH,
    DJANGO_RESOLVER_SEARCH,
    FLASK_AST_SEARCH,
    FASTAPI_AST_SEARCH,
)


def _find_target_file(pattern: str) -> pathlib.Path | None:
    root = pathlib.Path(work_path.path)
    ignored = {".venv", "venv", ".git", "__pycache__", "build", "dist"}
    for candidate in root.rglob(pattern):
        if any(part in ignored for part in candidate.parts):
            continue
        return candidate
    return None


def django_scan():
    url_file_path = _find_target_file("urls.py")
    if url_file_path is None:
        try:
            url_file_path = list(pathlib.Path(work_path.path).rglob("urls.py"))[0]
        except IndexError:
            return "Error: No urls.py file found in the project directory."

    result = None
    for i in range(2):
        # tries the first cmd
        if i == 0:
            cmd = DJANGO_RESOLVER_SEARCH
            path = work_path.path
            args = [str(work_path.get_exec_path()), "-c", cmd]
        # tries the second cmd
        else:
            cmd = DJANGO_AST_SEARCH
            path = work_path.path
            args = [
                str(work_path.get_exec_path()),
                "-c",
                cmd,
                str(url_file_path),
            ]
        try:
            result = subprocess.run(
                args,
                cwd=path,
                capture_output=True,
                text=True,
                check=True,
                timeout=30,
            )
        except subprocess.CalledProcessError as e:
            if i == 0:
                continue
            return f"Error running command: {e}\nOutput: {e.output}\nError Output: {e.stderr}"
        if i == 0:
            break

    if result is None or result.returncode != 0:
        return f"Error running command: {result.stderr if result else 'Command failed'}"

    try:
        url_patterns = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        return f"Error decoding JSON output: {e}"

    return url_patterns


def flask_scan(path: str | None = None, *args, **kwargs):
    # if path is provided to specific file just search that else search py files in dir
    if isinstance(path, (list, tuple)):
        path = " ".join(path).strip() if path else ""
    if not path:
        url_file_path = _find_target_file("*.py")
        if url_file_path is None:
            try:
                url_file_path = list(pathlib.Path(work_path.path).rglob("*.py"))[0]
            except IndexError:
                return "Error: No .py file found in the specified directory."
    else:
        url_file_path = pathlib.Path(path)
        if not url_file_path.is_absolute():
            url_file_path = pathlib.Path(work_path.path) / url_file_path

    cmd = FLASK_AST_SEARCH
    args_list = [
        str(work_path.get_exec_path()),
        "-c",
        cmd,
        str(url_file_path),
    ]
    try:
        result = subprocess.run(
            args_list,
            cwd=work_path.path,
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        )
    except subprocess.CalledProcessError as e:
        return (
            f"Error running command: {e}\nOutput: {e.output}\nError Output: {e.stderr}"
        )

    if result.returncode != 0:
        return f"Error running command: {result.stderr}"

    try:
        url_patterns = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        return f"Error decoding JSON output: {e}"

    return url_patterns


def fastapi_scan(path: str | None = None, *args, **kwargs):
    # if path is provided to specific file just search that else search py files in dir
    if isinstance(path, (list, tuple)):
        path = " ".join(path).strip() if path else ""
    if not path:
        url_file_path = _find_target_file("*.py")
        if url_file_path is None:
            try:
                url_file_path = list(pathlib.Path(work_path.path).rglob("*.py"))[0]
            except IndexError:
                return "Error: No .py file found in the specified directory."
    else:
        url_file_path = pathlib.Path(path)
        if not url_file_path.is_absolute():
            url_file_path = pathlib.Path(work_path.path) / url_file_path

    cmd = FASTAPI_AST_SEARCH
    args_list = [
        str(work_path.get_exec_path()),
        "-c",
        cmd,
        str(url_file_path),
    ]
    try:
        result = subprocess.run(
            args_list,
            cwd=work_path.path,
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        )
    except subprocess.CalledProcessError as e:
        return (
            f"Error running command: {e}\nOutput: {e.output}\nError Output: {e.stderr}"
        )

    if result.returncode != 0:
        return f"Error running command: {result.stderr}"

    try:
        url_patterns = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        return f"Error decoding JSON output: {e}"

    return url_patterns
