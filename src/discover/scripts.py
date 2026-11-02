DJANGO_AST_SEARCH = (
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

DJANGO_RESOLVER_SEARCH = (
    ""
    "from django.urls import get_resolver\n"
    "import json\n"
    "url_patterns = [str(pattern) for pattern in get_resolver().url_patterns]\n"
    "print(json.dumps(url_patterns))"
)
