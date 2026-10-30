import json
from pathlib import Path
from typing import Any, Iterable
from milk_man import work_path


def save_endpoints_to_file(routes: Iterable[str]) -> None:
    endpoints_file = Path(work_path.path) / "milk-man" / "endpoints.json"
    endpoints = [
        {
            "route": route,
            "method": None,
            "body": {},
            "observed_by": {
                "source_code": True,
                "live_traffic": False,
            },
            "response_body": None,
            "response_status": None,
        }
        for route in routes
    ]

    endpoints_file.parent.mkdir(parents=True, exist_ok=True)

    if endpoints_file.exists():
        with endpoints_file.open("r", encoding="utf-8") as file:
            existing_data = json.load(file)
    else:
        existing_data = []

    existing_routes = {endpoint["route"] for endpoint in existing_data}

    for endpoint in endpoints:
        if endpoint["route"] not in existing_routes:
            existing_data.append(endpoint)

    with endpoints_file.open("w", encoding="utf-8") as file:
        json.dump(existing_data, file, indent=4)
        file.write("\n")


def get_dict_from_file(route: str) -> dict:
    endpoints_file = Path(work_path.path) / "milk-man" / "endpoints.json"
    try:
        with open(str(endpoints_file), "r") as f:
            existing_data = json.load(f)

        for endpoint in existing_data:
            if endpoint["route"] == route:
                return endpoint

    except Exception as e:
        print(f"Error reading endpoints file: {e}")
        return None


def _merge_dicts(existing: dict[str, Any], updates: dict[str, Any]) -> None:
    for key, value in updates.items():
        if isinstance(value, dict) and isinstance(existing.get(key), dict):
            _merge_dicts(existing[key], value)
        else:
            existing[key] = value


def update_endpoint(route: str, **updates: Any) -> dict | None:
    endpoints_file = Path(work_path.path) / "milk-man" / "endpoints.json"

    with endpoints_file.open("r", encoding="utf-8") as file:
        existing_data = json.load(file)

    for endpoint in existing_data:
        if endpoint["route"].replace("/", "") == route.replace("/", ""):
            _merge_dicts(endpoint, updates)

            with endpoints_file.open("w", encoding="utf-8") as file:
                json.dump(existing_data, file, indent=4)
                file.write("\n")

            return endpoint

    return None


save_endpoints_to_file(["/api/v2/endpoint"])
