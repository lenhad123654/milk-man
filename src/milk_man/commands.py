from milk_man import work_path
from discover.runtime import django_scan
from db.database import save_endpoints_to_file
from discover.traffic import DEFAULT_CLIENT_PORT, proxy_is_listening, proxy_port


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

    elif command == "traffic":
        from discover.traffic import app_choices

        if not args:
            return "Error: No subcommand provided for 'traffic'."

        if args[0] == "open":
            # set client port and default if not provided
            try:
                client_port = int(args[1]) if len(args) > 1 else DEFAULT_CLIENT_PORT
            except ValueError:
                return "Error: Invalid client port specified."

            listening_port = proxy_port()

            # check if a previus proxy process is already running on the listening port
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
        return "Inspecting the API endpoints..."

    elif command == "compare":
        return "Comparing API endpoints..."

    elif command == "path":
        if not args:
            return work_path.path
        return work_path.change_path(" ".join(args))

    elif command == "help":
        message = (
            "Available commands:\n"
            "  scan    - Scan the project for API endpoints\n"
            "  traffic - Capture and analyze API traffic\n"
            "  inspect - Inspect the API endpoints\n"
            "  compare - Compare API endpoints\n"
            "  help    - Show this help message\n"
            "  exit    - Quit Milk man"
        )
        return message
    else:
        return f"Error: Unknown command: {command}"
