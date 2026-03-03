import asyncio

import sqlalchemy
import textual
from rich.traceback import install
from sqlalchemy import inspect
from textual import on, work
from textual.app import App
from textual.reactive import reactive
from textual.screen import Screen
from textual.widgets import Button, ListView
from textual.worker import Worker, WorkerState

from tdconsole.core import tabsdata_api
from tdconsole.core.db import start_session
from tdconsole.core.find_instances import query_session, resolve_working_instance
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
        self._pending_tabsdata_connect = False
        self.session = start_session()[0]
        self.session.info["app"] = self
        self.tabsdata_server = None
        self.working_instance = resolve_working_instance(app=self, session=self.session)

    def on_mount(self) -> None:
        # start with a MainMenu instance
        process_response(self, "_mount")
        self.handle_tabsdata_server_connection()

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
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            self._pending_tabsdata_connect = True
            return

        self._pending_tabsdata_connect = False
        self._connect_tabsdata_server_worker()

    @work(
        thread=True,
        exclusive=True,
        group="tabsdata-server-connection",
        exit_on_error=False,
    )
    def _connect_tabsdata_server_worker(self):
        return tabsdata_api.initialize_tabsdata_server_connection(self)

    def on_worker_state_changed(self, event: Worker.StateChanged) -> None:
        if event.worker.group != "tabsdata-server-connection":
            return

        if event.state == WorkerState.SUCCESS:
            payload = event.worker.result or {}
            self.tabsdata_server = payload.get("server")
            login_success = payload.get("login_success")
            if login_success is True:
                self.notify("Login Successful")
            elif login_success is False:
                self.notify("Login Failed", severity="error")
            self._refresh_home_screen_data()
        elif event.state == WorkerState.ERROR:
            self.tabsdata_server = None
            self.notify("Login Failed", severity="error")
            self._refresh_home_screen_data()

    def _refresh_home_screen_data(self) -> None:
        for screen in reversed(self.screen_stack):
            if screen.__class__.__name__ != "HomeTabbedScreen":
                continue

            try:
                screen._queue_autocomplete_refresh(force=True)
            except Exception:
                pass

            try:
                from tdconsole.textual_assets.textual_screens import InstanceInfoPanel

                panel = screen.query_one(InstanceInfoPanel)
                panel.refresh_widget()
            except Exception:
                pass
            break


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
