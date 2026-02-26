from __future__ import annotations

import ast
import asyncio
import asyncio.subprocess
import fcntl
import os
import pty
import random
import re
import shlex
import struct
import subprocess
import termios
import time
from dataclasses import dataclass
from functools import partial
from pathlib import Path
from typing import Awaitable, Callable, Iterable, List, Optional

from rich.console import Group, RenderableType
from rich.panel import Panel
from rich.text import Text
from sqlalchemy.orm import Session
from tabsdata.api.tabsdata_server import Collection, Function, TabsdataServer
from textual import events, on, work
from textual.app import ComposeResult
from textual.containers import (
    Center,
    Container,
    Horizontal,
    Vertical,
    VerticalScroll,
)
from textual.events import Key, ScreenResume
from textual.geometry import Offset, Region, Spacing
from textual.reactive import reactive
from textual.screen import ModalScreen, Screen
from textual.widgets import (
    Button,
    Checkbox,
    ContentSwitcher,
    DirectoryTree,
    Footer,
    Input,
    Label,
    ListItem,
    ListView,
    Pretty,
    RichLog,
    Static,
    Tab,
    Tabs,
)
from textual.widgets._tree import TreeNode
from textual_autocomplete._autocomplete import DropdownItem, TargetState

from tdconsole.core import input_validators, instance_tasks, tabsdata_api
from tdconsole.core.construct_command_trie import CliAutoComplete, Node
from tdconsole.core.find_instances import (
    instance_name_to_instance,
    sync_filesystem_instances_to_db,
)
from tdconsole.core.models import Instance
from tdconsole.textual_assets.spinners import SpinnerWidget


class ExitBar(Container):
    DEFAULT_CSS = """
    ExitBar {
        width: auto;
        min-width: 6;
        height: 3;
        margin: 0;
    }
    #exit-btn {
        color: #eaf0fb;
        background: #1e2531;
        border: round #5f7087;
        width: 5;
        min-width: 5;
        height: 3;
        content-align: center middle;
        text-style: bold;
    }
    #exit-btn:hover {
        background: #2c3647;
        border: round #8fa2bf;
    }
    #exit-btn:focus {
        background: #32405a;
        border: round #9ab2d6;
    }
    .exit-spacer {
        width: 1fr;
    }
    """

    def __init__(self, *, mode=None, **kwargs):
        super().__init__(**kwargs)
        self.mode = mode  # "exit" or "pop"

    def compose(self) -> ComposeResult:
        yield Button("x", id="exit-btn")

    @on(Button.Pressed, "#exit-btn")
    def on_exit_pressed(self, event: Button.Pressed) -> None:
        if self.mode == "dismiss":
            self.app.screen.dismiss(None)
        else:
            self.app.exit()


class RefreshBar(Container):
    DEFAULT_CSS = """
    RefreshBar {
        width: auto;
        min-width: 6;
        height: 3;
    }
    #refresh-btn {
        color: #eaf0fb;
        background: #1e2531;
        border: round #5f7087;
        width: 5;
        min-width: 5;
        height: 3;
        content-align: center middle;
        text-style: bold;
    }
    #refresh-btn:hover {
        background: #2c3647;
        border: round #8fa2bf;
    }
    #refresh-btn:focus {
        background: #32405a;
        border: round #9ab2d6;
    }
    .refresh-spacer {
        width: 1fr;
    }
    """

    def compose(self) -> ComposeResult:
        yield Button("↻", id="refresh-btn")

    @on(Button.Pressed, "#refresh-btn")
    def on_refresh_pressed(self, event: Button.Pressed) -> None:
        try:
            self.screen.query_one(InstanceInfoPanel).refresh(recompose=True)
        except:
            pass


class BackBar(Container):
    DEFAULT_CSS = """
    BackBar {
        width: auto;
        min-width: 6;
        height: 3;
    }
    #back-btn {
        color: #eaf0fb;
        background: #1e2531;
        border: round #5f7087;
        width: 5;
        min-width: 5;
        height: 3;
        content-align: center middle;
        text-style: bold;
    }
    #back-btn:hover {
        background: #2c3647;
        border: round #8fa2bf;
    }
    #back-btn:focus {
        background: #32405a;
        border: round #9ab2d6;
    }
    .back-spacer {
        width: 1fr;
    }
    """

    def compose(self) -> ComposeResult:
        yield Button("←", id="back-btn")

    @on(Button.Pressed, "#back-btn")
    def on_back_pressed(self, event: Button.Pressed) -> None:
        # Match app back behavior (if possible), otherwise pop one screen.
        try:
            self.app.action_go_back()
        except Exception:
            try:
                self.app.pop_screen()
            except Exception:
                pass


class WindowControls(Horizontal):
    DEFAULT_CSS = """
    WindowControls {
        width: 1fr;
        height: auto;
    }
    .window-controls-spacer {
        width: 1fr;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static("", classes="window-controls-spacer")
        yield BackBar()
        yield RefreshBar()
        yield ExitBar()


class CreateMenuButton(Container):
    DEFAULT_CSS = """
    CreateMenuButton {
        width: auto;
        min-width: 6;
        height: 3;
    }
    #create-menu-btn {
        color: #eaf0fb;
        background: #1e2531;
        border: round #5f7087;
        width: 5;
        min-width: 5;
        height: 3;
        content-align: center middle;
        text-style: bold;
    }
    #create-menu-btn:hover {
        background: #2c3647;
        border: round #8fa2bf;
    }
    #create-menu-btn:focus {
        background: #32405a;
        border: round #9ab2d6;
    }
    """

    def compose(self) -> ComposeResult:
        yield Button("+", id="create-menu-btn")


class BSOD(Screen):
    BINDINGS = [
        ("escape", "app.pop_screen", "Back"),
        ("left", "focus_back", "Focus Back"),
        ("right", "focus_exit", "Focus Exit"),
    ]

    CSS = """
    BSOD {
        background: blue;
        color: white;
        align: center middle;
        width: auto;
    }

    #wrapper {
        align: center middle;
    }

    #title {
        content-align: center middle;
        text-style: reverse;
        margin-bottom: 1;
    }

    #spinner {
        content-align: center middle;
        align: center middle;
    }

    #message {
        content-align: center middle;
        margin-bottom: 1;
    }

    #buttons {
        align: center middle;
        height: 3;
    }

    Button {
        margin: 0 2;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self.ERROR_TEXT = (
            "uh-oh, you've stumbled upon something Daniel hasn't built out yet :("
        )

    def compose(self) -> ComposeResult:
        yield ExitBar()
        with VerticalScroll(id="wrapper"):
            yield Static(" Bad News :() ", id="title")

            # ✅ ONE SINGLE EMOJI, CENTERED
            yield Horizontal(Center(SpinnerWidget("material", id="spinner")))

            yield Static(self.ERROR_TEXT, id="message")

            with Horizontal(id="buttons"):
                yield Button("Back", id="back-btn")
                yield Button("Exit", id="exit-btn")

    def on_mount(self) -> None:
        self.query_one("#back-btn", Button).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back-btn":
            self.app.pop_screen()
        elif event.button.id == "exit-btn":
            self.app.exit()

    def action_focus_back(self) -> None:
        self.query_one("#back-btn", Button).focus()

    def action_focus_exit(self) -> None:
        self.query_one("#exit-btn", Button).focus()


class InstanceWidget(Static):
    """Rich panel showing the current working instance."""

    def __init__(self, inst: Optional[str] = None, **kwargs):
        super().__init__(**kwargs)
        if isinstance(inst, str):
            inst = instance_name_to_instance(inst)
        self.inst = inst

    def _make_instance_panel(self) -> Panel:

        inst = self.inst

        status_color = "#e4e4e6"
        status_line = "○ No Instance Selected"
        line1 = "No External Running Port"
        line2 = "No Internal Running Port"

        if inst is None:
            pass
        elif inst.name == "_Create_Instance":
            status_color = "#1F66D1"
            status_line = "Create a New Instance"
            line1 = ""
            line2 = ""
        elif inst.status == "Running":
            status_color = "#22c55e"
            status_line = f"{inst.name}  ● Running"
            line1 = f"running on → ext: {inst.arg_ext}"
            line2 = f"running on → int: {inst.arg_int}"
        elif inst.status == "Not Running":
            status_color = "#4c4c4c"
            status_line = f"{inst.name}  ○ Not running"
            line1 = f"configured on → ext: {inst.cfg_ext}"
            line2 = f"configured on → int: {inst.cfg_int}"

        header = Text(status_line, style=f"bold {status_color}")
        body = Text(f"{line1}\n{line2}", style="#f9f9f9")

        return Panel(
            Group(header, body),
            border_style=status_color,
            expand=False,
        )

    def render(self) -> RenderableType:
        # inner instance panel
        instance_panel = self._make_instance_panel()
        return instance_panel


from textual import on
from textual.containers import Container
from textual.widgets import Static


class CollectionModal(ModalScreen):
    CSS = """
    CollectionModal {
        width: 100%;
        height: 100%;
        align: center middle;
        background: rgba(0,0,0,0.25);
    }

    #popup {
        width: 60%;
        height: 80%;
        border: round $primary;
        background: $panel;
        padding: 1 2;
    }

    #title {
        margin-bottom: 1;
    }

    #popup > ListView {
        width: 100%;
        height: 1fr;
    }
    """

    def __init__(self, server, collection) -> None:
        super().__init__()
        self.server = server
        self.collection = collection

    def compose(self) -> ComposeResult:
        with Container(id="popup"):
            yield ExitBar(mode="dismiss")
            if isinstance(self.collection, Collection):
                options = ["Delete Collection"]
                yield Static(
                    f"What would you like to do with the {self.collection.name} collection?",
                    id="title",
                )
                yield ListView(*[LabelItem(o) for o in options])
            else:
                yield Static(
                    "What would you like to call your collection?",
                    id="title",
                )
                yield Input(
                    validate_on=["submitted"],
                    validators=[
                        input_validators.ValidCollectionName(
                            self.app, self.app.tabsdata_server
                        )
                    ],
                )

    @on(ListView.Selected)
    def _picked(self, event: ListView.Selected) -> None:
        selected = event.item.label
        if selected == "Delete Collection":
            server: TabsdataServer = self.server
            delete_collection = server.delete_collection(self.collection.name)
        self.dismiss(delete_collection)

    @on(Input.Submitted)
    def _inputed(self, event: Input.Submitted) -> None:
        value = event.input.value
        if event.validation_result.is_valid:
            server: TabsdataServer = self.server
            print(value)
            create_collection = server.create_collection(value)
            self.dismiss(create_collection)
        else:
            self.app.notify(f"{event.validation_result.failure_descriptions}")


class FunctionModal(ModalScreen):
    CSS = """
    FunctionModal {
        width: 100%;
        height: 100%;
        align: center middle;
        background: rgba(0,0,0,0.25);
    }

    #popup {
        width: 60%;
        height: 80%;
        border: round $primary;
        background: $panel;
        padding: 1 2;
    }

    #title {
        margin-bottom: 1;
    }

    #popup > ListView {
        width: 100%;
        height: 1fr;
    }
    """

    def __init__(self, server, collection, function) -> None:
        super().__init__()
        self.server = server
        self.collection = collection
        self.function = function
        self.collection_name = "No Collection provided"
        if self.collection is not None:
            self.collection_name = self.collection.name

    def compose(self) -> ComposeResult:
        with Container(id="popup"):
            yield ExitBar(mode="dismiss")
            if isinstance(self.function, Function):
                options = ["Trigger Function"]
                yield Static(
                    f"What would you like to do with the {self.function.name} function?",
                    id="title",
                )
                yield ListView(*[LabelItem(o) for o in options])
            else:
                yield Static(
                    "What would you like to call your function?",
                    id="title",
                )
                yield Vertical(
                    Horizontal(
                        Label(
                            "Collection Name:",
                            id="collection-name-label",
                        ),
                        Input(
                            placeholder=self.collection_name,
                            disabled=True,
                            compact=True,
                            id="collection-name-input",
                            classes="inputs",
                        ),
                        Pretty("", id="collection-message"),
                    ),
                    id="collection-container",
                    classes="input_container",
                )
                yield Vertical(
                    Horizontal(
                        Label("Function Name", id="function-name-label"),
                        Input(
                            compact=True,
                            validate_on=["submitted"],
                            validators=[input_validators.PlaeholderValidator()],
                            id="function-name-input",
                            classes="inputs",
                        ),
                        Pretty("", id="function-name-message"),
                    ),
                    id="function-name-container",
                    classes="input_container",
                )
                yield Vertical(
                    Horizontal(
                        Label("Function Path", id="function-path-label"),
                        Input(
                            compact=True,
                            validate_on=["submitted"],
                            validators=[input_validators.PlaeholderValidator()],
                            id="function-path-input",
                            classes="inputs",
                        ),
                        Pretty("", id="function-path-message"),
                    ),
                    id="function-path-container",
                    classes="input_container",
                )
                yield Vertical(
                    Horizontal(
                        Label("Function Body Name", id="function-body-name-label"),
                        Input(
                            compact=True,
                            validate_on=["submitted"],
                            validators=[input_validators.PlaeholderValidator()],
                            id="function-vody-name-input",
                            classes="inputs",
                        ),
                        Pretty("", id="function-body-name-message"),
                    ),
                    id="function-body-name-container",
                    classes="input_container",
                )
                yield Vertical(
                    Button(
                        label="Submit",
                        id="submit-button",
                        classes="submit-button",
                    ),
                    id="submit-container",
                    classes="button_container",
                )

    @on(ListView.Selected)
    def _picked(self, event: ListView.Selected) -> None:
        selected = event.item.label
        if selected == "Trigger Function":
            function_name = getattr(self.function, "name", str(self.function))
            collection_name = getattr(self.collection, "name", None)
            self.dismiss(
                {
                    "action": "trigger",
                    "collection": collection_name,
                    "function": function_name,
                }
            )
            return
        self.dismiss(None)

    @on(Input.Submitted)
    def _inputed(self, event: Input.Submitted) -> None:
        value = event.input.value
        if event.validation_result.is_valid:
            server: TabsdataServer = self.server
            print(value)
            create_collection = server.create_collection(value)
            self.dismiss(create_collection)
        else:
            self.app.notify(f"{event.validation_result.failure_descriptions}")


class InstanceInfoPanel(Horizontal):
    DEFAULT_CSS = """
InstanceInfoPanel > Horizontal {
    height: 10;
}
InstanceInfoPanel {
max-height: 70%;}

InstanceInfoPanel .box {
    height: 1fr;
    width: 1fr;
    layout: vertical;
}

InstanceInfoPanel .box > ListView {
    height: 1fr;
}
    """

    def __init__(self):
        super().__init__()
        self.tabsdata_server = None
        self.instance = None
        self.collection_list = []
        self.selected_collection = None
        self.selected_collection_name = None
        self.selected_function = None
        self.selected_function_name = None
        self.function_list = []
        self.selected_function = None
        self.table_list = []
        self.selected_table = None
        self.selected_table_name = None
        self.recompile_td_data()
        tabsdata_api.sync_instance_to_db(self.app)

    def resolve_working_instance(self, instance=None):
        if isinstance(instance, str):
            instance = instance_name_to_instance(instance)
        sync_filesystem_instances_to_db(app=self.app)
        working_instance = self.app.app_query_session(
            "instances", limit=1, working=True
        )
        return working_instance or instance

    def refresh_widget(self):
        self.recompile_td_data()
        self.refresh(recompose=True)

    def recompile_td_data(self):
        self.instance = self.resolve_working_instance()
        self.tabsdata_server = self.app.tabsdata_server
        self.tabsdata_server: TabsdataServer
        try:
            self.collection_list = self.tabsdata_server.list_collections()
            self.selected_collection = None
            if self.selected_collection_name is not None:
                self.selected_collection = next(
                    (
                        item
                        for item in self.collection_list
                        if getattr(item, "name", item) == self.selected_collection_name
                    ),
                    None,
                )

            if self.selected_collection and self.tabsdata_server:
                coll_name = getattr(self.selected_collection, "name", None)
                self.function_list = self.tabsdata_server.list_functions(coll_name)
                self.table_list = self.tabsdata_server.list_tables(coll_name)
            else:
                self.function_list = []
                self.table_list = []
        except:
            self.function_list = []
            self.table_list = []
            self.selected_collection = None

    @on(
        events.Click,
        "CurrentCollectionsWidget Label, CurrentCollectionsWidget LabelItem",
    )
    async def handle_double_click_collection(self, event: events.Click):
        if event.button == 1 and getattr(event, "chain", 1) >= 2:
            if isinstance(event.widget, LabelItem):
                label = event.widget
            else:
                label = event.widget.parent
            if isinstance(label.label, (Collection, str)):
                collection = self.handle_collection_modal_response(
                    self.app.tabsdata_server, label
                )
                print(collection)
                self.refresh(recompose=True)

    @on(
        events.Click,
        "CurrentFunctionsWidget Label, CurrentFunctionsWidget LabelItem",
    )
    async def handle_double_click_function(self, event: events.Click):
        if event.button == 1 and getattr(event, "chain", 1) >= 2:
            if isinstance(event.widget, LabelItem):
                label = event.widget
            else:
                label = event.widget.parent
            if isinstance(label.label, (Function, str)):
                collection = self.handle_function_modal_response(
                    self.app.tabsdata_server, label
                )
                print(collection)
                self.refresh(recompose=True)

    @on(
        events.Click,
        "CurrentTablesWidget Label, CurrentTablesWidget LabelItem",
    )
    async def handle_double_click_table(self, event: events.Click):
        if event.button == 1 and getattr(event, "chain", 1) >= 2:
            if isinstance(event.widget, LabelItem):
                label = event.widget
            else:
                label = event.widget.parent
            table = label.label
            if isinstance(table, str) and table == "Create a Table":
                return
            table_name = getattr(table, "name", str(table))
            collection_name = (
                getattr(self.selected_collection, "name", None)
                if self.selected_collection is not None
                else None
            )
            if collection_name is None:
                self.app.notify("No collection selected.", severity="error")
                return
            self._open_table_actions_modal(collection_name, table_name)

    @work
    async def _open_table_actions_modal(self, collection_name: str, table_name: str):
        result = await self.app.push_screen_wait(
            TableActionsModal(self.app, collection_name, table_name)
        )
        if isinstance(result, dict) and result.get("action") == "sample":
            self._run_table_sample_cli(collection_name, table_name)

    def _run_table_sample_cli(self, collection_name: str, table_name: str) -> None:
        command = f"td table sample --coll {collection_name} --name {table_name}"
        home_screen = self._find_home_screen()
        if home_screen is None:
            self.app.notify("Home screen not available.", severity="error")
            return
        home_screen.run_cli_command(command, use_pty=False)

    @work
    async def handle_collection_modal_response(self, server, label) -> None:
        print("label is")
        print(label)
        print(label.label)
        result = await self.app.push_screen_wait(
            CollectionModal(self.app.tabsdata_server, label.label)
        )
        return result

    @work
    async def handle_function_modal_response(self, server, label) -> None:
        print("label is")
        print(label)
        print(label.label)
        print(self.selected_collection)
        result = await self.app.push_screen_wait(
            FunctionModal(
                self.app.tabsdata_server,
                getattr(label.label, "collection", self.selected_collection),
                label.label,
            )
        )

        if isinstance(result, dict) and result.get("action") == "trigger":
            self._trigger_function_cli(result)
        return result

    def _trigger_function_cli(self, payload: dict) -> None:
        collection = payload.get("collection")
        function = payload.get("function")
        if not collection or not function:
            self.app.notify("Missing collection or function name.", severity="error")
            return
        command = f"td fn trigger --coll {collection} --name {function}"
        home_screen = self._find_home_screen()
        if home_screen is None:
            self.app.notify("Home screen not available.", severity="error")
            return
        home_screen.run_cli_command(command, use_pty=False)

    def _find_home_screen(self):
        for screen in reversed(self.app.screen_stack):
            if screen.__class__.__name__ == "HomeTabbedScreen":
                return screen
        return None

    def compose(self) -> ComposeResult:
        yield CurrentInstanceWidget(title="Current Instance", classes="box")
        yield CurrentCollectionsWidget(title="Current Collection", classes="box")
        yield CurrentFunctionsWidget(
            title="Available Functions", classes="box collection_dependent"
        )
        yield CurrentTablesWidget(
            title="Available Tables", classes="box collection_dependent"
        )

    def watch_working_instance(self, old, new):
        pass


class CurrentStateWidgetTemplate(Static):
    DEFAULT_CSS = """
    CurrentStateWidgetTemplate {
        border: round #0f766e;
        border-title-align: center;
        border-title-color: #0f766e;
        content-align: center middle;
    }

    ListView {
    max-height: 100%;
    }


    CurrentStateWidgetTemplate > .inner {
        width: auto;
    }
    .section-title {
        padding-left: 1;
        color: #cfd7e6;
        text-style: bold;
    }
    VerticalScroll { height: 1fr; }
    ListView ListItem.--highlight {
        background: #0f766e;
        color: white;
    }
    """

    inst = reactive(None, recompose=True)

    def __init__(
        self,
        instance: Optional[str] = None,
        title: str = "Current Working Instance:",
        dependency=None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.instance = instance
        self.title = title
        self.dependency = dependency

    def generate_internals(self):
        return Static("null", classes="inner")

    def compose(self):
        self.border_title = self.title
        yield self.generate_internals()


class CurrentInstanceWidget(CurrentStateWidgetTemplate):
    def generate_internals(self):
        instance = self.app.working_instance

        status_color = "#e4e4e6"
        status_line = "○ No Instance Selected"
        line1 = "No External Running Port"
        line2 = "No Internal Running Port"

        if instance is None:
            pass
        elif instance.name == "_Create_Instance":
            status_color = "#1F66D1"
            status_line = "Create a New Instance"
            line1 = ""
            line2 = ""
        elif instance.status == "Running":
            status_color = "#22c55e"
            status_line = f"{instance.name}  ● Running"
            line1 = f"running on → ext: {instance.arg_ext}"
            line2 = f"running on → int: {instance.arg_int}"
        elif instance.status == "Not Running":
            status_color = "#4c4c4c"
            status_line = f"{instance.name}  ○ Not running"
            line1 = f"configured on → ext: {instance.cfg_ext}"
            line2 = f"configured on → int: {instance.cfg_int}"

        header = Text(status_line, style=f"bold {status_color}")
        body = Text(f"{line1}\n{line2}", style="#f9f9f9")

        return Static(
            Panel(Group(header, body), border_style=status_color, expand=False),
            classes="inner",
        )


class CurrentCollectionsWidget(CurrentStateWidgetTemplate):
    def generate_internals(self, collections=None):
        """Converts List to a ListView"""
        collections = list(self.parent.collection_list or [])
        choiceLabels = [
            LabelItem(getattr(i, "name", ""), i) for i in collections
        ]
        self.list = ListView(*choiceLabels)
        selected_name = self.parent.selected_collection_name
        if selected_name:
            for idx, item in enumerate(collections):
                if getattr(item, "name", item) == selected_name:
                    self.list.index = idx
                    break
        return Vertical(self.list, classes="inner")

    @on(ListView.Selected)
    def handle_collection_selected(self, event: ListView.Selected):
        event.stop()
        collection = event.item.label
        self.parent.selected_collection = collection
        self.parent.selected_collection_name = getattr(collection, "name", collection)

        self.parent.selected_function = None
        self.parent.selected_function_name = None
        self.parent.selected_table = None
        self.parent.selected_table_name = None
        self.parent.recompile_td_data()
        widgets_to_refresh = self.screen.query(".collection_dependent")
        for i in widgets_to_refresh:
            i.refresh(recompose=True)


class CurrentFunctionsWidget(CurrentStateWidgetTemplate):

    def generate_internals(self, functions=None):
        """Converts List to a ListView"""
        functions = list(self.parent.function_list or [])

        functions.append("Create a Function")
        choiceLabels = [
            LabelItem(getattr(i, "name", "Create a Function"), i) for i in functions
        ]
        self.list = ListView(*choiceLabels)
        selected_name = self.parent.selected_function_name
        if selected_name:
            for idx, item in enumerate(functions):
                if getattr(item, "name", item) == selected_name:
                    self.list.index = idx
                    break
        return self.list

    @on(ListView.Selected)
    def handle_function_selected(self, event: ListView.Selected):
        event.stop()
        value = event.item.label
        self.parent.selected_function = value
        self.parent.selected_function_name = getattr(value, "name", value)


class CurrentTablesWidget(CurrentStateWidgetTemplate):
    DEFAULT_CSS = """
    CurrentTablesWidget ListItem.--highlight {
        background: #0f766e;
        color: white;
    }
    """

    def generate_internals(self, collections=None):
        """Converts List to a ListView"""
        tables = list(self.parent.table_list or [])

        tables.append("Create a Table")
        choiceLabels = [
            LabelItem(getattr(i, "name", "Create a Function"), i) for i in tables
        ]
        self.list = ListView(*choiceLabels)
        selected_name = self.parent.selected_table_name
        if selected_name:
            for idx, item in enumerate(tables):
                if getattr(item, "name", item) == selected_name:
                    self.list.index = idx
                    break
        return self.list

    @on(ListView.Selected)
    def handle_table_selected(self, event: ListView.Selected):
        event.stop()
        value = event.item.label
        self.parent.selected_table = value
        self.parent.selected_table_name = getattr(value, "name", value)


class LabelItem(ListItem):
    def __init__(self, label: str, override_label=None) -> None:
        super().__init__()
        if type(label) is str:
            self.front = Label(label)
        else:
            self.front = label
        self.label = label
        if override_label is not None:
            self.label = override_label

    def compose(self) -> ComposeResult:
        yield self.front


class TableActionsModal(ModalScreen):
    CSS = """
    TableActionsModal {
        width: 100%;
        height: 100%;
        align: center middle;
        background: rgba(0,0,0,0.25);
    }

    #table-actions-popup {
        width: 50%;
        height: 50%;
        border: round $primary;
        background: $panel;
        padding: 1 2;
    }

    #table-actions-title {
        margin-bottom: 1;
    }

    #table-actions-popup > ListView {
        width: 100%;
        height: 1fr;
    }
    """

    def __init__(self, app, collection: str, table: str) -> None:
        super().__init__()
        self._app_ref = app
        self.collection = collection
        self.table = table

    def compose(self) -> ComposeResult:
        with Container(id="table-actions-popup"):
            yield ExitBar(mode="dismiss")
            yield Static(
                f"Table actions: {self.collection}.{self.table}",
                id="table-actions-title",
            )
            yield ListView(*[LabelItem("Sample Data")])

    @on(ListView.Selected)
    def on_list_view_selected(self, event: ListView.Selected) -> None:
        selected = event.item.label
        if selected == "Sample Data":
            self.dismiss(
                {
                    "action": "sample",
                    "collection": self.collection,
                    "table": self.table,
                }
            )
            return
        self.dismiss(None)


class CreateMenuModal(ModalScreen):
    CSS = """
    CreateMenuModal {
        width: 100%;
        height: 100%;
        align: center middle;
        background: rgba(0,0,0,0.25);
    }

    #create-menu-popup {
        width: 50%;
        height: 50%;
        border: round $primary;
        background: $panel;
        padding: 1 2;
    }

    #create-menu-title {
        margin-bottom: 1;
    }

    #create-menu-popup > ListView {
        width: 100%;
        height: 1fr;
    }
    """

    def compose(self) -> ComposeResult:
        with Container(id="create-menu-popup"):
            yield ExitBar(mode="dismiss")
            yield Static("Create...", id="create-menu-title")
            yield ListView(
                *[
                    LabelItem("Create Collection"),
                    LabelItem("Create Function"),
                ]
            )

    @on(ListView.Selected)
    def on_list_view_selected(self, event: ListView.Selected) -> None:
        selected = event.item.label
        if selected == "Create Collection":
            self.dismiss({"action": "create_collection"})
            return
        if selected == "Create Function":
            self.dismiss({"action": "create_function"})
            return
        self.dismiss(None)

class ListScreenTemplate(Screen):
    def __init__(self, choice_dict=None, header="Select a File: "):
        super().__init__()
        self.choice_dict = choice_dict
        self.choices = list(choice_dict.keys())
        self.header = header
        # self.app.working_instance = self.app.app_query_session(
        #     "instances", working=True
        # )

    def compose(self) -> ComposeResult:
        with VerticalScroll():
            yield WindowControls()
            yield InstanceInfoPanel()
            yield self.list_items()
            yield Footer()

    def on_show(self) -> None:
        # called again when you push this screen a
        #  second time (if reused)
        self.set_focus(self.list)

    def list_items(self):
        """Converts List to a ListView"""
        choiceLabels = [LabelItem(i) for i in self.choices]
        self.list = ListView(*choiceLabels)
        return self.list

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        selected = event.item.label
        if selected == "Exit":
            self.app.exit()
        elif selected in self.choices and self.choice_dict[selected] is not None:
            screen = self.choice_dict[selected]
            self.app.push_screen(screen())
        else:
            self.app.push_screen(BSOD())

    @on(ScreenResume)
    def refresh_current_instance_widget(self, event: ScreenResume):
        self.query_one(InstanceInfoPanel).refresh_widget()


class InstanceSelectionScreen(ListScreenTemplate):
    BINDINGS = [
        ("enter", "press_close", "Done"),
    ]

    def __init__(self, instances=None, flow_mode=None):
        self.app.flow_mode = flow_mode
        self.instances = self.resolve_instance_list()
        super().__init__(choice_dict=self.instances)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back-btn":
            self.app.pop_screen()

    def on_show(self) -> None:
        self.set_focus(self.list)

    def list_items(self):
        choiceLabels = [
            LabelItem(label=InstanceWidget(i), override_label=i) for i in self.choices
        ]
        self.list = ListView(*choiceLabels)
        return self.list

    def resolve_instance_list(self):
        session: Session = self.app.session
        instance_list = session.query(Instance).all()
        temp_list = []
        if self.app.flow_mode == "bind":
            temp_list = [instance_name_to_instance("_Create_Instance")]
            temp_list.extend(instance_list)
        elif self.app.flow_mode == "start":
            temp_list = [instance_name_to_instance("_Create_Instance")]
            temp_list.extend(instance_list)
        elif self.app.flow_mode == "stop":
            temp_list = session.query(Instance).filter_by(status="Running").all()
            new = new = {
                "name": False,
                "arg_ext": False,
                "arg_int": False,
                "use_https": False,
            }
            return_list = {
                i: partial(StopInstance, current=i, new=new) for i in temp_list
            }
            return return_list
        elif self.app.flow_mode == "delete":
            temp_list = session.query(Instance).all()
            new = new = {
                "name": False,
                "arg_ext": False,
                "arg_int": False,
                "use_https": False,
            }
            return_list = {
                i: partial(DeleteInstance, current=i, new=new) for i in temp_list
            }
            return return_list
        else:
            temp_list = session.query(Instance).all()

        return_list = {i: partial(PortConfigScreen, instance=i) for i in temp_list}
        return return_list

    def action_press_close(self) -> None:
        # Only act if the button exists
        try:
            btn = self.query_one("#close-btn", Button)
        except Exception:
            return
        btn.press()

    def on_mount(self) -> None:
        """Called after the screen is added to the app and widgets are mounted."""
        try:
            btn = self.query_one("#back-btn", Button)
            btn.focus()
        except:
            # This is fine when instances is not None and there is no back button
            pass


class MainScreen(ListScreenTemplate):

    def __init__(self):
        super().__init__(
            choice_dict={
                "Instance Management": InstanceManagementScreen,
                "Asset Management": AssetManagementScreen,
                "Workflow Management (Not Built Yet)": None,
                "Config Management (Not Built Yet)": None,
                "Exit": None,
            },
        )

    @on(ScreenResume)
    def handle_old_screens(self, event: ScreenResume):
        screen_stack = self.app.screen_stack
        if isinstance(screen_stack[-1], MainScreen) and len(screen_stack) > 2:
            while len(self.app.screen_stack) > 2:
                self.app.pop_screen()


class BottomAwareCliAutoComplete(CliAutoComplete):
    """Place autocomplete above the input when there is not enough room below."""

    def get_search_string(self, state: TargetState) -> str:
        # Candidates are already pre-filtered in candidates_callback.
        # Returning an empty search string bypasses fuzzy filtering that can hide
        # valid next-token suggestions (e.g. "td" -> "table"/"fn").
        return ""

    def should_show_dropdown(self, search_string: str) -> bool:
        return self.option_list.option_count > 0

    def _align_to_target(self) -> None:
        x, y = self.target.cursor_screen_offset
        dropdown = self.option_list
        width, height = dropdown.outer_size
        region = self.screen.scrollable_content_region

        below_space = max(0, region.bottom - (y + 1))
        above_space = max(0, y - region.y)
        show_above = below_space < min(height, 4) and above_space > below_space
        desired_y = y - height if show_above else y + 1

        x, y, _width, _height = Region(x - 1, desired_y, width, height).constrain(
            "inside",
            "none",
            Spacing.all(0),
            region,
        )
        self.absolute_offset = Offset(x, y)


class HomeTabbedScreen(Screen):
    CSS = """
    #home-topbar {
        width: 1fr;
        height: 3;
        min-height: 3;
        max-height: 3;
        align: left middle;
    }
    #home-tabs-nav {
        width: 1fr;
        height: 3;
        margin: 0;
        padding: 0;
    }
    #home-tabs-nav Tab {
        height: 3;
        margin: 0 1 0 0;
        padding: 0 2;
        content-align: center middle;
        border: round #4d5c71;
        background: #1a2230;
        color: #cfd7e6;
    }
    #home-tabs-nav Tab:hover {
        border: round #7e91ad;
        background: #253245;
        color: #f1f5fb;
    }
    #home-tabs-nav Tab.-active {
        border: round #9db3d4;
        background: #2f3f57;
        color: #ffffff;
        text-style: bold;
    }
    #home-controls {
        width: auto;
        height: 3;
        layout: horizontal;
        align: right middle;
    }
    #home-switcher {
        height: 1fr;
    }
    #main-list {
        height: 1fr;
    }
    #cli-pane {
        height: 1fr;
    }
    #cli-prompt {
        height: 1;
        padding: 0 1;
        background: $surface;
        color: $text-muted;
    }
    #cli-log {
        height: 1fr;
        border: round $accent;
    }
    #cli-input {
        height: 3;
    }
    #main-scroll {
        height: 1fr;
        overflow-y: auto;
    }
    #main-list {
        height: auto;
        overflow-y: hidden;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self.cwd = Path.cwd()
        self.cli_root = self._build_cli_tree()
        self.main_choice_dict = {
            "Instance Management": InstanceManagementScreen,
            "Asset Management": AssetManagementScreen,
            "Workflow Management (Not Built Yet)": None,
            "Config Management (Not Built Yet)": None,
            "Exit": None,
        }
        self.choices = list(self.main_choice_dict.keys())
        self.cli_prompt_widget: Static | None = None
        self.cli_log_widget: RichLog | None = None
        self.cli_input_widget: Input | None = None
        self._cli_screen_lines: list[str] = [""]
        self._cli_cursor_row: int = 0
        self._cli_cursor_col: int = 0
        self._cli_saved_cursor: tuple[int, int] | None = None
        self._cli_last_render: float = 0.0
        self._cli_rows: int = 40
        self._cli_cols: int = 120
        self._cli_screen: list[list[str]] = []
        self._pending_cli_command: str | None = None
        self._pending_cli_use_pty: bool = True

    def compose(self) -> ComposeResult:
        with Horizontal(id="home-topbar"):
            yield Tabs(
                Tab("Main", id="main-tab"),
                Tab("CLI", id="cli-tab"),
                id="home-tabs-nav",
            )
            with Horizontal(id="home-controls"):
                yield CreateMenuButton()
                yield BackBar()
                yield RefreshBar()
                yield ExitBar()

        with ContentSwitcher(initial="main-panel", id="home-switcher"):
            with Vertical(id="main-panel"):
                with VerticalScroll(id="main-scroll"):
                    yield InstanceInfoPanel()
                    yield ListView(
                        *[LabelItem(choice) for choice in self.choices], id="main-list"
                    )
            with Vertical(id="cli-panel"):
                with Vertical(id="cli-pane"):
                    yield Static("", id="cli-prompt")
                    yield RichLog(
                        id="cli-log", wrap=False, highlight=True, markup=False
                    )
                    input_widget = Input(
                        placeholder="Type a command and press Enter", id="cli-input"
                    )
                    yield input_widget
                    yield BottomAwareCliAutoComplete(
                        input_widget, candidates=self.candidates_callback
                    )
        yield Footer()

    def on_mount(self) -> None:
        self.cli_prompt_widget = self.query_one("#cli-prompt", Static)
        self.cli_log_widget = self.query_one("#cli-log", RichLog)
        self.cli_input_widget = self.query_one("#cli-input", Input)
        self._refresh_prompt()
        self._log_line("Built-ins: cd, clear, pwd, exit")
        self.query_one("#main-list", ListView).focus()

    @on(Button.Pressed, "#create-menu-btn")
    def on_create_menu_pressed(self, event: Button.Pressed) -> None:
        self._open_create_menu()

    @work
    async def _open_create_menu(self) -> None:
        result = await self.app.push_screen_wait(CreateMenuModal())
        if isinstance(result, dict):
            action = result.get("action")
            if action == "create_collection":
                self.app.push_screen(CollectionModal(self.app.tabsdata_server, None))
            elif action == "create_function":
                if Path.home() == Path.cwd():
                    self.app.notify(
                        "❌ Cannot scan root directory! Please run `tdconsole` in a more specific directory to avoid scanning your entire home path.",
                        severity="error",
                    )
                else:
                    self.app.push_screen(PyFileTreeScreen())

    @on(Tabs.TabActivated, "#home-tabs-nav")
    def on_tab_activated(self, event: Tabs.TabActivated) -> None:
        label = str(event.tab.label)
        switcher = self.query_one("#home-switcher", ContentSwitcher)
        if label == "Main":
            switcher.current = "main-panel"
            self.query_one("#main-list", ListView).focus()
        elif label == "CLI":
            switcher.current = "cli-panel"
            self.query_one("#cli-input", Input).focus()

    @on(ListView.Selected, "#main-list")
    def on_main_list_selected(self, event: ListView.Selected) -> None:
        selected = event.item.label
        if selected == "Exit":
            self.app.exit()
        elif selected in self.choices and self.main_choice_dict[selected] is not None:
            screen = self.main_choice_dict[selected]
            self.app.push_screen(screen())
        else:
            self.app.push_screen(BSOD())

    @on(ScreenResume)
    def refresh_current_instance_widget(self, event: ScreenResume):
        self.query_one(InstanceInfoPanel).refresh_widget()
        if self._pending_cli_command:
            self.call_after_refresh(self._execute_pending_cli)

    def _execute_pending_cli(self) -> None:
        if not self._pending_cli_command:
            return
        cmd = self._pending_cli_command
        use_pty = self._pending_cli_use_pty
        self._pending_cli_command = None
        self._pending_cli_use_pty = True
        self.run_cli_command(cmd, use_pty=use_pty)

    @on(Input.Submitted, "#cli-input")
    async def on_cli_input_submitted(self, event: Input.Submitted) -> None:
        command = event.value.strip()
        event.input.value = ""
        if not command:
            return

        self._log_line(f"$ {command}")
        await self._run_command(command)
        self._refresh_prompt()

    async def _run_command(self, command: str, use_pty: bool = False) -> None:
        if command == "clear":
            if self.cli_log_widget is not None:
                self.cli_log_widget.clear()
            return
        if command in {"exit", "quit"}:
            self.app.exit()
            return
        if command == "pwd":
            self._log_line(str(self.cwd))
            return
        if command.startswith("cd"):
            self._handle_cd(command)
            return

        if use_pty:
            master_fd, slave_fd = pty.openpty()
            self._set_pty_winsize(master_fd, slave_fd)
            self._init_cli_screen()
            env = os.environ.copy()
            process = subprocess.Popen(
                command,
                shell=True,
                cwd=str(self.cwd),
                stdin=slave_fd,
                stdout=slave_fd,
                stderr=slave_fd,
                env=env,
                close_fds=True,
            )
            os.close(slave_fd)

            try:
                while True:
                    data = await asyncio.to_thread(os.read, master_fd, 4096)
                    if not data:
                        break
                    chunk = data.decode(errors="replace")
                    self._apply_ansi_chunk(chunk)
            finally:
                os.close(master_fd)

            return_code = await asyncio.to_thread(process.wait)
            self._render_cli_buffer(force=True)
            if return_code != 0:
                self._log_line(f"[exit code: {return_code}]")
        else:
            process = await asyncio.create_subprocess_shell(
                command,
                cwd=str(self.cwd),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                env=os.environ.copy(),
            )
            assert process.stdout is not None
            while True:
                line = await process.stdout.readline()
                if not line:
                    break
                self._log_line(line.decode(errors="replace").rstrip("\n"))

            return_code = await process.wait()
            if return_code != 0:
                self._log_line(f"[exit code: {return_code}]")

    def run_cli_command(self, command: str, use_pty: bool = True) -> None:
        if not self.is_mounted:
            self._pending_cli_command = command
            self._pending_cli_use_pty = use_pty
            return
        switcher = self.query_one("#home-switcher", ContentSwitcher)
        tabs = self.query_one("#home-tabs-nav", Tabs)
        try:
            switcher.current = "cli-panel"
            tabs.active = "cli-tab"
            self.query_one("#cli-input", Input).focus()
        except Exception as e:
            print(e)
            try:
                tabs.active = 2
            except Exception:
                pass
        switcher.current = "cli-panel"
        if self.cli_input_widget is None or self.cli_log_widget is None:
            self.cli_prompt_widget = self.query_one("#cli-prompt", Static)
            self.cli_log_widget = self.query_one("#cli-log", RichLog)
            self.cli_input_widget = self.query_one("#cli-input", Input)
        self.query_one("#cli-input", Input).focus()
        self._log_line(f"$ {command}")
        asyncio.create_task(self._run_command(command, use_pty=use_pty))

    def _handle_cd(self, command: str) -> None:
        parts = shlex.split(command)
        target_raw = parts[1] if len(parts) > 1 else "~"
        target = Path(target_raw).expanduser()
        if not target.is_absolute():
            target = (self.cwd / target).resolve()

        if not target.exists():
            self._log_line(f"cd: no such file or directory: {target_raw}")
            return
        if not target.is_dir():
            self._log_line(f"cd: not a directory: {target_raw}")
            return
        self.cwd = target

    def _refresh_prompt(self) -> None:
        if self.cli_prompt_widget is not None:
            self.cli_prompt_widget.update(f"{self.cwd} $")

    def _log_line(self, text: str) -> None:
        if self.cli_log_widget is not None:
            self.cli_log_widget.write(text)

    def _apply_ansi_chunk(self, chunk: str) -> None:
        # Minimal ANSI/CSI handling to keep live tables readable in RichLog.
        i = 0
        while i < len(chunk):
            ch = chunk[i]
            if ch == "\x1b" and i + 1 < len(chunk) and chunk[i + 1] == "[":
                m = re.match(r"\x1b\[([0-9;?]*)([A-Za-z])", chunk[i:])
                if m:
                    params, code = m.group(1), m.group(2)
                    i += len(m.group(0))
                    self._handle_csi(params, code)
                    continue
            if ch == "\r":
                self._cli_cursor_col = 0
            elif ch == "\b":
                self._cli_cursor_col = max(0, self._cli_cursor_col - 1)
            elif ch == "\n":
                self._cli_cursor_row += 1
                self._cli_cursor_col = 0
                self._ensure_line(self._cli_cursor_row)
            else:
                self._write_char(ch)
            i += 1

        self._render_cli_buffer()

    def _handle_csi(self, params: str, code: str) -> None:
        # Handle the common codes used by Rich/CLI live output.
        if code == "m":
            return  # ignore color/style
        if code == "K":
            # clear to end of line
            self._clear_line(params or "0")
            return
        if code == "J":
            # clear screen
            self._clear_screen(params or "2")
            return
        if code == "A":
            # cursor up
            n = int(params or "1")
            self._cli_cursor_row = max(0, self._cli_cursor_row - n)
            return
        if code == "B":
            # cursor down
            n = int(params or "1")
            self._cli_cursor_row += n
            self._ensure_line(self._cli_cursor_row)
            return
        if code == "E":
            # next line, column 0
            n = int(params or "1")
            self._cli_cursor_row += n
            self._cli_cursor_col = 0
            self._ensure_line(self._cli_cursor_row)
            return
        if code == "F":
            # previous line, column 0
            n = int(params or "1")
            self._cli_cursor_row = max(0, self._cli_cursor_row - n)
            self._cli_cursor_col = 0
            return
        if code == "C":
            # cursor forward
            n = int(params or "1")
            self._cli_cursor_col += n
            return
        if code == "D":
            # cursor back
            n = int(params or "1")
            self._cli_cursor_col = max(0, self._cli_cursor_col - n)
            return
        if code == "G":
            # cursor horizontal absolute (1-based)
            try:
                col = int(params or "1") - 1
            except ValueError:
                col = 0
            self._cli_cursor_col = max(0, col)
            return
        if code == "H":
            # cursor home (ignore column, set row)
            if params:
                parts = params.split(";")
                try:
                    row = int(parts[0]) - 1
                    col = int(parts[1]) - 1 if len(parts) > 1 else 0
                except ValueError:
                    row = 0
                    col = 0
                self._cli_cursor_row = max(0, row)
                self._cli_cursor_col = max(0, col)
                self._ensure_line(self._cli_cursor_row)
            else:
                self._cli_cursor_row = 0
                self._cli_cursor_col = 0
            return
        if code == "s":
            # save cursor
            self._cli_saved_cursor = (self._cli_cursor_row, self._cli_cursor_col)
            return
        if code == "u":
            # restore cursor
            if self._cli_saved_cursor is not None:
                self._cli_cursor_row, self._cli_cursor_col = self._cli_saved_cursor
                self._ensure_line(self._cli_cursor_row)
            return

    def _ensure_line(self, row: int) -> None:
        if row < 0:
            return
        if row >= self._cli_rows:
            row = self._cli_rows - 1
        while len(self._cli_screen) < self._cli_rows:
            self._cli_screen.append([" "] * self._cli_cols)

    def _write_char(self, ch: str) -> None:
        if self._cli_cursor_col >= self._cli_cols:
            self._cli_cursor_row += 1
            self._cli_cursor_col = 0
        if self._cli_cursor_row >= self._cli_rows:
            return
        self._ensure_line(self._cli_cursor_row)
        self._cli_screen[self._cli_cursor_row][self._cli_cursor_col] = ch
        self._cli_cursor_col += 1

    def _render_cli_buffer(self, force: bool = False) -> None:
        if self.cli_log_widget is None:
            return
        now = time.monotonic()
        if not force and now - self._cli_last_render < 0.1:
            return
        self._cli_last_render = now
        self.cli_log_widget.clear()
        if not self._cli_screen:
            return
        for row in self._cli_screen:
            self.cli_log_widget.write("".join(row).rstrip() or " ")

    def _set_pty_winsize(self, master_fd: int, slave_fd: int) -> None:
        cols = 120
        rows = 40
        try:
            if self.cli_log_widget is not None:
                size = self.cli_log_widget.size
                if size.width > 0 and size.height > 0:
                    cols = size.width
                    rows = size.height
        except Exception:
            pass
        self._cli_cols = cols
        self._cli_rows = rows
        try:
            winsize = struct.pack("HHHH", rows, cols, 0, 0)
            fcntl.ioctl(master_fd, termios.TIOCSWINSZ, winsize)
            fcntl.ioctl(slave_fd, termios.TIOCSWINSZ, winsize)
        except Exception:
            pass

    def _init_cli_screen(self) -> None:
        self._cli_screen = [[" "] * self._cli_cols for _ in range(self._cli_rows)]
        self._cli_cursor_row = 0
        self._cli_cursor_col = 0

    def _clear_screen(self, mode: str) -> None:
        self._ensure_line(0)
        if mode == "0":
            # clear from cursor to end of screen
            for r in range(self._cli_cursor_row, self._cli_rows):
                start = self._cli_cursor_col if r == self._cli_cursor_row else 0
                for c in range(start, self._cli_cols):
                    self._cli_screen[r][c] = " "
        elif mode == "1":
            # clear from start to cursor
            for r in range(0, self._cli_cursor_row + 1):
                end = (
                    self._cli_cursor_col
                    if r == self._cli_cursor_row
                    else self._cli_cols
                )
                for c in range(0, end):
                    self._cli_screen[r][c] = " "
        else:
            # mode 2 or default: clear all
            self._cli_screen = [[" "] * self._cli_cols for _ in range(self._cli_rows)]
            self._cli_cursor_row = 0
            self._cli_cursor_col = 0

    def _clear_line(self, mode: str) -> None:
        if self._cli_cursor_row >= self._cli_rows:
            return
        self._ensure_line(self._cli_cursor_row)
        if mode == "2":
            for c in range(self._cli_cols):
                self._cli_screen[self._cli_cursor_row][c] = " "
            self._cli_cursor_col = 0
        elif mode == "1":
            for c in range(0, self._cli_cursor_col + 1):
                self._cli_screen[self._cli_cursor_row][c] = " "
        else:
            for c in range(self._cli_cursor_col, self._cli_cols):
                self._cli_screen[self._cli_cursor_row][c] = " "

    def candidates_callback(self, state: TargetState) -> list[DropdownItem]:
        base_items = self._pull_command_suggestions(self.cli_root, state.text)
        active_param, current_fragment = self._active_parameter_context(state.text)
        scope = self._command_scope(state.text)

        if active_param == "--coll":
            selected_name = self._extract_name_arg(state.text)
            if selected_name:
                items = self._filter_by_prefix(
                    self._collections_for_name(selected_name, scope),
                    current_fragment,
                )
            else:
                items = self._filter_by_prefix(
                    self._live_collection_names(),
                    current_fragment,
                )
        elif active_param == "--name":
            collection = self._extract_collection_arg(state.text)
            if scope == "table":
                dynamic_names = self._live_table_names(collection)
            elif scope == "fn":
                dynamic_names = self._live_function_names(collection)
            else:
                dynamic_names = sorted(
                    set(
                        self._live_function_names(collection)
                        + self._live_table_names(collection)
                    )
                )
            items = self._filter_by_prefix(dynamic_names, current_fragment)
        elif active_param == "--instance":
            items = self._filter_by_prefix(
                self._live_instance_names(),
                current_fragment,
            )
        else:
            if self._is_partial_token_context(state.text):
                items = self._filter_by_prefix(base_items, current_fragment)
            else:
                items = base_items

        return [DropdownItem(item) for item in items]

    def _build_cli_tree(self) -> Node:
        root = Node("root")

        td_node = Node(name="td")
        root.add_child(td_node)

        tdserver_node = Node("tdserver")
        root.add_child(tdserver_node)

        tdserver_node.add_child(["status", "start", "stop", "delete"])
        for i in tdserver_node.children:
            instance_node = i.add_child(Node(name="--instance", parameter=True))
            instance_node.add_child(Node(name="__instance_value__", parameter_arg=True))

        fn = td_node.add_child(Node("fn"))
        fn_sample = fn.add_child("sample")
        fn_schema = fn.add_child("schema")
        fn_sample.add_child(["--coll", "--name"])
        fn_schema.add_child(["--coll", "--name"])

        table = td_node.add_child(Node("table"))
        sample = table.add_child("sample")
        schema = table.add_child("schema")
        sample.add_child(["--coll", "--name"])
        schema.add_child(["--coll", "--name"])

        colls = root.recur_search("--coll")
        for node in colls:
            node.add_child(["__coll_value__"])
            node.parameter = True
            for child in node.children:
                child.parameter_arg = True

        names = root.recur_search("--name")
        for node in names:
            node.add_child(["__name_value__"])
            node.parameter = True
            for child in node.children:
                child.parameter_arg = True

        return root

    def _pull_command_suggestions(self, root: Node, text: str) -> list[str]:
        try:
            split_text = shlex.split(text)
        except ValueError:
            split_text = text.split(" ")

        cursor = root
        children = cursor.children
        param_list = []

        for index, word in enumerate(split_text):
            if not word:
                continue
            is_last = index == len(split_text) - 1
            treat_as_partial = is_last and not text.endswith(" ")
            found_child = cursor.get_child(word)
            if treat_as_partial and found_child is not None:
                # Exact match on the token currently being typed:
                # keep suggestions at current level until user commits with space.
                break
            if not found_child:
                if cursor.parameter is True:
                    # Accept dynamic parameter values (not explicitly in the tree)
                    # and continue from the parameter's parent so sibling flags
                    # like --name can still be suggested.
                    if cursor.parent is not None:
                        param_list = cursor.parent.children
                        cursor = cursor.parent
                        children = cursor.children
                        continue
                    return []
                break
            if found_child.parameter is True:
                param_list = cursor.children
            if found_child.parameter_arg is True:
                param_list = cursor.parent.children
                cursor = cursor.parent
            else:
                cursor = found_child
            children = cursor.children

        results = children
        if len(children) == 0 and len(param_list) > 0:
            results = param_list

        names = [node.name for node in results]
        names = [name for name in names if not name.startswith("__")]
        existing_params = [token for token in split_text if token.startswith("--")]
        return [name for name in names if name not in existing_params]

    def _safe_split(self, text: str) -> list[str]:
        try:
            return shlex.split(text)
        except ValueError:
            return [part for part in text.split(" ") if part]

    def _active_parameter_context(self, text: str) -> tuple[str | None, str]:
        tokens = self._safe_split(text)
        if not tokens:
            return None, ""

        ends_with_space = text.endswith(" ")
        current_fragment = "" if ends_with_space else tokens[-1]

        if ends_with_space:
            previous = tokens[-1]
        else:
            previous = tokens[-2] if len(tokens) > 1 else None

        if previous in {"--coll", "--name", "--instance"}:
            return previous, current_fragment
        return None, current_fragment

    def _extract_collection_arg(self, text: str) -> str | None:
        tokens = self._safe_split(text)
        collection: str | None = None
        for index, token in enumerate(tokens[:-1]):
            if token == "--coll":
                candidate = tokens[index + 1]
                if not candidate.startswith("--"):
                    collection = candidate
        return collection

    def _extract_name_arg(self, text: str) -> str | None:
        tokens = self._safe_split(text)
        name: str | None = None
        for index, token in enumerate(tokens[:-1]):
            if token == "--name":
                candidate = tokens[index + 1]
                if not candidate.startswith("--"):
                    name = candidate
        return name

    def _command_scope(self, text: str) -> str | None:
        tokens = self._safe_split(text)
        if len(tokens) < 2:
            return None
        if tokens[0] != "td":
            if tokens[0] == "tdserver":
                return "tdserver"
            return None
        if tokens[1] in {"table", "fn"}:
            return tokens[1]
        return None

    def _live_collection_names(self) -> list[str]:
        collections = tabsdata_api.pull_all_collections(self.app)
        return sorted({getattr(item, "name", str(item)) for item in collections})

    def _live_function_names(self, collection: str | None) -> list[str]:
        if collection:
            functions = tabsdata_api.pull_functions_from_collection(
                self.app, collection
            )
            return sorted({getattr(item, "name", str(item)) for item in functions})

        names: set[str] = set()
        for coll in self._live_collection_names():
            functions = tabsdata_api.pull_functions_from_collection(self.app, coll)
            names.update(getattr(item, "name", str(item)) for item in functions)
        return sorted(names)

    def _live_table_names(self, collection: str | None) -> list[str]:
        if collection:
            tables = tabsdata_api.pull_tables_from_collection(self.app, collection)
            return sorted({getattr(item, "name", str(item)) for item in tables})

        names: set[str] = set()
        for coll in self._live_collection_names():
            tables = tabsdata_api.pull_tables_from_collection(self.app, coll)
            names.update(getattr(item, "name", str(item)) for item in tables)
        return sorted(names)

    def _filter_by_prefix(self, items: list[str], prefix: str) -> list[str]:
        if not prefix:
            return items
        return [item for item in items if item.startswith(prefix)]

    def _collections_for_name(self, name: str, scope: str | None) -> list[str]:
        matching_collections: list[str] = []
        for coll in self._live_collection_names():
            if scope == "table":
                table_names = self._live_table_names(coll)
                if name in table_names:
                    matching_collections.append(coll)
            elif scope == "fn":
                function_names = self._live_function_names(coll)
                if name in function_names:
                    matching_collections.append(coll)
            else:
                function_names = self._live_function_names(coll)
                table_names = self._live_table_names(coll)
                if name in function_names or name in table_names:
                    matching_collections.append(coll)
        return matching_collections

    def _is_partial_token_context(self, text: str) -> bool:
        """True when the last typed token is partial and should prefix-filter candidates."""
        if text.endswith(" "):
            return False

        tokens = self._safe_split(text)
        if not tokens:
            return False

        cursor = self.cli_root
        for index, token in enumerate(tokens):
            is_last = index == len(tokens) - 1
            found = cursor.get_child(token)
            if not found:
                return True
            if is_last:
                # Exact last-token match without trailing space is still "in progress".
                return True
            if found.parameter_arg is True and found.parent is not None:
                cursor = found.parent
            else:
                cursor = found

        # Every token resolved exactly; next-token suggestions should not be filtered.
        return False

    def _live_instance_names(self) -> list[str]:
        try:
            sync_filesystem_instances_to_db(app=self.app)
        except Exception:
            pass

        try:
            session: Session = self.app.session
            instances = session.query(Instance).order_by(Instance.name).all()
            return [instance.name for instance in instances]
        except Exception:
            return []


class AssetManagementScreen(ListScreenTemplate):

    def __init__(self):
        super().__init__(
            choice_dict={
                "Register a Function": PyFileTreeScreen,
                "Update a Function": None,
                "Delete a Function": None,
                "Create a Collection": None,
                "Delete a Collection": None,
                "Delete a Table": None,
                "Sample Table Schema": None,
                "Sample Table Data" "Exit": None,
            },
        )

    @on(ListView.Selected)
    def handle_api_response(self, event: ListView.Selected):
        value = event.item.label
        if value == "Register a Function":
            if Path.home() == Path.cwd():
                self.app.notify(
                    "❌ Cannot scan root directory! Please run `tdconsole` in a more specific directory to avoid scanning your entire home path.",
                    severity="error",
                )
            else:
                self.app.push_screen(PyFileTreeScreen())


class InstanceManagementScreen(ListScreenTemplate):
    def __init__(self):
        super().__init__(
            choice_dict={
                "Bind An Instance": partial(InstanceSelectionScreen, flow_mode="bind"),
                "Start an Instance": partial(
                    InstanceSelectionScreen, flow_mode="start"
                ),
                "Stop An Instance": partial(InstanceSelectionScreen, flow_mode="stop"),
                "Delete An Instance": partial(
                    InstanceSelectionScreen, flow_mode="delete"
                ),
            },
            header="Welcome to Tabsdata. Select an Option to get started below",
        )


class PortConfigScreen(Screen):
    """
    Screen that asks for:
      - Instance name (for new instances)
      - External port
      - Internal port

    Validation:
      * Port 1–65535
      * Port not in use by another running instance
      * Internal port must not equal external port
    """

    CSS = """
    * {
        height: auto;
    }
    Screen {
        layout: vertical;
    }

    #portscroll {
        height: 1fr;
        overflow-y: auto;
    }

    .input_container Input {
    width: auto;
    }

Checkbox:focus > .toggle--button {
    color: $accent;
}


    """

    def __init__(self, instance) -> None:
        super().__init__()
        if instance is None:
            raise TypeError("PortConfigScreen requires an Instance object")

        if instance.name == "_Create_Instance":
            self.placeholder = "tabsdata"
        else:
            self.placeholder = instance.name
        self.instance = instance

    def compose(self) -> ComposeResult:
        yield ExitBar()
        yield VerticalScroll(
            InstanceInfoPanel(),
            Vertical(
                Horizontal(
                    Label(
                        "Instance Name:",
                        id="title-instance",
                    ),
                    Input(
                        placeholder=self.placeholder,
                        validate_on=["submitted"],
                        disabled=True,
                        validators=[
                            input_validators.ValidInstanceName(self.app, self.instance)
                        ],
                        compact=True,
                        id="instance-input",
                        classes="inputs",
                    ),
                    Pretty("", id="instance-message"),
                ),
                id="instance-container",
                classes="input_container",
            ),
            Vertical(
                Horizontal(
                    Label("External port:", id="ext-label"),
                    Input(
                        placeholder=str(self.instance.arg_ext or ""),
                        restrict=r"\d*",
                        max_length=5,
                        compact=True,
                        validate_on=["submitted"],
                        validators=[
                            input_validators.ValidExtPort(self.app, self.instance)
                        ],
                        id="ext-input",
                        classes="inputs",
                    ),
                    Pretty("", id="ext-message"),
                ),
                id="ext-container",
                classes="input_container",
            ),
            Vertical(
                Horizontal(
                    Label("Internal port:", id="int-label"),
                    Input(
                        placeholder=str(self.instance.arg_int or ""),
                        validate_on=["submitted"],
                        restrict=r"\d*",
                        compact=True,
                        max_length=5,
                        validators=[
                            input_validators.ValidIntPort(self.app, self.instance)
                        ],
                        id="int-input",
                        classes="inputs",
                    ),
                    Pretty("", id="int-message"),
                ),
                id="int-container",
                classes="input_container",
            ),
            Vertical(
                Horizontal(
                    Label("Use HTTPS:", id="https-label"),
                    Checkbox(
                        value=getattr(self.instance, "use_https", False),
                        compact=True,
                        id="https-checkbox",
                        classes="inputs",
                    ),
                ),
                id="https-container",
                classes="input_container",
            ),
            Vertical(
                Button(
                    label="Submit",
                    id="submit-button",
                    classes="submit-button",
                ),
                id="submit-container",
                classes="button_container",
            ),
        )

        yield Footer()

    def set_visibility(self):
        input_containers = self.query(".input_container")
        instance_container = self.query_one("#instance-container")
        ext_container = self.query_one("#ext-container")
        int_container = self.query_one("#int-container")
        self.input_fields = [
            i for i in self.query("Input, Checkbox, Button") if i.disabled != True
        ]

        input_messages = self.query(".input_container Pretty")

        instance_input = self.query_one("#instance-input")
        ext_input = self.query_one("#ext-input")
        int_input = self.query_one("#int-input")

        for i in input_messages:
            i.display = False

        if self.instance.name == "_Create_Instance":
            self.set_focus(instance_input)
            instance_input.disabled = False
            return

        self.set_focus(ext_input)
        return

    def on_mount(self) -> None:
        self.set_visibility()

    def on_screen_resume(self, event) -> None:
        self.set_visibility()

    def on_key(self, event):
        key_mapping = {"up": -1, "down": 1}
        if self.screen.focused not in self.input_fields:
            return
        focused_index = self.input_fields.index(self.screen.focused)
        if event.key in key_mapping:
            next_index = (focused_index + key_mapping[event.key]) % len(
                self.input_fields
            )
            self.set_focus(self.input_fields[next_index])

    def validate_input(self, input: Input, value):
        if value == "":
            value = input.placeholder
        validation_result = input.validate(value)
        return validation_result

    @on(Input.Submitted, ".inputs")
    def handle_input_submission(self, event: Input.Submitted):
        value = event.value
        input_widget = event.input
        validation_result = self.validate_input(input_widget, value)

        if validation_result.is_valid == False:
            self.app.notify(
                f"❌ {validation_result.failure_descriptions}.",
                severity="error",
            )
            message = input_widget.parent.query_one("Pretty")
            message.update(validation_result.failure_descriptions)
            message.display = True
        else:
            message = input_widget.parent.query_one("Pretty")
            message.update("[Validation Passed]")
            message.display = True
            key_event = Key(key="down", character=None)
            self.on_key(key_event)
        return

    @on(Button.Pressed, "#submit-button")
    def handle_submission_request(self, event: Button.Pressed):
        fields = [i for i in self.query("Input") if len(i.validators) > 0]

        if self.instance.name != "_Create_Instance":
            fields = [i for i in fields if i.id != "instance-input"]

        validation_passed = True
        new = {}
        for i in fields:
            i: Input
            validation_result = self.validate_input(i, i.value)
            if validation_result.is_valid is False:
                self.app.notify(
                    f"❌ {validation_result.failure_descriptions}.",
                    severity="error",
                )
                message = i.parent.query_one("Pretty")
                message.update(validation_result.failure_descriptions)
                message.display = True
                validation_passed = False
            else:
                message = i.parent.query_one("Pretty")
                message.update("[Validation Passed]")
                message.display = True

        if validation_passed:
            values = [
                i.value if i.value != "" else i.placeholder
                for i in self.query("Input.inputs")
            ]
            values.append(self.query_one("Checkbox.inputs").value or False)
            new = {
                "name": values[0] != self.instance.name,
                "arg_ext": values[1] != self.instance.arg_ext,
                "arg_int": values[2] != self.instance.arg_int,
                "use_https": values[3] != self.instance.use_https,
            }
            self.instance.name = values[0]
            self.instance.arg_ext = values[1]
            self.instance.arg_int = values[2]
            self.instance.use_https = values[3]
            if self.app.flow_mode == "bind":
                self.app.push_screen(
                    BindAndStartInstance(current=self.instance, new=new)
                )
            elif self.app.flow_mode == "start":
                self.app.push_screen(StartInstance(current=self.instance, new=new))


@dataclass
class TaskSpec:
    description: str
    func: Callable[[str | None], Awaitable[None]]
    background: bool = False


class TaskRow(Horizontal):
    def __init__(self, description: str, task_id: str) -> None:
        super().__init__(id=task_id, classes="task-row")
        self.description = description

    def compose(self) -> ComposeResult:
        yield SpinnerWidget("dots", id=f"{self.id}-spinner", classes="task-spinner")
        yield Label(self.description, id=f"{self.id}-label", classes="task-label")

    def set_running(self) -> None:
        self.query_one(f"#{self.id}-spinner").display = True
        self.query_one(f"#{self.id}-label", Label).update(self.description)

    def set_done(self, exit_code: Optional[int] = None) -> None:
        try:
            self.query_one(f"#{self.id}-spinner").display = False
            if exit_code == 0 or exit_code is None:
                self.query_one(f"#{self.id}-label", Label).update(
                    f"✅ {self.description}"
                )
            else:
                self.query_one(f"#{self.id}-label", Label).update(
                    f"❌ {self.description}"
                )
        except:
            pass


class SequentialTasksScreenTemplate(Screen):
    BINDINGS = [
        ("enter", "press_close", "Done"),
    ]

    CSS = """
        * {
            height: auto;
        }
        #tasks-header { padding: 1 2; text-style: bold; }
        .task-row { height: 1; content-align: left middle; }
        .task-spinner { width: 3; }
        .task-label { padding-left: 1; }
        #task-log {
            padding: 1 2;
            border: round $accent;
            overflow-y: auto;
            overflow-x: auto;
            height: 20;
            width: 80%;
        }
        #task-box {align: center top;}
        VerticalScroll { height: 1fr; overflow-y: auto; }
    """

    COLOR_PALETTE = [
        "deep_sky_blue1",
        "spring_green2",
        "yellow1",
        "magenta",
        "cyan",
        "orchid",
        "orange1",
        "plum1",
    ]

    def __init__(self, tasks: List[TaskSpec] | None = None) -> None:
        super().__init__()
        self.tasks = tasks or []
        self.task_rows: List[TaskRow] = []
        self.log_widget: RichLog | None = None
        self.task_colors = {
            task.description: random.choice(self.COLOR_PALETTE) for task in self.tasks
        }

        # fail-fast state
        self.failed: bool = False
        self._background_tasks: list[asyncio.Task] = []

    def compose(self) -> ComposeResult:
        for index, task in enumerate(self.tasks):
            row = TaskRow(task.description, task_id=f"task-{index}")
            self.task_rows.append(row)

        yield ExitBar()
        yield VerticalScroll(
            Vertical(
                Label("Running setup tasks...", id="tasks-header"),
                *self.task_rows,
                Static(""),
                Container(
                    RichLog(
                        id="task-log",
                        auto_scroll=False,
                        max_lines=100,
                        markup=True,
                        wrap=False,
                    ),
                    id="task-box",
                ),
                Static(""),
                Footer(),
            ),
        )

    def conclude_tasks(self) -> None:
        self.query_one(VerticalScroll).scroll_end(animate=False)

    async def on_mount(self) -> None:
        self.log_widget = self.query_one("#task-log", RichLog)
        self.log_line(None, "Starting setup tasks…")
        asyncio.create_task(self.run_tasks())

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "close-btn":
            self.app.push_screen(HomeTabbedScreen())

    def log_line(self, task: str | None, msg: str) -> None:
        if task:
            color = self.task_colors.get(task, "white")
            line = f"[{color}][{task}]:[/] {msg}"
        else:
            line = msg

        if self.log_widget:
            self.log_widget.write(line)

    async def run_logged_subprocess(
        self,
        label: str | None,
        *args: str,
    ) -> int:
        """Run a subprocess, stream its output into the log, and return exit code."""
        self.log_line(label, f"Running: {' '.join(args)}")

        process = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )

        while True:
            line = await process.stdout.readline()
            if not line:
                break
            text = line.decode().rstrip("\n")
            self.log_line(label, text)

        code = await process.wait()
        self.log_line(label, f"Exited with code {code}")
        return code

    async def run_single_task(self, idx: int, task: TaskSpec) -> int | None:
        """
        Run a single task and return its exit code.
        Success = 0 or None.
        Failure = any other int.
        """
        row = self.task_rows[idx]
        row.set_running()
        self.log_line(task.description, "Starting")
        code: int | None = None

        try:
            # allow task.func to return either None or an int
            result = await task.func(task.description)
            code = result if isinstance(result, int) else None
            self.log_line(task.description, "Finished")
        except Exception as e:
            self.log_line(task.description, f"Error: {e!r}")
            code = 1  # treat exception as failure
        finally:
            row.set_done(code)

        return code

    async def abort_all_tasks(self) -> None:
        """Fail-fast: cancel all background tasks and mark remaining rows as failed."""
        if self.failed:
            return  # idempotent

        self.failed = True
        self.log_line(None, "❌ Aborting remaining tasks due to failure.")

        # Cancel background tasks
        for task in self._background_tasks:
            if not task.done():
                task.cancel()

        # Mark any still-running rows as failed
        for row in self.task_rows:
            spinner = row.query_one(f"#{row.id}-spinner")
            if getattr(spinner, "display", False):
                # If spinner is still visible, treat it as failed
                row.set_done(exit_code=1)

        self.conclude_tasks()

    async def _background_wrapper(self, idx: int, task: TaskSpec) -> None:
        """Wrapper for background tasks so they can trigger fail-fast."""
        try:
            code = await self.run_single_task(idx, task)
        except asyncio.CancelledError:
            self.log_line(task.description, "Cancelled")
            return

        if code not in (0, None):
            await self.abort_all_tasks()

    def action_press_close(self) -> None:
        # Only act if the button exists
        try:
            btn = self.query_one("#close-btn", Button)
        except Exception:
            return
        btn.press()

    async def run_tasks(self) -> None:
        try:
            # Start background tasks first
            self._background_tasks = []
            for i, t in enumerate(self.tasks):
                if t.background:
                    self.log_line(t.description, "Scheduling background task")
                    self._background_tasks.append(
                        asyncio.create_task(self._background_wrapper(i, t))
                    )

            # Run foreground tasks sequentially
            for i, t in enumerate(self.tasks):
                if self.failed:
                    break  # already failed; stop starting new tasks

                if not t.background:
                    code = await self.run_single_task(i, t)
                    if code not in (0, None):
                        await self.abort_all_tasks()
                        break

            # Wait for background tasks to finish / cancel
            if self._background_tasks:
                await asyncio.gather(*self._background_tasks, return_exceptions=True)

            if self.failed:
                self.log_line(None, "⚠️ Tasks aborted due to failure.")
            else:
                self.log_line(None, "🎉 All tasks complete.")
                self.conclude_tasks()
        except Exception as exc:
            self.failed = True
            self.log_line(None, f"❌ Task runner error: {exc!r}")
        finally:
            # Always show “Done” button
            try:
                footer = self.query_one(Footer)
                if not self.query("#close-btn"):
                    await self.mount(Button("Done", id="close-btn"), before=footer)
                button = self.query_one("#close-btn", Button)
                button.focus()
            except Exception:
                pass


class BindAndStartInstance(SequentialTasksScreenTemplate):
    def __init__(self, current, new) -> None:
        self.instance = current
        self.new = new
        self.instance.working = True

        tasks = [
            TaskSpec(
                "Preparing Instance",
                partial(instance_tasks.prepare_instance, self, self.instance),
            ),
            TaskSpec(
                "Checking Instance Version",
                partial(instance_tasks.upgrade_instance, self, self.instance),
            ),
            TaskSpec(
                "Binding Ports",
                partial(instance_tasks.bind_ports, self, self.instance),
            ),
            TaskSpec(
                "Connecting to Tabsdata instance",
                partial(instance_tasks.connect_tabsdata, self, self.instance),
            ),
            TaskSpec(
                "Checking Server Status",
                partial(instance_tasks.run_tdserver_status, self, self.instance),
            ),
            TaskSpec(
                "Logging you In",
                partial(instance_tasks.tabsdata_login, self, self.instance),
            ),
        ]

        super().__init__(tasks)

    def conclude_tasks(self, status=None):
        super().conclude_tasks()
        self.instance.working = True
        merged_instance = self.app.session.merge(self.instance)
        self.app.session.commit()
        self.app.working_instance = merged_instance


class StartInstance(SequentialTasksScreenTemplate):
    def __init__(self, current, new) -> None:
        self.instance = current
        self.new = new
        self.instance.working = True

        tasks = [
            TaskSpec(
                "Preparing Instance",
                partial(instance_tasks.prepare_instance, self, self.instance),
            ),
            TaskSpec(
                "Binding Ports",
                partial(instance_tasks.bind_ports, self, self.instance),
            ),
            TaskSpec(
                "Connecting to Tabsdata instance",
                partial(instance_tasks.connect_tabsdata, self, self.instance),
            ),
            TaskSpec(
                "Checking Server Status",
                partial(instance_tasks.run_tdserver_status, self, self.instance),
            ),
        ]

        super().__init__(tasks)


class StopInstance(SequentialTasksScreenTemplate):
    def __init__(self, current, new) -> None:
        self.instance = current
        self.new = new
        self.instance.working = False

        tasks = [
            TaskSpec(
                "Preparing Instance",
                partial(instance_tasks.prepare_instance, self, self.instance),
            ),
            TaskSpec(
                "Stopping Tabsdata instance",
                partial(instance_tasks.stop_instance, self, self.instance),
            ),
            TaskSpec(
                "Checking Server Status",
                partial(instance_tasks.run_tdserver_status, self, self.instance),
            ),
        ]

        super().__init__(tasks)

    def conclude_tasks(self):
        super().conclude_tasks()
        self.instance.working = False
        self.app.session.merge(self.instance)
        self.app.session.commit()


class DeleteInstance(SequentialTasksScreenTemplate):
    def __init__(self, current, new) -> None:
        self.instance = current
        self.new = new
        self.instance.working = False

        tasks = [
            TaskSpec(
                "Preparing Instance",
                partial(instance_tasks.prepare_instance, self, self.instance),
            ),
            TaskSpec(
                "Deleting Tabsdata instance",
                partial(instance_tasks.delete_instance, self, self.instance),
            ),
            TaskSpec(
                "Checking Server Status",
                partial(instance_tasks.run_tdserver_status, self, self.instance),
            ),
        ]

        super().__init__(tasks)

    def conclude_tasks(self):
        super().conclude_tasks()
        self.instance.working = False
        self.app.session.merge(self.instance)
        self.app.session.commit()


class PyOnlyDirectoryTree(DirectoryTree):
    """DirectoryTree that:
    - only shows .py files (but keeps directories)
    - only shows .py files that contain td publisher/subscriber/transformer
    - only shows directories that (recursively) contain such .py files
    - limits recursive search to `auto_expand_depth` levels
    - auto-expands the first `auto_expand_depth` levels on mount
    """

    DEFAULT_CSS = """
    DirectoryTree {
        
        & > .directory-tree--folder {
            text-style: bold;
            color: green;
        }

        & > .directory-tree--extension {
            text-style: italic;
        }
        
        & > .directory-tree--file {
            text-style: italic;
            color: green;
        }

        & > .directory-tree--hidden {
            text-style: dim;
        }

        &:ansi {
        
            & > .tree--guides {
               color: transparent;              
            }
        
            & > .directory-tree--folder {
                text-style: bold;
            }

            & > .directory-tree--extension {
                text-style: italic;
            }

            & > .directory-tree--hidden {
                color: ansi_default;
                text-style: dim;
            }
        }

    }
    """

    def __init__(
        self,
        path: str | Path,
        *,
        auto_expand_depth: int = 5,  # <- 3 levels on first mount
        **kwargs,
    ) -> None:
        self.auto_expand_depth = auto_expand_depth
        super().__init__(path, **kwargs)

    # ---------- filtering ----------

    def filter_paths(self, paths: Iterable[Path]) -> Iterable[Path]:
        """Keep only:
        - .py files that match _file_is_tabsdata_function
        - directories that (within depth) contain at least one such file
        """
        result: list[Path] = []
        for p in paths:
            if p.is_file() and p.suffix == ".py":
                if self._file_is_tabsdata_function(p):
                    result.append(p)
            elif p.is_dir():
                if self._dir_has_py(p, depth=0, max_depth=self.auto_expand_depth):
                    result.append(p)

        return result

    def _file_is_tabsdata_function(self, path: Path) -> bool:
        """Return True if the .py file contains a td.publisher/subscriber/transformer-decorated function."""
        if path.suffix != ".py":
            return False

        try:
            source = path.read_text()
        except OSError:
            return False

        try:
            tree = ast.parse(source, filename=str(path))
        except SyntaxError:
            return False

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):  # or ast.AsyncFunctionDef
                for deco in node.decorator_list:
                    func = deco.func if isinstance(deco, ast.Call) else deco
                    if isinstance(func, ast.Attribute) and isinstance(
                        func.value, ast.Name
                    ):
                        if func.value.id == "td" and func.attr in {
                            "publisher",
                            "subscriber",
                            "transformer",
                        }:
                            return True
        return False

    def _dir_has_py(self, path: Path, depth: int = 0, max_depth: int = 5) -> bool:
        """Return True if directory contains a matching .py file within max_depth levels."""
        if depth > max_depth:
            return False

        try:
            for entry in path.iterdir():
                if entry.is_file() and entry.suffix == ".py":
                    if self._file_is_tabsdata_function(entry):
                        return True
                elif entry.is_dir():
                    if self._dir_has_py(entry, depth + 1, max_depth):
                        return True
        except PermissionError:
            return False

        return False

    # ---------- auto expand on mount ----------

    async def on_mount(self) -> None:
        """When the tree is first mounted, auto-expand N levels."""
        await self._expand_to_depth(
            self.root, depth=0, max_depth=self.auto_expand_depth
        )

    async def _expand_to_depth(
        self, node: TreeNode, depth: int, max_depth: int
    ) -> None:
        """Recursively expand nodes up to `max_depth` levels deep."""
        if depth >= max_depth:
            return

        await self._add_to_load_queue(node)

        # Recurse into child directories only
        for child in node.children:
            data = child.data
            if data is None:
                continue

            path = getattr(data, "path", None)
            if isinstance(path, Path) and path.is_dir():
                await self._expand_to_depth(child, depth + 1, max_depth)

    @on(DirectoryTree.NodeExpanded)
    def set_file_color(self, event: DirectoryTree.NodeExpanded):
        for i in event.node.children:
            if i.data.path.is_file():
                i.label.stylize("green")
        self.refresh()


class PyFileTreeScreen(Screen):
    """ListScreenTemplate variant that shows a DirectoryTree of .py files."""

    def __init__(
        self, id=None, header="Select a Python file: ", root: str | Path = "."
    ):
        # Reuse ListScreenTemplate init, but choices are irrelevant for the tree
        super().__init__()
        self.root = Path(root)
        self.initial_root = Path(root)
        self.limit_root = Path.cwd()
        self.header = header

    def compose(self) -> ComposeResult:
        """Same layout as ListScreenTemplate, but with a DirectoryTree instead of ListView."""
        yield ExitBar()
        with VerticalScroll():
            if self.header is not None:
                yield Label(self.header, id="listHeader")
            yield Horizontal(
                Button("Up", id="tree-up-btn"),
                Button("Home", id="tree-home-btn"),
                Button("CWD", id="tree-cwd-btn"),
                Input(placeholder="Paste path…", id="tree-path-input"),
                Button("Go", id="tree-go-btn"),
                id="tree-controls",
            )

            # Reuse your existing "current instance" widget
            yield CurrentInstanceWidget(self.app.working_instance)

            with Container(id="tree-container"):
                # Swap ListView for a DirectoryTree rooted at CWD, filtered to .py files
                self.dirtree = PyOnlyDirectoryTree(
                    self.root,
                    id="py-directory-tree",
                )
                self.dirtree.show_guides = True
                self.dirtree.guide_depth = 2
                self.dirtree.show_root = True
                yield self.dirtree

            yield Footer()

    def on_show(self) -> None:
        """Focus the directory tree when the screen is shown."""
        self.set_focus(self.dirtree)

    @on(Button.Pressed, "#tree-up-btn")
    async def on_tree_up(self, event: Button.Pressed) -> None:
        new_root = self.root.parent if self.root.parent != self.root else self.root
        await self._set_tree_root(new_root)

    @on(Button.Pressed, "#tree-home-btn")
    async def on_tree_home(self, event: Button.Pressed) -> None:
        await self._set_tree_root(Path.home())

    @on(Button.Pressed, "#tree-cwd-btn")
    async def on_tree_cwd(self, event: Button.Pressed) -> None:
        await self._set_tree_root(Path.cwd())

    @on(Button.Pressed, "#tree-go-btn")
    async def on_tree_go(self, event: Button.Pressed) -> None:
        raw = self.query_one("#tree-path-input", Input).value.strip()
        if not raw:
            return
        path = Path(raw).expanduser()
        if not path.is_absolute():
            path = (self.root / path).resolve()
        if not path.exists() or not path.is_dir():
            self.app.notify("Path not found or not a directory.", severity="error")
            return
        await self._set_tree_root(path)

    async def _set_tree_root(self, new_root: Path) -> None:
        new_root = new_root.resolve()
        limit_root = self.limit_root.resolve()
        if new_root == Path("/"):
            self.app.notify("Root navigation disabled.", severity="warning")
            return
        if new_root != limit_root and limit_root not in new_root.parents:
            self.app.notify(
                f"Navigation restricted to {limit_root}", severity="warning"
            )
            return
        if new_root == self.root:
            return
        self.root = new_root
        try:
            await self.dirtree.remove()
        except Exception:
            pass
        container = self.query_one("#tree-container", Container)
        self.dirtree = PyOnlyDirectoryTree(
            self.root,
            id="py-directory-tree",
        )
        self.dirtree.show_guides = True
        self.dirtree.guide_depth = 2
        self.dirtree.show_root = True
        await container.mount(self.dirtree)
        self.set_focus(self.dirtree)

    def on_directory_tree_file_selected(
        self, event: DirectoryTree.FileSelected
    ) -> None:
        """Handle selection of a file in the directory tree."""
        selected_path: Path = event.path
        self.app.push_screen(AssetManagementScreen())
