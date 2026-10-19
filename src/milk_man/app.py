from textual.app import App, ComposeResult
from textual.containers import Vertical
from textual.widgets import Footer, Header, Input, RichLog, Static
from milk_man.commands import main as command_main


class ApiFindApp(App):
    TITLE = "APIFind"
    SUB_TITLE = "API discovery assistant"

    CSS = """
    Screen {
        background: #101010;
    }

    #welcome {
        color: #dddddd;
        padding: 1 2;
        height: auto;
    }

    #conversation {
        height: 1fr;
        padding: 1 2;
        border: round #444444;
    }

    #prompt {
        margin: 1 2;
        border: round #777777;
    }
    """

    BINDINGS = [
        ("ctrl+c", "quit", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()

        with Vertical():
            yield Static(
                "Welcome to APIFind\n"
                "Discover, inspect, and understand your API endpoints.\n\n"
                "Try asking: Scan this project",
                id="welcome",
            )
            yield RichLog(id="conversation", markup=False, wrap=True)
            yield Input(
                placeholder="Ask APIFind to scan, inspect, or compare APIs...",
                id="prompt",
            )

        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#prompt", Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        prompt = event.value.strip()
        if not prompt:
            return

        if prompt.startswith("/"):
            conversation = self.query_one("#conversation", RichLog)
            message = command_main(
                prompt.replace("/", "").strip().split(" ")[0].lower(),
                prompt.strip().split(" ")[1:],
            )
            if message:
                conversation = self.query_one("#conversation", RichLog)
                conversation.write(f"You: {prompt}")
                conversation.write(message)
            else:
                conversation.write("APIFind: No output from the command.")

        try:
            conversation = self.query_one("#conversation", RichLog)
            conversation.write(f"You: {prompt}")
            conversation.write(message)
            event.input.value = ""
        except Exception as e:
            conversation.write(f"Error: {e}")


def main() -> None:
    ApiFindApp().run()


# uv run --active milk-man to start
