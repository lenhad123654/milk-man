import json
from pathlib import Path
from milk_man import work_path
from db.database import _route_key

# /inspect command logic


def get_all() -> list[str]:
    endpoints_file = Path(work_path.path) / "milk-man" / "endpoints.json"
    if not endpoints_file.exists():
        return []

    with endpoints_file.open("r", encoding="utf-8") as file:
        data = json.load(file)
        # sort the data by route and method for consistent output
        data.sort(key=lambda x: (x.get("route", ""), x.get("method", "")))

        return [
            f"'{endpoint.get('route')}' [{endpoint.get('method', 'ANY')}]"
            for endpoint in data
        ]


def get_details(route: str) -> dict | None:
    endpoints_file = Path(work_path.path) / "milk-man" / "endpoints.json"
    if not endpoints_file.exists():
        return None

    with endpoints_file.open("r", encoding="utf-8") as file:
        data = json.load(file)
        for endpoint in data:
            endpoint_route = endpoint.get("route")
            if (
                isinstance(endpoint_route, str)
                and _route_key(endpoint_route) == _route_key(route)
            ):
                return endpoint
    return None
