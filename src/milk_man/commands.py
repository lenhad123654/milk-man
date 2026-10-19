from milk_man import work_path


# Command definitions and dispatch.


def main(command: str, args: list[str]) -> str | None:
    if command == "scan":
        print("Scanning the project for API endpoints...")
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
            "  inspect - Inspect the API endpoints\n"
            "  compare - Compare API endpoints\n"
            "  help    - Show this help message"
        )
        return message
    else:
        print(f"Unknown command: {command}")
