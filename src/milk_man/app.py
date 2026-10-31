import shlex

from rich.console import Console
from milk_man.commands import main as command_main

console = Console()


def execute_request(request: str) -> str | list[str] | None:
    try:
        parts = shlex.split(request)
    except ValueError as error:
        return f"Error parsing request: {error}"

    if not parts:
        return None

    command = parts[0].removeprefix("/").lower()
    args = parts[1:]

    if command == "discover":
        command = "scan"
    if command == "scan" and (
        not args or args[0].lower() in {"this", "the", "my", "project"}
    ):
        args = ["django"]

    return command_main(command, args)


def main() -> None:
    console.print("[bold purple]Milk man[/]")
    console.print("[dim]Discover and understand the APIs in your project.[/]")
    console.print(
        "[dim]Try:[/] scan this project  ·  inspect  ·  traffic status  ·  help\n"
    )

    while True:
        try:
            request = console.input("[bold purple]milk-man[/] [dim]›[/] ").strip()
        except EOFError, KeyboardInterrupt:
            console.print("\n[dim]Goodbye.[/]")
            return

        if not request:
            continue
        if request.lower() in {"exit", "quit"}:
            console.print("[dim]Goodbye.[/]")
            return

        result = execute_request(request)
        if isinstance(result, list):
            if not result:
                console.print("No endpoints found.", style="dim")
            for item in result:
                console.print(f"  {item}", style="white", markup=False)
        elif result is not None:
            console.print(result, markup=False)
