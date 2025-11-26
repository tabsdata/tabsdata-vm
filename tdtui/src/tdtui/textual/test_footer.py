from pathlib import Path
import logging

from textual.app import App, ComposeResult
from textual.screen import Screen
from textual.widgets import ListView, ListItem, Label, Button
from textual.containers import Vertical, Horizontal
from textual import events, on

# Optional logging, like you had
logging.basicConfig(
    filename=Path.home() / "tabsdata-vm" / "log.log",
    level=logging.INFO,
    format="%(message)s",
)


class LabelItem(ListItem):
    """ListItem that just wraps a text label."""

    def __init__(self, label: str) -> None:
        super().__init__()
        self._label_text = label

    def compose(self) -> ComposeResult:
        yield Label(self._label_text)


class FooterBar(Horizontal):
    """Horizontal footer with Back / Quit and left/right/up key handling."""

    def on_mount(self) -> None:
        # Cache the buttons in the order they appear
        self._buttons = self.query(Button).results()
        self._index = 0
        # Don't steal focus on mount, we'll move focus here explicitly

    def focus_button(self, index: int) -> None:
        """Focus the button at the given index."""
        index = max(0, min(index, len(self._buttons) - 1))
        self._index = index
        self.app.set_focus(self._buttons[self._index])

    def on_key(self, event: events.Key) -> None:
        # Left/right move within footer buttons
        if event.key == "left":
            self.focus_button(self._index - 1)
            event.stop()
        elif event.key == "right":
            self.focus_button(self._index + 1)
            event.stop()
        # Up moves back to the list (last item)
        elif event.key == "up":
            menu = self.screen.query_one("#menu", ListView)
            if menu.children:
                menu.index = len(menu.children) - 1  # last item
            self.app.set_focus(menu)
            event.stop()

            

    @on(Button.Pressed, "#back")
    def handle_back(self, event: Button.Pressed) -> None:
        logging.info("Back pressed from footer")
        # If this screen was pushed, you could pop here:
        # self.screen.app.pop_screen()
        # For now just bell:
        self.app.bell()

    @on(Button.Pressed, "#quit")
    def handle_quit(self, event: Button.Pressed) -> None:
        logging.info("Quit pressed from footer")
        self.app.exit()


class MainMenu(Screen):
    """Screen with a vertical menu and a horizontal footer."""

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label("Main Menu")
            yield ListView(
                LabelItem("Fruits"),
                LabelItem("Animals"),
                id="menu",
            )
            with FooterBar(id="footer"):
                yield Button("Back", id="back", variant="default")
                yield Button("Quit", id="quit", variant="error")

    def on_mount(self) -> None:
        # Start with focus on the list
        menu = self.query_one("#menu", ListView)
        if menu.children:
            menu.index = 0
        self.app.set_focus(menu)

    def on_key(self, event: events.Key) -> None:
        # If DOWN on last list item, jump to footer
        if event.key == "down":
            menu = self.query_one("#menu", ListView)
            if self.focused is menu and menu.index == len(list(menu.children)) - 1:
                footer = self.query_one("#footer", FooterBar)
                footer.focus_button(0)  # first footer button
                event.stop()
                return



class DemoApp(App):
    """App that shows the MainMenu screen."""

    CSS = """
    Screen {
        layout: vertical;
    }

    #menu {
        height: 1fr;
    }

    #footer {
        height: 3;
        padding: 0 1;
        content-align: left middle;
    }

    Button {
        width: 12;
        margin-right: 1;
    }
    """

    def on_mount(self) -> None:
        self.push_screen(MainMenu())


if __name__ == "__main__":
    DemoApp().run()
