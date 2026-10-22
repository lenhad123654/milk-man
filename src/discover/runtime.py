import json
import subprocess
from milk_man import work_path


def django_scan():
    cmd = (
        ""
        "from django.urls import get_resolver\n"
        "import json\n"
        "url_patterns = [str(pattern) for pattern in get_resolver().url_patterns]\n"
        "print(json.dumps(url_patterns))"
    )
    result = subprocess.run(
        ["python"],
        cwd=work_path.path,
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
        input=cmd,
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
