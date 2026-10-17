# Command definitions and dispatch.


def main(command: str) -> None:
    if command == "scan":
        print("Scanning the project for API endpoints...")
    elif command == "inspect":
        print("Inspecting the API endpoints...")
    elif command == "compare":
        print("Comparing API endpoints...")
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
