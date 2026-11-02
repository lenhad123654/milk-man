import json
from pathlib import Path
from typing import Any, Iterable
from milk_man import work_path

# Logic for other features saving data to endpoints.json file


def _route_key(route: str) -> str:
    normalized_route = route.strip("/")
    return f"/{normalized_route}" if normalized_route else "/"


def _method_key(method: str | None) -> str | None:
    return method.upper() if method else None


def _merge_dicts(existing: dict[str, Any], updates: dict[str, Any]) -> None:
    for key, value in updates.items():
        if key == "observed_by" and isinstance(value, dict):
            observed_by = existing.setdefault("observed_by", {})
            for source, observed in value.items():
                if isinstance(observed, bool) and isinstance(
                    observed_by.get(source), bool
                ):
                    observed_by[source] = observed_by[source] or observed
                else:
                    observed_by[source] = observed
        elif isinstance(value, dict) and isinstance(existing.get(key), dict):
            _merge_dicts(existing[key], value)
        else:
            existing[key] = value


def _merge_endpoint_data(existing: dict[str, Any], incoming: dict[str, Any]) -> None:
    for key, value in incoming.items():
        if key in {"route", "method"}:
            continue
        if key == "observed_by" and isinstance(value, dict):
            observed_by = existing.setdefault("observed_by", {})
            for source, observed in value.items():
                observed_by[source] = observed_by.get(source, False) or observed
        elif isinstance(value, dict):
            current = existing.setdefault(key, {})
            if isinstance(current, dict):
                _merge_endpoint_data(current, value)
        elif value not in (None, {}, [], "") or key not in existing:
            existing[key] = value


def _deduplicate_endpoints(endpoints: list[dict[str, Any]]) -> list[dict[str, Any]]:
    unique: list[dict[str, Any]] = []
    by_identity: dict[tuple[str, str | None], dict[str, Any]] = {}

    for endpoint in endpoints:
        route = endpoint.get("route")
        if not isinstance(route, str):
            unique.append(endpoint)
            continue

        method = _method_key(endpoint.get("method"))
        identity = (_route_key(route), method)
        existing = by_identity.get(identity)
        if existing is None:
            endpoint["method"] = method
            unique.append(endpoint)
            by_identity[identity] = endpoint
        else:
            _merge_endpoint_data(existing, endpoint)

    by_route: dict[str, list[dict[str, Any]]] = {}
    for endpoint in unique:
        route = endpoint.get("route")
        if isinstance(route, str):
            by_route.setdefault(_route_key(route), []).append(endpoint)

    for route_endpoints in by_route.values():
        methodless = next(
            (endpoint for endpoint in route_endpoints if not endpoint.get("method")),
            None,
        )
        if methodless is None:
            continue

        method_specific = [
            endpoint for endpoint in route_endpoints if endpoint is not methodless
        ]
        if method_specific:
            for endpoint in method_specific:
                _merge_endpoint_data(endpoint, methodless)
            unique.remove(methodless)

    return unique


def _read_endpoints(endpoints_file: Path) -> list[dict[str, Any]]:
    if not endpoints_file.exists():
        return []
    with endpoints_file.open("r", encoding="utf-8") as file:
        endpoints = json.load(file)
    if not isinstance(endpoints, list):
        raise ValueError(f"Expected a list of endpoints in {endpoints_file}.")
    return endpoints


def _write_endpoints(endpoints_file: Path, endpoints: list[dict[str, Any]]) -> None:
    endpoints_file.parent.mkdir(parents=True, exist_ok=True)
    with endpoints_file.open("w", encoding="utf-8") as file:
        json.dump(endpoints, file, indent=4)
        file.write("\n")


def save_endpoints_to_file(routes: Iterable[str], method: str | None = None) -> None:
    endpoints_file = Path(work_path.path) / "milk-man" / "endpoints.json"
    existing_data = _deduplicate_endpoints(_read_endpoints(endpoints_file))
    normalized_method = _method_key(method)

    for route in routes:
        endpoint = {
            "route": route,
            "method": normalized_method,
            "body": {},
            "observed_by": {
                "source_code": True,
                "live_traffic": False,
                "imported": False,
            },
            "response_body": None,
            "response_status": None,
        }
        same_route = [
            existing
            for existing in existing_data
            if isinstance(existing.get("route"), str)
            and _route_key(existing["route"]) == _route_key(route)
        ]

        if normalized_method is None:
            methodless = next(
                (existing for existing in same_route if not existing.get("method")),
                None,
            )
            if methodless is not None:
                _merge_endpoint_data(methodless, endpoint)
            elif same_route:
                for existing in same_route:
                    existing.setdefault("observed_by", {})["source_code"] = True
            else:
                existing_data.append(endpoint)
            continue

        matching = next(
            (
                existing
                for existing in same_route
                if _method_key(existing.get("method")) == normalized_method
            ),
            None,
        )
        if matching is None:
            matching = next(
                (existing for existing in same_route if not existing.get("method")),
                None,
            )
            if matching is not None:
                matching["method"] = normalized_method

        if matching is None:
            existing_data.append(endpoint)
        else:
            _merge_endpoint_data(matching, endpoint)

    _write_endpoints(endpoints_file, _deduplicate_endpoints(existing_data))


def get_dict_from_file(route: str) -> dict[str, Any] | None:
    endpoints_file = Path(work_path.path) / "milk-man" / "endpoints.json"
    for endpoint in _read_endpoints(endpoints_file):
        if isinstance(endpoint.get("route"), str) and _route_key(
            endpoint["route"]
        ) == _route_key(route):
            return endpoint
    return None


def update_endpoint(route: str, **updates: Any) -> dict | None:
    endpoints_file = Path(work_path.path) / "milk-man" / "endpoints.json"
    existing_data = _deduplicate_endpoints(_read_endpoints(endpoints_file))
    method = _method_key(updates.get("method"))
    same_route = [
        endpoint
        for endpoint in existing_data
        if isinstance(endpoint.get("route"), str)
        and _route_key(endpoint["route"]) == _route_key(route)
    ]

    endpoint = next(
        (
            existing
            for existing in same_route
            if method is not None and _method_key(existing.get("method")) == method
        ),
        None,
    )
    if endpoint is None:
        endpoint = next(
            (existing for existing in same_route if not existing.get("method")),
            None,
        )
        if endpoint is not None and method is not None:
            endpoint["method"] = method

    if endpoint is None and method is None and same_route:
        endpoint = same_route[0]

    if endpoint is None:
        if method is None:
            return None
        observed_source_code = any(
            existing.get("observed_by", {}).get("source_code", False)
            for existing in same_route
        )
        observed_imported = any(
            existing.get("observed_by", {}).get("imported", False)
            for existing in same_route
        )
        endpoint = {
            "route": route,
            "method": method,
            "body": {},
            "observed_by": {
                "source_code": observed_source_code,
                "live_traffic": True,
                "imported": observed_imported,
            },
            "response_body": None,
            "response_status": None,
        }
        existing_data.append(endpoint)

    normalized_updates = dict(updates)
    if "method" in normalized_updates:
        normalized_updates["method"] = method
    _merge_dicts(endpoint, normalized_updates)

    existing_data = _deduplicate_endpoints(existing_data)
    _write_endpoints(endpoints_file, existing_data)
    return next(
        (
            saved
            for saved in existing_data
            if saved.get("route") == endpoint.get("route")
            and _method_key(saved.get("method")) == method
        ),
        endpoint,
    )
