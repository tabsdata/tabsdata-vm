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
    filename=Path(__file__).resolve().parent / "log.log",
    level=logging.INFO,
    format="%(message)s",
)


def validate_port(port_str: str) -> bool:
    """Return True if port_str is an integer between 1 and 65535."""
    port_str = str(port_str)
    if not port_str.isdigit():
        return False
    port = int(port_str)
    return 1 <= port <= 65535


def get_running_ports() -> List[Dict[str, Any]]:
    """
    Python equivalent of get_running_ports() from bash.

    Returns a list of dicts for running instances, each with:
      name, status, external_port, internal_port
    """
    instances = find_instances()
    running = []

    for inst in instances:
        status = inst.get("status")
        if status != "Running":
            continue

        name = inst.get("name", "?")
        arg_ext = inst.get("arg_ext") or ""
        arg_int = inst.get("arg_int") or ""

        # Extract port from "host:port" or use as-is if just "port"
        ext_port_str = arg_ext.split(":")[-1] if arg_ext else ""
        int_port_str = arg_int.split(":")[-1] if arg_int else ""

        # Only keep if they look like valid ports; otherwise ignore
        ext_port = int(ext_port_str) if ext_port_str.isdigit() else None
        int_port = int(int_port_str) if int_port_str.isdigit() else None

        running.append(
            {
                "name": name,
                "status": status,
                "external_port": ext_port,
                "internal_port": int_port,
            }
        )

    return running


def port_in_use(
    port: int, current_instance_name: Optional[str] = None
) -> Optional[str]:
    """
    Return the instance name using this port, or None if free.
    """
    for inst in get_running_ports():
        name = inst.get("name")
        if current_instance_name and name == current_instance_name:
            continue

        ext_port = inst.get("external_port")
        int_port = inst.get("internal_port")

        if ext_port == port or int_port == port:
            return name

    return None


def name_in_use(selected_name: str) -> bool:
    """
    Return True if an instance already uses this name.
    """
    for inst in find_instances():
        name = inst.get("name")
        if selected_name == name:
            return True
    return False


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
            self.status = instances["status"]
        else:
            self.status = "Not Running"
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
        app.port_selection["name"] = self.selected_instance_name
        app.port_selection["external_port"] = self.external_port
        app.port_selection["internal_port"] = self.internal_port
        app.port_selection["status"] = self.status
        logging.info(app.port_selection)
        process_response(self)
