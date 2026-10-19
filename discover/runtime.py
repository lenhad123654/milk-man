import json
import subprocess
from milk_man import work_path


def django_scan():
    result = subprocess.run(
        [
            f"{work_path.get_exec_path()}/python",
            "manage.py",
            "dump_urls",
        ],
        cwd=work_path.path,
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )

    if result.returncode != 0:
        print("Error running Django management command:", result.stderr)
        return []

    try:
        url_patterns = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        print("Error decoding JSON output:", e)
        return []

    return url_patterns
