# milk-man

Utilities for discovering and working with Django projects.

## Project layout

- `src/milk_man/` contains the application package and its command handling.
- `src/discover/` contains project and endpoint discovery modules.
- `src/db/` contains database and OpenAPI modules.

The traffic proxy listens on `127.0.0.1:12345` by default and forwards to the
Django service on port `8000`. Set `MILK_MAN_PROXY_PORT` to override the proxy
port.
