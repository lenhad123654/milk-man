import json
import pathlib
import subprocess
from milk_man import work_path


def django_scan():
    # command that is run inside the subprocess
    cmd_resolver = (
        ""
        "from django.urls import get_resolver\n"
        "import json\n"
        "url_patterns = [str(pattern) for pattern in get_resolver().url_patterns]\n"
        "print(json.dumps(url_patterns))"
    )

    cmd_urls_file = (
        ""
        "import ast\n"
        "import json\n"
        "import pathlib\n"
        "urls_file = pathlib.Path(__import__('sys').argv[1])\n"
        "tree = ast.parse(urls_file.read_text(encoding='utf-8'))\n"
        "url_routes = []\n"
        "for node in ast.walk(tree):\n"
        "    if not isinstance(node, ast.Call):\n"
        "        continue\n"
        "    if not isinstance(node.func, ast.Name):\n"
        "        continue\n"
        "    if node.func.id not in {'path', 're_path'} or not node.args:\n"
        "        continue\n"
        "    route = node.args[0]\n"
        "    if isinstance(route, ast.Constant) and isinstance(route.value, str):\n"
        "        url_routes.append(route.value)\n"
        "url_routes = list(dict.fromkeys(url_routes))\n"
        "print(json.dumps(url_routes))"
    )
    url_file_path = list(pathlib.Path(work_path.path).rglob("urls.py"))[0]

    for i in range(2):
        # trys the first cmd
        if i == 0:
            cmd = cmd_resolver
            path = work_path.path
            args = [str(work_path.get_exec_path()), "-c", cmd]
        # trys the second cmd
        else:
            cmd = cmd_urls_file
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
            return "Error running Django resolve command:", e.stderr

    try:
        url_patterns = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        return "Error decoding JSON output:", e

    return url_patterns
