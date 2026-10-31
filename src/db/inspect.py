import json
from pathlib import Path
from milk_man import work_path

# /inspect command logic


def get_all() -> list[str]:
    endpoints_file = Path(work_path.path) / "milk-man" / "endpoints.json"
    if not endpoints_file.exists():
        return []

    with open(endpoints_file, "r", encoding="utf-8") as file:
        data = json.load(file)
        return [endpoint["route"] for endpoint in data if "route" in endpoint]


def get_details(route: str) -> dict | None:
    endpoints_file = Path(work_path.path) / "milk-man" / "endpoints.json"
    if not endpoints_file.exists():
        return None

    with open(endpoints_file, "r", encoding="utf-8") as file:
        data = json.load(file)
        for endpoint in data:
            if endpoint.get("route") == route:
                return endpoint
    return None
