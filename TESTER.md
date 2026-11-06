# Writing `tester.json` tests

Milk-Man can send saved HTTP requests from a `tester.json` file. The file is
read from the target project's `milk-man/tester.json` path:

```text
my-project/
└── milk-man/
    └── tester.json
```

## File format

The top-level value must be a JSON object. Each property is a test name, and
its value describes the request. Hyphens and underscores are recommended for
test names; if a name contains whitespace, quote it when invoking the test
from the CLI.

```json
{
  "list-users": {
    "url": "http://127.0.0.1:8000/api/users/",
    "method": "GET",
    "headers": {
      "Authorization": "Bearer your-token"
    }
  }
}
```

### Request fields

| Field | Required | Description |
| --- | --- | --- |
| `url` | Yes | The complete URL to request. |
| `method` | No | HTTP method. Defaults to `GET`. |
| `headers` | No | Request headers as a JSON object. |
| `body` | No | Request data sent with the request. |
| `expected` | No | Expected response, used to report pass or fail. |

Methods are case-insensitive and are sent in uppercase. The `body` value is
passed as request form data by the HTTP client. For example:

```json
{
  "create-user": {
    "url": "http://127.0.0.1:8000/api/users/",
    "method": "POST",
    "headers": {
      "Content-Type": "application/x-www-form-urlencoded"
    },
    "body": {
      "name": "Ada",
      "email": "ada@example.com"
    }
  }
}
```

## Checking responses

Without an expected response, Milk-Man sends the request and reports its
status code:

```text
Test 'list-users' sent. Status code: 200
```

To check only the status code, set `expected` to a number:

```json
{
  "list-users": {
    "url": "http://127.0.0.1:8000/api/users/",
    "expected": 200
  }
}
```

To check both the status code and response body, provide an object. The
response body is parsed as JSON when possible; otherwise its text is used.
The object must match the complete result exactly:

```json
{
  "health-check": {
    "url": "http://127.0.0.1:8000/health/",
    "expected": {
      "status_code": 200,
      "body": {
        "status": "ok"
      }
    }
  }
}
```

Successful checks produce a message such as:

```text
PASSED 'health-check'. Response matched expected result.
```

Failed checks show both the expected and actual values so the test can be
corrected.

## Running tests

Start Milk-Man from the target project, then use:

```text
test
```

This sends every test in `tester.json`. To send one named test:

```text
test health-check
```

If the file does not exist, Milk-Man reports:

```text
No tests found. Please create a test file first.
```

## Creating test templates

If you already have endpoints in `milk-man/endpoints.json`, generate starter
tests with:

```text
test make
```

This creates or overwrites `milk-man/tester.json`. Each generated test
contains the endpoint route, HTTP method, request body, and the stored response
status as its `expected` value. Replace the generated route with the full URL
of the target API before running the test.

Review the generated file before running the tests. Replace placeholder
values, add required headers, and rename generated test names if necessary.
Hyphens and underscores are recommended when renaming generated tests. If a
test name contains whitespace, quote it when invoking that test from the CLI.
