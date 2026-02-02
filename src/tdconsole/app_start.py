import sqlalchemy
import textual
from rich.traceback import install
from sqlalchemy import inspect
from textual import on
from textual.app import App
from textual.reactive import reactive
from textual.screen import Screen
from textual.widgets import Button, ListView

from tdconsole.core import tabsdata_api
from tdconsole.core.db import start_session
from tdconsole.core.find_instances import query_session, resolve_working_instance
from tdconsole.core.find_instances import (
    sync_filesystem_instances_to_db as sync_filesystem_instances_to_db,
)
from tdconsole.core.models import get_model_by_tablename
from tdconsole.textual_assets.api_processor import process_response

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
        self.working_instance = resolve_working_instance(app=self, session=self.session)

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
        if new != old and new is not None:
            self.handle_tabsdata_server_connection()

    def handle_tabsdata_server_connection(self):
        self.tabsdata_server = tabsdata_api.initialize_tabsdata_server_connection(self)

    @on(ListView.Highlighted)
    async def on_select_highlighted(self, event: ListView.Highlighted):
        # Scroll the highlighted list itself into view
        item = event.list_view.highlighted_child
        if item:
            item.scroll_visible()

    @on(Button.Pressed, "#exit-btn")
    def on_exit_pressed(self, event: Button.Pressed) -> None:
        self.exit()


def run_app():
    NestedMenuApp().run()


if __name__ == "__main__":
    run_app()
