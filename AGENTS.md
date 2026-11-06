# AGENTS.md — AI Developer & Agent Integration Guide for Milk-Man

> **Target Audience:** All AI coding agents (and human engineers) implementing features, bug fixes, refactors, or extensions in the `milk-man` codebase.
> **Objective:** Ensure all features integrate flawlessly with existing architecture, data schemas, CLI UX, and test suites.

---

## 1. Project Mission & Core Concept

**Milk-Man** is a developer-facing CLI tool designed to discover, capture, and inspect API endpoints for web applications

```mermaid
flowchart TD
    User["Developer CLI / REPL (`src/milk_man/app.py`)"] --> Dispatch["Command Dispatcher (`src/milk_man/commands.py`)"]
    
    subgraph Discovery ["Discovery Engines"]
        Scan["Static & Resolver Scanner (`src/discover/scanner.py`)"]
        Proxy["Live Traffic Proxy (`src/discover/traffic.py`)"]
        Importer["Spec Importers (OpenAPI / JSON / YAML)"]
    end
    
    subgraph State ["Global State & Config"]
        WP["Target Directory (`src/milk_man/work_path.py`)"]
        CFG["Port Configuration (`src/milk_man/config.py`)"]
    end

    subgraph Storage ["Canonical Persistence"]
        DB["Data Layer & Merger (`src/db/database.py`)"]
        File[("`{work_path}/milk-man/endpoints.json`")]
        Inspect["Inspector (`src/db/inspect.py`)"]
    end

    Dispatch --> Scan
    Dispatch --> Proxy
    Dispatch --> Importer
    Dispatch --> Inspect
    Dispatch --> WP
    Dispatch --> CFG

    Scan --> DB
    Proxy --> DB
    Importer --> DB
    DB <--> File
    Inspect <--> File
```

The tool unifies three views of an API:
1. **Declared API**: What is declared in source code routing (discovered via AST / resolver).
2. **Observed API**: What actually flows over HTTP during runtime (captured via FastAPI proxy).
3. **Documented API**: What is specified in contracts (imported from OpenAPI / Swagger).

---

## 2. Workspace & Environment Conventions

- **Python Version:** Python >= 3.10 (see `pyproject.toml`).
- **Package Manager & Runner:** `uv`.
- **Command Runner:** Always run tests and scripts using `uv run` (e.g., `uv run pytest`).
- **Dependencies:** Managed in `pyproject.toml`. Do not introduce heavyweight dependencies (like massive ORMs or external databases) without explicit need. Core libraries: `fastapi`, `httpx`, `python-multipart`, `rich`, `uvicorn`, `pytest`.

### Essential Commands
```bash
# Run the complete test suite
uv run pytest

# Run a specific test file with verbose output
uv run pytest tests/test_database.py -v

# Launch interactive REPL locally
uv run milk-man
```

---

## 3. Architecture & Repository Layout

```
milk-man/
├── pyproject.toml              # Project metadata & dependencies (uv build backend)
├── AGENTS.md                   # This integration guide
├── README.md                   # User documentation
├── TESTER.md                   # Automated testing format documentation
├── src/
│   ├── milk_man/               # Core application package
│   │   ├── __init__.py         # CLI entry point (`main()`)
│   │   ├── app.py              # Interactive Rich REPL & input tokenizer
│   │   ├── commands.py         # Command dispatcher & help texts
│   │   ├── config.py           # Config state (client target port)
│   │   └── work_path.py        # Active target project directory & cross-platform venv resolver
│   ├── discover/               # API discovery & capture layer
│   │   ├── openapi.py          # OpenAPI 3.0 & 3.1 JSON/YAML specification parser
│   │   ├── scanner.py          # Framework URL scanners (Django resolver/AST, Flask, FastAPI)
│   │   ├── scripts.py          # Standalone python AST & resolver inspection scripts
│   │   └── traffic.py          # Cross-platform FastAPI reverse proxy capturing live HTTP traffic
│   ├── db/                     # Data persistence & query layer
│   │   ├── database.py         # JSON storage, merging, & deduplication logic
│   │   └── inspect.py          # Formatted query & retrieval for REPL
│   └── sender/                 # HTTP request execution and test-template generation
│       ├── __init__.py         # Sender package marker
│       └── sending.py          # Tester runner and template generator
└── tests/                      # Pytest suite with isolated fixtures
    ├── conftest.py             # Shared fixtures (fake_project, seed_endpoints)
    ├── test_app.py
    ├── test_config.py
    ├── test_database.py
    ├── test_inspect.py
    ├── test_openapi.py
    ├── test_scanner.py
    ├── test_traffic.py
    └── test_work_path.py
```

### Packaging & Module Distribution Note
Currently, `src/` contains four top-level packages: `milk_man`, `db`, `discover`, and `sender`.
- Imports use top-level package names: `from db.database import ...`, `from discover.scanner import ...`, and `from sender.sending import ...`.
- The build configuration in `pyproject.toml` (`[tool.uv.build-backend]`) bundles all four modules (`["milk_man", "db", "discover", "sender"]`) so distribution wheels and editable installs include all required modules.
- Virtual environment detection in `work_path.py` and traffic proxy process management in `traffic.py` are cross-platform (supporting Linux, macOS, and Windows).

---

## 4. The Canonical Data Contract (`endpoints.json`)

All features that create, update, or read endpoints **MUST** adhere strictly to the storage contract defined in `db/database.py`.

### 4.1 Storage Location Rule
> [!IMPORTANT]
> The database file is **NEVER** stored directly at the Milk-Man repository root!  
> It is stored relative to the active target workspace directory:  
> `Path(work_path.path) / "milk-man" / "endpoints.json"`  
> Always resolve paths dynamically through `work_path.path`.

### 4.2 Canonical Endpoint Schema
Each record in `endpoints.json` is a JSON object conforming strictly to this structure:

```python
{
    "route": str,  # Normalized route (e.g. "/customer/categories/")
    "method": str
    | None,  # Uppercase HTTP method: "GET", "POST", etc., or None if unspecified
    "body": dict,  # Request schema, query parameters, form keys, or payload structure
    "observed_by": {
        "source_code": bool,  # True if discovered through AST or runtime code scan
        "live_traffic": bool,  # True if captured through reverse proxy
        "imported": bool,  # True if imported from OpenAPI/Swagger or external schema
    },
    "response_body": dict | str | None,  # Serialized sample or schema of response body
    "response_status": int
    | None,  # Expected or observed HTTP status code (e.g. 200, 201)
}
```

### 4.3 Route & Method Normalization
- **Routes:** Handled via `_route_key(route)`. Strips leading and trailing slashes and guarantees a leading slash (unless root `"/"`).
- **Methods:** Handled via `_method_key(method)`. Returns uppercase (e.g. `"GET"`) or `None`.
- **Identity:** An endpoint is uniquely identified by `(_route_key(route), _method_key(method))`.
- **Methodless Merging:** When an endpoint is discovered via code scanning without a method (`method=None`), and later observed via live traffic with `method="GET"`, the deduplication logic in `database.py` merges the records into the method-specific endpoint.

### 4.4 Data Access Rules
Do **not** implement custom ad-hoc JSON file writing routines in new modules. Instead:
- Use `db.database.save_endpoints_to_file(routes, method=None)` for bulk route additions.
- Use `db.database.update_endpoint(route, **updates)` for updating endpoint details (such as observed traffic, response status, payloads).
- Use `db.inspect.get_all()` or `db.inspect.get_details(route)` for read operations.

---

## 5. REPL & Command Dispatch Integration

When adding new commands or flags, update the complete REPL lifecycle:

### 5.1 Step 1: Input Parsing (`src/milk_man/app.py`)
- `execute_request(request: str)` splits user input via `shlex.split`.
- Strips leading slashes (`/inspect` and `inspect` behave identically).
- Handles natural language aliases if helpful (e.g., `scan this project` -> `scan django`).

### 5.2 Step 2: Command Dispatch (`src/milk_man/commands.py`)
- Function: `main(command: str, args: list[str]) -> str | list[str] | dict | None`.
- Respect return type contracts handled by `app.py`:
  - `list[str]`: Rendered line-by-line with clean spacing.
  - `dict`: Formatted using `rich.pretty.Pretty` with indent guides.
  - `str`: Displayed directly; ordinary messages use `markup=False`, while test pass/fail messages use Rich markup.
  - `None`: Silent success.
  - Errors: Return a string starting with `"Error: <details>"`.

  The `file clean` command removes `/static/` and `/media/` routes from the
  active project's `endpoints.json` file.

### 5.3 Step 3: Help Documentation (`src/milk_man/commands.py`)
- Update `help` in `commands.py`:
  - Add the new command to the default grouped help message.
  - Add a dedicated `help <command>` block when the command has subcommands or options.

---

## 7. Quality Standards & Python 3 Conventions

### 7.1 Python Syntax & Typing Rules
- **Type Annotations:** All new functions and public methods must have complete type hints (e.g., `def run(path: Path) -> list[str]:`).
- **Union Types:** Use modern union syntax `str | None` instead of `Optional[str]` or `Union[str, None]`.
- **File Encodings:** Always specify `encoding="utf-8"` when calling `.open()` or `read_text()`.
- **String Formatting:** Use f-strings for error messages and output formatting.

### 7.2 Safety & Defensive Programming
- **Binary Payloads:** In the proxy or HTTP handlers, never blindly call `.decode("utf-8")` without `errors="replace"` or binary guards (to prevent `UnicodeDecodeError` on images/files).
- **Subprocesses:** Always pass `check=True` (or handle `CalledProcessError`), set explicit `timeout`s, and capture both `stdout` and `stderr`.
- **Unbound Variables:** Ensure all loops or try-blocks guarantee variable assignment before referencing (e.g., initialize `result = None` before subprocess execution).

---

## 8. Testing Guidelines & Fixtures

The test suite must maintain high reliability and sub-second execution speed.

### 8.1 The Fixture Contract (`tests/conftest.py`)
Never touch real files or the current directory in tests! Always use the existing fixtures:

```python
def test_my_feature(fake_project, seed_endpoints):
    # 1. Arrange: seed data into fake_project/milk-man/endpoints.json
    seed_endpoints([{"route": "/api/users", "method": "GET", "body": {}}])

    # 2. Act: Call your function
    result = get_details("/api/users")

    # 3. Assert: Validate return types and data integrity
    assert result is not None
    assert result["method"] == "GET"
```

### 8.2 Testing Checklist for Every Pull Request / Feature
- [ ] Unit tests for new logic (use `@pytest.mark.parametrize` for input variations and edge cases).
- [ ] Test the empty state (no file, empty directory, missing endpoint).
- [ ] Test return types and error strings (`assert isinstance(...)`).
- [ ] If adding a command, add tests in `tests/test_app.py` or a new `tests/test_commands.py`.
- [ ] Verify that `uv run pytest` runs cleanly with 0 failures before completing work.
