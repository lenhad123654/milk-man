import json
from pathlib import Path
from typing import Any

import yaml

from db.database import save_imported_endpoints

_HTTP_METHODS = {"GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"}


def _resolve_reference(
    value: Any,
    document: dict[str, Any],
    resolving: tuple[str, ...] = (),
) -> Any:
    if isinstance(value, list):
        return [_resolve_reference(item, document, resolving) for item in value]
    if not isinstance(value, dict):
        return value

    reference = value.get("$ref")
    if isinstance(reference, str):
        if not reference.startswith("#/"):
            raise ValueError(
                f"Only local OpenAPI references are supported: {reference}"
            )
        if reference in resolving:
            raise ValueError(f"Circular OpenAPI reference: {reference}")
        target: Any = document
        for part in reference[2:].split("/"):
            if not isinstance(target, dict) or part not in target:
                raise ValueError(f"OpenAPI reference not found: {reference}")
            target = target[part]
        resolved = _resolve_reference(target, document, (*resolving, reference))
        siblings = {
            key: _resolve_reference(item, document, resolving)
            for key, item in value.items()
            if key != "$ref"
        }
        if isinstance(resolved, dict):
            return {**resolved, **siblings}
        return resolved

    return {
        key: _resolve_reference(item, document, resolving)
        for key, item in value.items()
    }


def _load_document(spec_path: Path) -> dict[str, Any]:
    try:
        with spec_path.open("r", encoding="utf-8") as file:
            if spec_path.suffix.lower() in {".yaml", ".yml"}:
                document = yaml.safe_load(file)
            else:
                document = json.load(file)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, yaml.YAMLError) as error:
        raise ValueError(f"Unable to read OpenAPI specification: {error}") from error

    if not isinstance(document, dict):
        raise ValueError("OpenAPI specification must contain a top-level object.")
    version = document.get("openapi")
    if not isinstance(version, str) or not version.startswith(("3.0", "3.1")):
        raise ValueError("Only OpenAPI 3.0 and 3.1 specifications are supported.")
    if not isinstance(document.get("paths"), dict):
        raise ValueError("OpenAPI specification must contain a paths object.")
    return document


def _request_schema(
    operation: dict[str, Any],
    path_item: dict[str, Any],
    document: dict[str, Any],
) -> dict[str, Any]:
    request_body = operation.get("requestBody", path_item.get("requestBody"))
    if isinstance(request_body, dict):
        content = request_body.get("content")
        if isinstance(content, dict):
            media = content.get("application/json") or next(
                (value for value in content.values() if isinstance(value, dict)),
                None,
            )
            if isinstance(media, dict) and "schema" in media:
                schema = _resolve_reference(media["schema"], document)
                if isinstance(schema, dict):
                    return schema

    parameters = []
    for parameter_source in (
        path_item.get("parameters", []),
        operation.get("parameters", []),
    ):
        if isinstance(parameter_source, list):
            parameters.extend(parameter_source)
    parameter_schemas: dict[str, Any] = {}
    for parameter in parameters:
        if not isinstance(parameter, dict):
            continue
        name = parameter.get("name")
        schema = parameter.get("schema")
        if isinstance(name, str) and schema is not None:
            parameter_schemas[name] = _resolve_reference(schema, document)
    return parameter_schemas


def _response_details(
    operation: dict[str, Any],
    document: dict[str, Any],
) -> tuple[int | None, dict[str, Any] | None]:
    responses = operation.get("responses")
    if not isinstance(responses, dict):
        return None, None

    successful = []
    for status, response in responses.items():
        try:
            status_code = int(status)
        except (TypeError, ValueError):
            continue
        if 200 <= status_code < 300 and isinstance(response, dict):
            successful.append((status_code, response))
    if not successful:
        return None, None

    status_code, response = min(successful, key=lambda item: item[0])
    content = response.get("content")
    if not isinstance(content, dict):
        return status_code, None
    media = content.get("application/json") or next(
        (value for value in content.values() if isinstance(value, dict)),
        None,
    )
    if not isinstance(media, dict) or "schema" not in media:
        return status_code, None
    schema = _resolve_reference(media["schema"], document)
    return status_code, schema if isinstance(schema, dict) else None


def import_openapi(spec_path: str | Path) -> list[dict[str, Any]]:
    """Import an OpenAPI 3 specification into the endpoint database."""
    path = Path(spec_path)
    document = _load_document(path)
    imported: list[dict[str, Any]] = []

    for route, raw_path_item in document["paths"].items():
        if not isinstance(route, str) or not isinstance(raw_path_item, dict):
            continue
        path_item = _resolve_reference(raw_path_item, document)
        if not isinstance(path_item, dict):
            continue
        for method, operation in path_item.items():
            if not isinstance(method, str) or method.upper() not in _HTTP_METHODS:
                continue
            if not isinstance(operation, dict):
                continue
            response_status, response_body = _response_details(operation, document)
            imported.append(
                {
                    "route": route,
                    "method": method.upper(),
                    "body": _request_schema(operation, path_item, document),
                    "observed_by": {
                        "source_code": False,
                        "live_traffic": False,
                        "imported": True,
                    },
                    "response_body": response_body,
                    "response_status": response_status,
                }
            )

    save_imported_endpoints(imported)
    return imported
