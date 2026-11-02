from milk_man import work_path
from discover.runtime import django_scan
from db.database import save_endpoints_to_file
from db.inspect import get_all, get_details
from discover.openapi import import_openapi
from discover.traffic import proxy_is_listening, proxy_port
from milk_man.config import get_client_port, set_client_port
from discover.traffic import app_choices


# Command definitions and dispatch.


def main(command: str, args: list[str]) -> str | list[str] | None:
    if command == "scan":
        framework = args[0].lower() if args else "django"
        if framework != "django":
            return f"Error: Unsupported framework for scanning: {framework}"

        url_patterns = django_scan()

        if isinstance(url_patterns, list):
            save_endpoints_to_file(url_patterns)
            return url_patterns

        return f"Error: {url_patterns}"

    elif command in {"import", "openapi"}:
        if not args:
            return "Error: No specification path provided."
        try:
            imported = import_openapi(args[0])
        except (OSError, ValueError) as error:
            return f"Error: {error}"
        return [endpoint["route"] for endpoint in imported]

    elif command == "traffic":
        if not args:
            return "Error: No subcommand provided for 'traffic'."

        if args[0] == "open":
            try:
                client_port = int(args[1]) if len(args) > 1 else get_client_port()
            except (IndexError, ValueError):
                return "Error: Invalid client port specified."

            listening_port = proxy_port()

            # check if a previous proxy process is already running on the listening port
            if proxy_is_listening(listening_port):
                return (
                    f"Traffic proxy is already running on port {listening_port}; "
                    f"forwarding to port {client_port}."
                )

            app_choices("open", client_port)
            return (
                f"Traffic proxy opened on port {listening_port}, "
                f"forwarding to port {client_port}."
            )
        elif args[0] == "close":
            app_choices("close", 0)
            return "Traffic proxy closed."
        elif args[0] == "status":
            return app_choices("status", 0)
        return f"Error: Unknown traffic command: {args[0]}"

    elif command == "inspect":
        if not args or args[0].lower() == "all":
            return get_all()
        elif args[0].lower() == "details":
            try:
                return get_details(args[1])
            except IndexError:
                return "Error: No route provided for 'inspect details'."

    elif command == "compare":
        return "Comparing API endpoints..."

    elif command == "path":
        if not args:
            return work_path.path
        return work_path.change_path(" ".join(args))

    elif command == "set":
        if not args:
            return "Error: No args provided for 'set'."
        elif args[0].lower() == "port":
            try:
                port = int(args[1])
                set_client_port(port)
                return f"Client port set to {port}."
            except (IndexError, ValueError):
                return "Error: Invalid port specified for 'set port'."
        return f"Error: Unknown setting: {args[0]}"

    elif command == "help":
        if not args:
            message = (
                "Available commands:\n"
                "  scan    - Scan the project for API endpoints\n"
                "  import  - Import an OpenAPI 3 specification\n"
                "  traffic - Capture and analyze API traffic\n"
                "  inspect - Inspect the API endpoints\n"
                "  compare - Compare API endpoints\n"
                "  set port - Set the target API client port\n"
                "  help    - Show this help message or get help for a specific command by providing the command name as an argument\n"
                "  exit    - Quit Milk man"
            )
            return message
        elif args[0].lower() == "traffic":
            return (
                "Traffic subcommands:\n"
                "  open [client_port]  - Open the traffic proxy (default client port if not specified)\n"
                "  close               - Close the traffic proxy\n"
                "  status              - Show the status of the traffic proxy"
            )
        elif args[0].lower() == "inspect":
            return (
                "Inspect subcommands:\n"
                "  all                 - Show all endpoints\n"
                "  details <route>     - Show details for a specific endpoint"
            )
        elif args[0].lower() == "set":
            return (
                "Set subcommands:\n"
                "  port <port_number>  - Set the target API client port"
            )
        elif args[0].lower() == "scan":
            return (
                "Scan subcommands:\n"
                "  django              - Scan the project for Django API endpoints"
            )
        elif args[0].lower() in {"import", "openapi"}:
            return "Import usage:\n  import <file_path>  - Import an OpenAPI 3 JSON or YAML specification"
        return f"Error: Unknown help topic: {args[0]}"
    else:
        return f"Error: Unknown command: {command}"
