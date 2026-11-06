import shlex
import sys

from rich.console import Console
from rich.pretty import Pretty
from milk_man.commands import main as command_main

console = Console()


def execute_request(request: str) -> str | list[str] | dict | None:
    is_posix = sys.platform != "win32"
    try:
        parts = shlex.split(request, posix=is_posix)
        if not is_posix:
            parts = [
                p[1:-1] if len(p) >= 2 and (p[0] == p[-1] and p[0] in ('"', "'")) else p
                for p in parts
            ]
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
    console.print("[dim]Use 'help' for assistance.\n")

    while True:
        try:
            request = console.input("[bold purple]milk-man[/] [dim]›[/] ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Goodbye.[/]")
            return

        if not request:
            continue
        if request.lower() in {"exit", "quit"}:
            console.print("[dim]Goodbye.[/]")
            return

        result = execute_request(request)

        try:
            if isinstance(result, list):
                if not result:
                    console.print("No endpoints found.", style="dim")
                for item in result:
                    console.print(f"  {item}", style="white", markup=False)
            elif isinstance(result, str) and ("FAILED" in result or "PASSED" in result):
                console.print(result, markup=True)
            elif isinstance(result, dict):
                console.print(Pretty(result, indent_guides=True, expand_all=True))
            elif result is not None:
                console.print(result, markup=False)
        except Exception as e:
            console.print(f"[red]Error displaying result: {e}[/]")
            
