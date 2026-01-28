from __future__ import annotations

import ast
import asyncio
import asyncio.subprocess
import random
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
from textual.containers import Center, Container, Horizontal, Vertical, VerticalScroll
from textual.events import Key, ScreenResume
from textual.reactive import reactive
from textual.screen import ModalScreen, Screen
from textual.widgets import (
    Button,
    Checkbox,
    DirectoryTree,
    Footer,
    Input,
    Label,
    ListItem,
    ListView,
    Pretty,
    RichLog,
    Static,
)
from textual.widgets._tree import TreeNode

from tdconsole.core import input_validators, instance_tasks, tabsdata_api
from tdconsole.core.find_instances import (
    instance_name_to_instance,
    sync_filesystem_instances_to_db,
)
from tdconsole.core.models import Instance
from tdconsole.textual_assets.spinners import SpinnerWidget


class ExitBar(Container):
    DEFAULT_CSS = """
    ExitBar {
        width: 3;
        min-width: 3;
        height: 1;
    }
    #exit-btn {
        color: white;
        background: transparent;
        width: 3;
        min-width: 3;
        height: 1;
        padding: 0 1;
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
        width: 3;
        min-width: 3;
        height: 1;
    }
    #refresh-btn {
        color: white;
        background: transparent;
        width: 3;
        min-width: 3;
        height: 1;
        padding: 0 1;
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
            if isinstance(self.collection, Function):
                options = ["Delete Function", "Trigger Function"]
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
        self.selected_function = None
        self.function_list = []
        self.selected_function = None
        self.table_list = []
        self.selected_table = None
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
        self.selected_collection = None
        self.selected_function = None
        self.selected_table = None
        self.refresh(recompose=True)

    def recompile_td_data(self):
        self.instance = self.resolve_working_instance()
        self.tabsdata_server = self.app.tabsdata_server
        self.tabsdata_server: TabsdataServer
        try:
            self.collection_list = self.tabsdata_server.list_collections()

            if (
                self.selected_collection in self.collection_list
                and self.tabsdata_server
            ):
                self.function_list = self.tabsdata_server.list_functions(
                    self.selected_collection.name
                )
                self.table_list = self.tabsdata_server.list_tables(
                    self.selected_collection.name
                )
            else:
                self.function_list = []
                self.table_list = []
        except:
            self.function_list = []
            self.table_list = []

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

        return result

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
        server: TabsdataServer = self.app.tabsdata_server
        collections = server.list_collections()
        collections.append("Create a Collection")
        choiceLabels = [
            LabelItem(getattr(i, "name", "Create a Collection"), i) for i in collections
        ]
        self.list = ListView(*choiceLabels)
        return self.list

    @on(ListView.Selected)
    def handle_collection_selected(self, event: ListView.Selected):
        event.stop()
        collection = event.item.label
        self.parent.selected_collection = collection
        self.parent.recompile_td_data()
        widgets_to_refresh = self.screen.query(".collection_dependent")
        for i in widgets_to_refresh:
            i.refresh(recompose=True)


class CurrentFunctionsWidget(CurrentStateWidgetTemplate):

    def generate_internals(self, functions=None):
        """Converts List to a ListView"""
        server: TabsdataServer = self.app.tabsdata_server
        selected_collection = self.parent.selected_collection
        try:
            functions = server.list_functions(selected_collection.name)
        except:
            functions = []

        functions.append("Create a Function")
        choiceLabels = [
            LabelItem(getattr(i, "name", "Create a Function"), i) for i in functions
        ]
        self.list = ListView(*choiceLabels)
        return self.list

    @on(ListView.Selected)
    def handle_function_selected(self, event: ListView.Selected):
        event.stop()


class CurrentTablesWidget(CurrentStateWidgetTemplate):
    DEFAULT_CSS = """
    CurrentTablesWidget ListItem.--highlight {
        background: #0f766e;
        color: white;
    }
    """

    def generate_internals(self, collections=None):
        """Converts List to a ListView"""
        server: TabsdataServer = self.app.tabsdata_server
        selected_collection = self.parent.selected_collection

        try:
            tables = server.list_tables(selected_collection.name)
        except:
            tables = []

        tables.append("Create a Table")
        choiceLabels = [
            LabelItem(getattr(i, "name", "Create a Function"), i) for i in tables
        ]
        self.list = ListView(*choiceLabels)
        return self.list

    @on(ListView.Selected)
    def handle_table_selected(self, event: ListView.Selected):
        event.stop()


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
            yield Horizontal(ExitBar(), Label("   "), RefreshBar())
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
        #task-log { padding: 1 2; border: round $accent; overflow-y: auto; height: 20; width: 80%;}
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
                        id="task-log", auto_scroll=False, max_lines=100, markup=True
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
            self.app.push_screen(MainScreen())

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

        # Show “Done” button either way
        footer = self.query_one(Footer)
        await self.mount(Button("Done", id="close-btn"), before=footer)
        button = self.query_one("#close-btn")
        button.focus()


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
        self.header = header

    def compose(self) -> ComposeResult:
        """Same layout as ListScreenTemplate, but with a DirectoryTree instead of ListView."""
        yield ExitBar()
        with VerticalScroll():
            if self.header is not None:
                yield Label(self.header, id="listHeader")

            # Reuse your existing "current instance" widget
            yield CurrentInstanceWidget(self.app.working_instance)

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

    def on_directory_tree_file_selected(
        self, event: DirectoryTree.FileSelected
    ) -> None:
        """Handle selection of a file in the directory tree."""
        selected_path: Path = event.path
        self.app.push_screen(AssetManagementScreen())
