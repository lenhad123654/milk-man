import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any
import httpx
from milk_man import work_path


TestData = Mapping[str, Any]
NamedTest = tuple[str, TestData]


def _tests_file() -> Path:
    return Path(work_path.path) / "milk-man" / "tester.json"


def check_exists() -> bool:
    return _tests_file().exists()


def get_all_tests() -> dict[str, TestData]:
    tests_file = _tests_file()
    if not tests_file.exists():
        return {}

    try:
        with tests_file.open(encoding="utf-8") as file:
            return json.load(file)
    except (OSError, json.JSONDecodeError) as error:
        return f"Error reading tests file: {error}"


def _send_named_test(test_name: str, test_data: TestData) -> str:
    url = test_data.get("url")
    method = test_data.get("method", "GET").upper()
    headers = test_data.get("headers", {})
    body = test_data.get("body")

    try:
        response = httpx.request(method, url, headers=headers, data=body)
    except (httpx.HTTPError, TypeError, ValueError) as error:
        return f"Failed to send test '{test_name}': {error}"

    expected = test_data.get("expected")
    if expected is not None:
        actual = {
            "status_code": response.status_code,
            "body": _response_body(response),
        }
        return compare_results(test_name, expected, actual)

    return f"Test '{test_name}' sent. Status code: {response.status_code}"


def _response_body(response: httpx.Response) -> Any:
    try:
        return response.json()
    except ValueError:
        return response.text


def send_all_tests() -> str:
    if not check_exists():
        return "No tests found. Please create a test file first."

    messages = [
        _send_named_test(test_name, test_data)
        for test_name, test_data in get_all_tests().items()
    ]
    return "\n".join(messages)


def send_test(test_name: str) -> str:
    if not check_exists():
        return "No tests found. Please create a test file first."

    tests = get_all_tests()
    if test_name not in tests:
        return f"Test '{test_name}' not found."

    return _send_named_test(test_name, tests[test_name])


def send_few_tests(tests: Sequence[NamedTest]) -> str:
    if not check_exists():
        return "No tests found. Please create a test file first."

    messages: list[str] = []
    for test in tests:
        if len(test) != 2:
            messages.append(
                f"Invalid test format: {test}. "
                "Expected a tuple of (test_name, test_data)."
            )
            continue

        test_name, test_data = test
        messages.append(_send_named_test(test_name, test_data))

    return "\n".join(messages)


def compare_results(test_name: str, expected: Any, actual: TestData) -> str:
    if isinstance(expected, int):
        if expected == actual.get("status_code"):
            return f"[green]PASSED[/] '{test_name}'. Response matched expected result."
        expected = {"status_code": expected}

    if expected == actual:
        return f"[green]PASSED[/] '{test_name}'. Response matched expected result."

    return (
        f"[red]FAILED[/] '{test_name}'. Response did not match expected result.\n"
        f"Expected: {json.dumps(expected, indent=2)}\n"
        f"Actual: {json.dumps(actual, indent=2)}"
    )


def make_templates() -> str:
    templates_file = Path(work_path.path) / "milk-man" / "tester.json"
    endpoints_file = Path(work_path.path) / "milk-man" / "endpoints.json"

    with open(endpoints_file, "r", encoding="utf-8") as ef:
        endpoints = json.load(ef)

    with open(templates_file, "w", encoding="utf-8") as tf:
        write_data = {}
        for endpoint in endpoints:
            test_name = f"{endpoint['route']} {endpoint.get('method', 'GET')} test"
            test_data = {
                "url": endpoint["route"],
                "method": endpoint.get("method", "GET"),
                "body": endpoint.get("body", None),
                "expected": {
                    "status_code": endpoint.get("status_code", 200),
                },
            }
            write_data.update({test_name: test_data})

        tf.write(json.dumps(write_data, indent=4))

    return f"Test templates created in {templates_file}. Please edit them as needed."
