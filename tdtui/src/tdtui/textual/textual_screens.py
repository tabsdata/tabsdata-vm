from textual.app import App, ComposeResult
from textual.screen import Screen
from textual.widgets import ListView, ListItem, Label, Static
from pathlib import Path
from tdtui.textual.api_processor import process_response
from tdtui.core.find_instances import main as find_instances
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

from tdtui.textual.task_screen import TaskScreen as InstanceStartup

from __future__ import annotations

from typing import Optional, Dict, Any, List

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Input, Label, Static, Footer
from textual.containers import Vertical, VerticalScroll
from rich.text import Text

from tdtui.core.find_instances import main as find_instances
import logging
from pathlib import Path
from textual import events

logging.basicConfig(
    filename=Path.home() / "tabsdata-vm" / "log.log",
    level=logging.INFO,
    format="%(message)s",
)


class InstanceWidget(Static):
    """Rich panel showing the current working instance."""

    def __init__(self, inst: Optional[str] = None, inst_name=None):
        super().__init__()
        self.inst = inst
        self.inst_name = inst_name

    def _make_instance_panel(self) -> Panel:

        inst = self.inst
        inst_name = self.inst_name
        # inst --> inst_name --> app attr

        if inst is not None and type(inst) == dict:
            pass
        elif inst_name is not None:
            inst = [i for i in find_instances() if i["name"] == inst_name][0]
        elif hasattr(self.app, "instance_name"):
            inst = [i for i in find_instances() if i["name"] == self.app.instance_name][
                0
            ]

        if inst is None:
            status = None
        else:
            name = inst.get("name", None)
            status = inst.get("status", None)
            cfg_ext = inst.get("cfg_ext", None)
            cfg_int = inst.get("cfg_int", None)
            arg_ext = inst.get("arg_ext", None)
            arg_int = inst.get("arg_int", None)

        if status == "Running":
            status_color = "#22c55e"
            status_line = f"{name}  ● Running"
            line1 = f"running on → ext: {arg_ext}"
            line2 = f"running on → int: {arg_int}"
            self.app.port_selection["status"] = "Running"
        elif status is None:
            status_color = "#e4e4e6"
            status_line = f"○ No Instance Selected"
            line1 = f"No External Running Port"
            line2 = f"No Internal Running Port"
        else:
            status_color = "#ef4444"
            status_line = f"{name}  ○ Not running"
            line1 = f"configured on → ext: {cfg_ext}"
            line2 = f"configured on → int: {cfg_int}"

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


class CurrentInstanceWidget(InstanceWidget):
    def render(self) -> RenderableType:
        # inner instance panel
        instance_panel = self._make_instance_panel()

        header = Align.center(Text("Current Working Instance:", style="bold #22c55e"))

        inner = Group(
            header,  # spacer
            Align.center(instance_panel),
        )

        outer = Panel(
            inner,
            border_style="#0f766e",
            expand=False,
        )
        return Align.center(outer)


class LabelItem(ListItem):

    def __init__(self, label: str, override_label=None) -> None:
        super().__init__()
        if type(label) == str:
            self.front = Label(label)
        else:
            self.front = label
        self.label = label
        if override_label is not None:
            self.label = override_label

    def compose(self) -> ComposeResult:
        yield self.front


class ScreenTemplate(Screen):
    def __init__(self, choices=None, id=None, header="Select an Option: "):
        super().__init__()
        self.choices = choices
        self.id = id
        self.header = header

    def compose(self) -> ComposeResult:
        logging.info(self.app.port_selection)
        instance = self.app.port_selection.get("name")
        logging.info(f"instance chosen is {instance} at type {type(instance)}")
        with VerticalScroll():
            if self.header is not None:
                yield Label(self.header, id="listHeader")
            yield CurrentInstanceWidget(inst_name=instance)
            choiceLabels = [LabelItem(i) for i in self.choices]
            self.list = ListView(*choiceLabels)
            yield self.list
            yield Footer()

    def on_show(self) -> None:
        # called again when you push this screen a
        #  second time (if reused)
        self.set_focus(self.list)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        selected = event.item.label
        logging.info(type(self.screen).__name__)
        process_response(self, selected)  # push instance


class OverflowScreen(Screen):

    CSS = """
    Screen {
        background: $background;
        color: black;
    }

    VerticalScroll {
        width: 1fr;
    }

    Static {
        margin: 1 2;
        background: green 80%;
        border: green wide;
        color: white 90%;
        height: auto;
    }

    #right {
        overflow-y: hidden;
    }
    """

    def compose(self) -> ComposeResult:
        TEXT = """I must not fear.
        Fear is the mind-killer.
        Fear is the little-death that brings total obliteration.
        I will face my fear.
        I will permit it to pass over me and through me.
        And when it has gone past, I will turn the inner eye to see its path.
        Where the fear has gone there will be nothing. Only I will remain."""
        yield Horizontal(
            VerticalScroll(
                Static(TEXT),
                Static(TEXT),
                Static(TEXT),
                id="left",
            ),
            VerticalScroll(
                Static(TEXT),
                Static(TEXT),
                Static(TEXT),
                id="right",
            ),
        )


class InstanceSelectionScreen(Screen):
    def __init__(self, id=None):
        super().__init__()

    def compose(self) -> ComposeResult:
        instances = find_instances()
        instanceWidgets = [
            LabelItem(label=InstanceWidget(i), override_label=i.get("name"))
            for i in instances
        ]
        with VerticalScroll():
            # self.list = ListView(*[LabelItem('a'), LabelItem('b')])
            self.list = ListView(*instanceWidgets)
            yield self.list
        yield Footer()

    def on_show(self) -> None:
        # called again when you push this screen a
        #  second time (if reused)
        self.set_focus(self.list)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        selected = event.item.label
        logging.info(type(self.screen).__name__)
        process_response(self, selected)  # push instance


class PortConfigScreen(Screen):
    """
    Screen that asks for external and internal ports with validation:

      * Port must be 1–65535
      * Port must not be in use by another running instance
      * External and internal ports must not be equal

    On success, stores the results on the app as:
      app.selected_instance_name
      app.selected_external_port
      app.selected_internal_port
      app.port_selection (dict)
    """

    CSS = """
    Screen {
        layout: vertical;
    }

    #portscroll {
        height: 1fr;
        overflow-y: auto;
    }
    """

    def __init__(self, instance_name: Optional[str] = None) -> None:
        super().__init__()
        if instance_name is not None:
            self.instance_name = instance_name
        else:
            self.instance_name = self.app.instance_name
        self.selected_instance_name: Optional[str] = instance_name

        instances = [i for i in find_instances() if i["name"] == self.instance_name]
        if len(instances) > 0:
            instances = instances[0]
            self.external_port = instances["arg_ext"].split(":")[-1]
            self.internal_port = instances["arg_int"].split(":")[-1]
        else:
            self.external_port = None
            self.internal_port = None

    def compose(self) -> ComposeResult:
        logging.info(self.virtual_size)

        # import here to avoid circulars if needed
        from tdtui.textual.textual_simple import CurrentInstanceWidget

        yield VerticalScroll(
            CurrentInstanceWidget(self.instance_name),
            Label(
                "What Would Like to call your Tabsdata Instance:",
                id="title-instance",
            ),
            Input(placeholder="tabsdata", id="instance-input"),
            Label("", id="instance-error"),
            Label("", id="instance-confirm"),
            Label("Configure Tabsdata ports", id="title"),
            Label("External port:", id="ext-label"),
            Input(placeholder=self.external_port, id="ext-input"),
            Label("", id="ext-error"),
            Label("", id="ext-confirm"),
            Label("Internal port:", id="int-label"),
            Input(placeholder=self.internal_port, id="int-input"),
            Label("", id="int-error"),
            Label("", id="int-confirm"),
            Static(""),
        )

        yield Footer()

    def set_visibility(self):
        if self.instance_name is not None:
            self.selected_instance_name = self.instance_name
            # Instance already known: hide instance name input, start on ext port
            self.query_one("#instance-confirm", Label).display = False
            self.query_one("#instance-error", Label).display = False
            self.query_one("#instance-input", Input).display = False
            self.query_one("#title-instance", Label).display = False
            self.set_focus(self.query_one("#ext-input", Input))
        else:
            # No instance yet: start by asking for name
            self.query_one("#ext-confirm", Label).display = False
            self.query_one("#ext-error", Label).display = False
            self.query_one("#ext-input", Input).display = False
            self.query_one("#ext-label", Label).display = False
            self.query_one("#title", Label).display = False
            self.set_focus(self.query_one("#instance-input", Input))

        self.query_one("#int-label", Label).display = False
        self.query_one("#int-input", Input).display = False
        self.query_one("#int-error", Label).display = False
        self.query_one("#int-confirm", Label).display = False

    def on_mount(self) -> None:
        logging.info(self.virtual_size)
        self.set_visibility()

    def on_screen_resume(self, event) -> None:
        self.set_visibility()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        logging.info(self.virtual_size)

        if event.input.id == "ext-input":
            self._handle_external_submitted(event.input)
        elif event.input.id == "int-input":
            self._handle_internal_submitted(event.input)
        elif event.input.id == "instance-input":
            self._handle_instance_name_submitted(event.input)

    # ---------------------------
    # External port flow
    # ---------------------------

    def _handle_external_submitted(self, ext_input: Input) -> None:
        ext_error = self.query_one("#ext-error", Label)
        ext_confirm = self.query_one("#ext-confirm", Label)

        ext_error.update("")
        ext_confirm.update("")

        value = ext_input.value.strip()
        if value == "":
            value = self.external_port

        if not validate_port(value):
            ext_error.update("That is not a valid port number. Please enter 1–65535.")
            self.set_focus(ext_input)
            ext_input.clear()
            return

        port = int(value)
        in_use_by = port_in_use(port, current_instance_name=self.instance_name)

        if in_use_by is not None:
            ext_error.update(
                f"Port {port} is already in use by instance '{in_use_by}'. "
                "Please choose a different port."
            )
            self.set_focus(ext_input)
            ext_input.clear()
            return

        # Valid and free
        self.external_port = port
        ext_confirm.update(
            Text(f"Selected external port: {port}", style="bold #22c55e")
        )

        # Reveal internal port input and focus it
        self.query_one("#int-label", Label).display = True
        self.query_one("#int-input", Input).display = True
        self.query_one("#int-error", Label).display = True
        self.query_one("#int-confirm", Label).display = True

        self.set_focus(self.query_one("#int-input", Input))

    # ---------------------------
    # Instance Name flow
    # ---------------------------

    def _handle_instance_name_submitted(self, instance_input: Input) -> None:
        instance_error = self.query_one("#instance-error", Label)
        instance_confirm = self.query_one("#instance-confirm", Label)

        instance_error.update("")
        instance_confirm.update("")

        value = instance_input.value.strip()
        if value == "":
            value = "tabsdata"

        if name_in_use(value):
            instance_error.update("That Name is Already in Use. Please Try Another:")
            self.set_focus(instance_input)
            instance_input.clear()
            return

        # Valid and free
        self.selected_instance_name = value
        instance_confirm.update(
            Text(
                f"Defined an Instance with the following Name: {value}",
                style="bold #22c55e",
            )
        )

        # Reveal external port input and focus it
        self.query_one("#ext-label", Label).display = True
        self.query_one("#ext-input", Input).display = True
        self.query_one("#ext-error", Label).display = True
        self.query_one("#ext-confirm", Label).display = True

        self.set_focus(self.query_one("#ext-input", Input))

    # ---------------------------
    # Internal port flow
    # ---------------------------

    def _handle_internal_submitted(self, int_input: Input) -> None:
        from tdtui.textual.api_processor import process_response

        int_error = self.query_one("#int-error", Label)
        int_confirm = self.query_one("#int-confirm", Label)

        int_error.update("")
        int_confirm.update("")

        value = int_input.value.strip()
        if value == "":
            value = self.internal_port

        if not validate_port(value):
            int_error.update("That is not a valid port number. Please enter 1–65535.")
            self.set_focus(int_input)
            int_input.clear()
            return

        port = int(value)

        # Must not match external
        if self.external_port is not None and port == self.external_port:
            int_error.update(
                "Internal port must not be the same as external port. "
                "Please choose another port."
            )
            self.set_focus(int_input)
            int_input.clear()
            return

        in_use_by = port_in_use(port, current_instance_name=self.instance_name)

        if in_use_by is not None:
            int_error.update(
                f"Port {port} is already in use by instance '{in_use_by}'. "
                "Please choose a different port."
            )
            self.set_focus(int_input)
            int_input.clear()
            return

        # Valid, distinct, and free
        self.internal_port = port
        int_confirm.update(
            Text(f"Selected internal port: {port}", style="bold #22c55e")
        )

        # Store result on the app
        app = self.app
        app.selected_instance_name = self.selected_instance_name
        app.selected_external_port = self.external_port
        app.selected_internal_port = self.internal_port
        app.port_selection = {
            "name": self.selected_instance_name,
            "external_port": self.external_port,
            "internal_port": self.internal_port,
        }
        logging.info(app.port_selection)
        process_response(self)
