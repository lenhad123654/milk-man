import json
from pathlib import Path
from typing import Iterable
from milk_man import work_path

ENDPOINTS_FILE = Path(work_path.path) / "milk-man" / "endpoints.json"


def save_endpoints_to_file(routes: Iterable[str]) -> None:
    endpoints = [
        {
            "route": route,
            "method": None,
            "body": {},
            "observed_by": {
                "source_code": True,
                "live_traffic": False,
            },
        }
        for route in routes
    ]

    ENDPOINTS_FILE.parent.mkdir(parents=True, exist_ok=True)

    if ENDPOINTS_FILE.exists():
        with ENDPOINTS_FILE.open("r", encoding="utf-8") as file:
            existing_data = json.load(file)
    else:
        existing_data = []

    existing_routes = {endpoint["route"] for endpoint in existing_data}

    for endpoint in endpoints:
        if endpoint["route"] not in existing_routes:
            existing_data.append(endpoint)

    with ENDPOINTS_FILE.open("w", encoding="utf-8") as file:
        json.dump(existing_data, file, indent=4)
        file.write("\n")


save_endpoints_to_file(["/api/v2/endpoint"])
