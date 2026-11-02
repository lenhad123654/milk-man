import json
import pathlib
import subprocess
from milk_man import work_path
from discover.scripts import DJANGO_AST_SEARCH, DJANGO_RESOLVER_SEARCH


def django_scan():
    try:
        url_file_path = list(pathlib.Path(work_path.path).rglob("urls.py"))[0]
    except IndexError:
        return "Error: No urls.py file found in the project directory."

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
        return f"Error running command: {result.stderr}"

    try:
        url_patterns = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        return f"Error decoding JSON output: {e}"

    return url_patterns
