from milk_man import work_path
from discover.runtime import django_scan
from db.database import save_endpoints_to_file
from discover.traffic import DEFAULT_CLIENT_PORT, proxy_is_listening, proxy_port


# Command definitions and dispatch.


def main(command: str, args: list[str]) -> str | None:
    if command == "scan":
        try:
            if args[0] == "django":
                url_patterns = django_scan()

                if isinstance(url_patterns, list):
                    save_endpoints_to_file(url_patterns)
                    return url_patterns

                else:
                    return f"Error: {url_patterns}"
        except IndexError:
            return "Error: No framework specified for scanning."

    elif command == "traffic":
        from discover.traffic import app_choices

        if not args:
            return "Error: No subcommand provided for 'traffic'."

        if args[0] == "open":
            # set client port and default if not provided
            try:
                client_port = int(args[1]) if len(args) > 1 else DEFAULT_CLIENT_PORT
            except IndexError, ValueError:
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
        # Implement traffic capture and analysis logic here.

    elif command == "inspect":
        print("Inspecting the API endpoints...")

    elif command == "compare":
        print("Comparing API endpoints...")

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
            "  help    - Show this help message"
        )
        return message
    else:
        print(f"Unknown command: {command}")
