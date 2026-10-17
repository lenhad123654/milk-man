from textual.app import App, ComposeResult
from textual.containers import Vertical
from textual.widgets import Footer, Header, Input, RichLog, Static


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

        conversation = self.query_one("#conversation", RichLog)
        conversation.write(f"You: {prompt}")
        conversation.write(
            "APIFind: I received your request. "
            "The discovery engine will be connected here."
        )
        event.input.value = ""


def main() -> None:
    ApiFindApp().run()

