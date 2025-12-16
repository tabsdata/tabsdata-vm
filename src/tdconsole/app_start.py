from textual.app import App, ComposeResult
from textual import on
from textual.screen import Screen
from textual.widgets import ListView, ListItem, Label, Static
from pathlib import Path
from tdconsole.textual_assets.api_processor import process_response
from tdconsole.core.find_instances import (
    sync_filesystem_instances_to_db as sync_filesystem_instances_to_db,
)
from textual.reactive import reactive
import logging
from typing import Optional, Dict, Any, List
from textual.events import ScreenResume, Key
from textual.containers import VerticalScroll

from textual.widgets import Static

from rich.console import Group, RenderableType
from rich.panel import Panel
from rich.text import Text
from rich.align import Align

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer


from textual.app import App, ComposeResult
from textual.screen import Screen
from textual.containers import Horizontal, VerticalScroll
from textual.widgets import Static
from tdconsole.core.db import start_session
from tdconsole.core.find_instances import query_session
from tdconsole.core.models import Instance, get_model_by_tablename
from rich.traceback import install
import textual
import sqlalchemy
from sqlalchemy import inspect
from tdconsole.core import events
from tdconsole.core import tabsdata_api

install(
    show_locals=False,  # or True if you like locals
    suppress=[textual, sqlalchemy],
)


class NestedMenuApp(App):
    CSS = """
    * {
    height: auto;
    }
    ListView {
    height: auto;
}
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
    working_instance = reactive(None, init=False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.session = start_session()[0]
        self.session.info["app"] = self

    def on_mount(self) -> None:
        # start with a MainMenu instance
        process_response(self, "_mount")

    def action_go_back(self):
        if len(self.screen_stack) > 2:
            self.pop_screen()
        # self.install_screen(active_screen_class(), active_screen_name)

    def handle_api_response(self, screen: Screen, label: str | None = None) -> None:
        process_response(screen, label)

    def app_query_session(self, model, limit=None, *conditions, **filters):
        model = get_model_by_tablename(model)
        session = self.session
        query = query_session(session, model, limit, *conditions, **filters)
        return query

    def watch_working_instance(self, old, new):
        old = (
            None
            if old is None
            else {
                attr.key: getattr(old, attr.key)
                for attr in inspect(old).mapper.column_attrs
            }
        )
        new = (
            None
            if new is None
            else {
                attr.key: getattr(new, attr.key)
                for attr in inspect(new).mapper.column_attrs
            }
        )
        if new != old and new != None:
            self.handle_tabsdata_server_connection()
            print(self.tabsdata_server)

    def handle_tabsdata_server_connection(self):
        self.tabsdata_server = tabsdata_api.initialize_tabsdata_server_connection(self)

    @on(ListView.Highlighted)
    async def on_select_highlighted(self, event: ListView.Highlighted):
        # Scroll the highlighted list itself into view
        item = event.list_view.highlighted_child
        if item:
            item.scroll_visible()


def run_app():
    NestedMenuApp().run()


if __name__ == "__main__":
    run_app()
