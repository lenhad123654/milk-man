from milk_man import work_path
from discover.scanner import django_scan, flask_scan, fastapi_scan
from db.database import save_endpoints_to_file, save_fastapi_endpoints_to_file, _clean_endpoints
from db.inspect import get_all, get_details
from discover.openapi import import_openapi
from discover.traffic import proxy_is_listening, proxy_port
from milk_man.config import get_client_port, set_client_port
from discover.traffic import app_choices
from sender.sending import send_all_tests, send_test, make_templates


# Command definitions and dispatch.


def main(command: str, args: list[str]) -> str | list[str] | None:
    if command == "scan":
        framework = args[0].lower() if args else "django"
        if framework == "django":
            url_patterns = django_scan()
        if framework == "flask":
            url_patterns = flask_scan(args[1:] if len(args) > 1 else "")
        if framework == "fastapi":
            url_patterns = fastapi_scan(args[1:] if len(args) > 1 else "")

        if isinstance(url_patterns, list) and isinstance(url_patterns[0], dict):
            save_fastapi_endpoints_to_file(url_patterns)
            return url_patterns
        elif isinstance(url_patterns, list) and isinstance(url_patterns[0], str):
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
                details = get_details(args[1])
            except IndexError:
                return "Error: No route provided for 'inspect details'."
            if details is None:
                return f"Error: No endpoint found for route '{args[1]}'."
            return details

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

    elif command == "test":
        if not args:
            return send_all_tests()
        elif args[0].lower() == "make":
            return make_templates()
        elif args[0]:
            return send_test(args[0])

    elif command == "file":
        if not args:
            return "Error: No args provided for 'file'."
        if args[0].lower() == "clean":
            try:
                _clean_endpoints()
                return "Endpoints cleaned."
            except Exception as e:
                return f"Error cleaning endpoints: {e}"
        return f"Error: Unknown file command: {args[0]}"

    elif command == "help":
        if not args:
            return (
                "Milk-Man command reference\n"
                "\n"
                "Discovery:\n"
                "  scan [django|flask|fastapi] Find API routes in the project\n"
                "  import <file>              Import an OpenAPI JSON or YAML file\n"
                "\n"
                "Traffic:\n"
                "  traffic open [port]        Start the traffic proxy\n"
                "  traffic status             Show the proxy status\n"
                "  traffic close              Stop the traffic proxy\n"
                "\n"
                "Inspection:\n"
                "  inspect                    List all discovered endpoints\n"
                "  inspect details <route>   Show details for one endpoint\n"
                "\n"
                "Testing:\n"
                "  test                       Run every test in tester.json\n"
                "  test <name>                Run one named test\n"
                "  test make                  Create tester.json templates\n"
                "\n"
                "File management:\n"
                "  file clean                 Remove static and media routes\n"
                "\n"
                "Configuration:\n"
                "  path                       Show the active project path\n"
                "  path <directory>           Change the active project path\n"
                "  set port <port>            Set the target API port\n"
                "\n"
                "Other:\n"
                "  help [command]             Show this help or command details\n"
                "  exit                       Quit Milk-Man\n"
                "\n"
                "Run 'help <command>' for more information."
            )
        topic = args[0].lower()
        if topic == "traffic":
            return (
                "Usage: traffic <open|status|close> [client_port]\n"
                "\n"
                "  traffic open [port]  Start the proxy and forward requests to port.\n"
                "  traffic status       Show whether the proxy is running.\n"
                "  traffic close        Stop the proxy."
            )
        elif topic == "inspect":
            return (
                "Usage: inspect [all|details <route>]\n"
                "\n"
                "  inspect                    List all discovered endpoints.\n"
                "  inspect details <route>   Show one endpoint's stored details."
            )
        elif topic == "set":
            return (
                "Usage: set port <port>\n"
                "\n"
                "Changes the port used as the target for the traffic proxy."
            )
        elif topic == "scan":
            return (
                "Usage: scan [django|flask|fastapi] [file]\n"
                "\n"
                "Scans the active project for API routes (Django resolver & AST, "
                "Flask routes, or FastAPI endpoints) and saves them to endpoints.json."
            )
        elif topic in {"import", "openapi"}:
            return (
                "Usage: import <file>\n"
                "\n"
                "Imports an OpenAPI 3 JSON or YAML specification. "
                "'openapi' is an alias for 'import'."
            )
        elif topic == "test":
            return (
                "Usage: test [make|<name>]\n"
                "\n"
                "  test          Run every test in milk-man/tester.json.\n"
                "  test <name>   Run one named test.\n"
                "  test make     Create tester.json templates from endpoints.json.\n"
                "\n"
                "See TESTER.md for the tester.json format."
            )
        elif topic == "file":
            return (
                "Usage: file clean\n"
                "\n"
                "Removes routes beginning with '/static/' or '/media/' "
                "from endpoints.json."
            )
        elif topic == "path":
            return (
                "Usage: path [directory]\n"
                "\n"
                "With no directory, shows the active project path. "
                "Otherwise changes the active project path."
            )
        return f"Error: Unknown help topic: {args[0]}"
    else:
        return f"Error: Unknown command: {command}"
