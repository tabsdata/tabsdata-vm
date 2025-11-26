from rich.spinner import Spinner

from textual.app import App, ComposeResult
from textual.widgets import Static


class SpinnerWidget(Static):
    BINDINGS = [
        ("ctrl+c", "quit", "Quit"),
        ("ctrl+b", "go_back", "Go Back"),
    ]

    def __init__(self, spinner_name: str = "dots", *args, **kwargs) -> None:
        # Accept id=, classes=, etc from Textual and forward them
        super().__init__("", *args, **kwargs)
        self._spinner = Spinner(spinner_name)

    def on_mount(self) -> None:
        # ~20 FPS is plenty for a terminal spinner
        self.set_interval(1 / 20, self.update_spinner)

    def update_spinner(self) -> None:
        self.update(self._spinner)


class MyApp(App[None]):
    BINDINGS = [
        ("ctrl+c", "quit", "Quit"),
        ("ctrl+b", "go_back", "Go Back"),
    ]

    def compose(self) -> ComposeResult:
        yield SpinnerWidget()


if __name__ == "__main__":
    MyApp().run()
