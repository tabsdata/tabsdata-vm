from textual.app import App, ComposeResult
from textual.screen import Screen
from textual.widgets import ListView, ListItem, Label, Static
from pathlib import Path
from tdtui.textual.api_processor import process_response
from tdtui.core.find_instances import pull_all_tabsdata_instance_data as find_instances
import logging
from typing import Optional, Dict, Any, List
from textual.containers import VerticalScroll

from textual.widgets import Static

from rich.console import Group, RenderableType
from rich.panel import Panel
from rich.text import Text
from rich.align import Align

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer

from tdtui.textual.textual_instance_config import PortConfigScreen

from textual.app import App, ComposeResult
from textual.screen import Screen
from textual.containers import Horizontal, VerticalScroll
from textual.widgets import Static
from tdtui.core.db import start_session

logging.basicConfig(
    filename=Path.home() / "tabsdata-vm" / "log.log",
    level=logging.INFO,
    format="%(message)s",
)


class NestedMenuApp(App):
    CSS = """

    VerticalScroll {
        width: 1fr;
    }

    #right {
        overflow-y: hidden;
    }
    """
    BINDINGS = [
        ("ctrl+c", "quit", "Quit"),
        ("ctrl+b", "go_back", "Go Back"),
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.session = start_session()

    def on_mount(self) -> None:
        # start with a MainMenu instance
        self.push_screen(GettingStartedScreen())

    def action_go_back(self):
        logging.info(
            f'screen is { {k: v for k, v in self.screen.__dict__.items() if "InstanceSelection" in str(v)} }'
        )

        if self.screen.id not in ["MainScreen", "GettingStartedScreen"]:
            active_screen = self.screen
            active_screen_class = self.screen.__class__
            active_screen_name = self.screen.name
            self.pop_screen()
            # self.install_screen(active_screen_class(), active_screen_name)


def run_app():
    NestedMenuApp().run()


if __name__ == "__main__":
    NestedMenuApp().run()
