from __future__ import annotations
from textual.app import App, ComposeResult
from textual.screen import Screen
from textual.widgets import ListView, ListItem, Label, Static, Button
from pathlib import Path
from tdtui.textual_assets.spinners import SpinnerWidget
from typing import Awaitable, Callable, List
from textual.widgets import RichLog
from textual.containers import Center

from tdtui.core.find_instances import (
    sync_filesystem_instances_to_db,
    instance_name_to_instance,
    manage_working_instance,
    print_all_instance_data,
    sync_filesystem_instances_to_db,
)
import logging
from typing import Optional, Dict, Any, List
from textual.containers import VerticalScroll, Container
from dataclasses import dataclass

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


from typing import Optional, Dict, Any, List

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Input, Label, Static, Footer
from textual.containers import Vertical, VerticalScroll
from rich.text import Text
from typing import Optional, Dict, List, Union

import asyncio.subprocess
import random
import asyncio
from tdtui.core.yaml_getter_setter import get_yaml_value, set_yaml_value
from functools import partial

from tdtui.core.find_instances import (
    sync_filesystem_instances_to_db as sync_filesystem_instances_to_db,
)
import logging
from pathlib import Path
from tdtui.textual_assets.textual_instance_config import (
    name_in_use,
    port_in_use,
    get_running_ports,
    validate_port,
)


from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Static


from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Static, Button
from textual.containers import Horizontal, Vertical


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
    }

    #wrapper {
        width: 80;
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


from tdtui.core import instance_tasks

logging.basicConfig(
    filename="/Users/danieladayev/test-tui/tabsdata-tui/logger.log",
    level=logging.INFO,
    format="%(message)s",
    force=True,
)


class InstanceWidget(Static):
    """Rich panel showing the current working instance."""

    def __init__(self, inst: Optional[str] = None):
        super().__init__()
        if isinstance(inst, str):
            inst = instance_name_to_instance(inst)
        self.inst = inst

    def _make_instance_panel(self) -> Panel:

        inst = self.inst
        try:
            logging.info([(i, inst[i]) for i in inst])
        except:
            pass

        if inst is None:
            status_color = "#e4e4e6"
            status_line = f"○ No Instance Selected"
            line1 = f"No External Running Port"
            line2 = f"No Internal Running Port"
        elif inst.name == "_Create_Instance":
            status_color = "#1F66D1"
            status_line = f"Create a New Instance"
            line1 = f""
            line2 = f""
        elif inst.status == "Running":
            status_color = "#22c55e"
            status_line = f"{inst.name}  ● Running"
            line1 = f"running on → ext: {inst.arg_ext}"
            line2 = f"running on → int: {inst.arg_int}"
        elif inst.status == "Not Running":
            status_color = "#ef4444"
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


class CurrentInstanceWidget(InstanceWidget):
    def __init__(self, inst: Optional[str] = None):
        sync_filesystem_instances_to_db(app=self.app)
        super().__init__()
        if isinstance(inst, str):
            inst = instance_name_to_instance(inst)
        working_instance = self.app.app_query_session("instances", working=True)
        if working_instance is not None:
            self.inst = inst
        else:
            self.inst = working_instance

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
        if id is not None:
            self.id = id
        self.header = header
        self.app.working_instance = self.app.app_query_session(
            "instances", working=True
        )

    def compose(self) -> ComposeResult:
        with VerticalScroll():
            if self.header is not None:
                yield Label(self.header, id="listHeader")
            yield CurrentInstanceWidget(self.app.working_instance)
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
        self.app.handle_api_response(self, selected)  # push instance


class InstanceSelectionScreen(Screen):
    def __init__(self, instances=None):
        super().__init__()
        if instances is None:
            self.instances = sync_filesystem_instances_to_db(app=self.app)
        else:
            self.instances = instances

    def compose(self) -> ComposeResult:
        instances = self.instances
        if len(instances) == 1:
            instances = [instances]
        instanceWidgets = [
            LabelItem(label=InstanceWidget(i), override_label=i.name) for i in instances
        ]
        instanceWidgets.insert(
            0,
            LabelItem(
                label=InstanceWidget(inst="_Create_Instance"),
                override_label="_Create_Instance",
            ),
        )
        with VerticalScroll():
            # self.list = ListView(*[LabelItem('a'), LabelItem('b')])
            self.list = ListView(
                *instanceWidgets,
            )
            yield self.list
        yield Footer()

    def on_show(self) -> None:
        # called again when you push this screen a
        #  second time (if reused)
        self.set_focus(self.list)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        selected = event.item.label
        self.app.handle_api_response(self, selected)  # push instance


class MainScreen(ScreenTemplate):

    def __init__(self):
        super().__init__(
            choices=[
                "Instance Management",
                "Workflow Management",
                "Asset Management",
                "Config Management",
                "Exit",
            ],
        )


class InstanceManagementScreen(ScreenTemplate):
    def __init__(self):
        super().__init__(
            choices=[
                "Bind An Instance",
                "Start an Instance",
                "Stop An Instance",
            ],
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
        yield VerticalScroll(
            CurrentInstanceWidget(self.instance),
            Label(
                "What Would Like to call your Tabsdata Instance:",
                id="title-instance",
            ),
            Input(placeholder=self.placeholder, id="instance-input"),
            Label("", id="instance-error"),
            Label("", id="instance-confirm"),
            Label("Configure Tabsdata ports", id="title"),
            Label("External port:", id="ext-label"),
            Input(
                placeholder=str(self.instance.arg_ext or ""),
                id="ext-input",
            ),
            Label("", id="ext-error"),
            Label("", id="ext-confirm"),
            Label("Internal port:", id="int-label"),
            Input(
                placeholder=str(self.instance.arg_int or ""),
                id="int-input",
            ),
            Label("", id="int-error"),
            Label("", id="int-confirm"),
            Static(""),
        )

        yield Footer()

    def set_visibility(self) -> None:
        """Decide which step to show first and hide later steps."""
        is_existing = (
            self.instance is not None and self.instance.name != "_Create_Instance"
        )

        # Instance name step
        show_instance_name = not is_existing
        self.query_one("#title-instance", Label).display = show_instance_name
        self.query_one("#instance-input", Input).display = show_instance_name
        self.query_one("#instance-error", Label).display = show_instance_name
        self.query_one("#instance-confirm", Label).display = show_instance_name

        # External port step is hidden until instance name is chosen for new instances
        show_ext = is_existing
        self.query_one("#title", Label).display = show_ext
        self.query_one("#ext-label", Label).display = show_ext
        self.query_one("#ext-input", Input).display = show_ext
        self.query_one("#ext-error", Label).display = show_ext
        self.query_one("#ext-confirm", Label).display = show_ext

        # Internal port step starts hidden
        for wid in ("#int-label", "#int-input", "#int-error", "#int-confirm"):
            self.query_one(wid, Static | Label | Input).display = False

        # Focus
        if show_instance_name:
            self.set_focus(self.query_one("#instance-input", Input))
        else:
            self.set_focus(self.query_one("#ext-input", Input))

    def on_mount(self) -> None:
        self.set_visibility()

    def on_screen_resume(self, event) -> None:
        self.set_visibility()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        input_id = event.input.id
        if input_id == "ext-input":
            self._handle_port("ext", event.input, require_diff=False)
        elif input_id == "int-input":
            self._handle_port("int", event.input, require_diff=True)
        elif input_id == "instance-input":
            self._handle_instance_name_submitted(event.input)

    # ---------------------------
    # Shared port flow
    # ---------------------------

    def _handle_port(self, kind: str, port_input: Input, require_diff: bool) -> None:
        """
        kind: "ext" or "int"
        require_diff: True for internal port, which must differ from arg_ext.
        """
        error_label = self.query_one(f"#{kind}-error", Label)
        confirm_label = self.query_one(f"#{kind}-confirm", Label)

        error_label.update("")
        confirm_label.update("")

        # Current value on instance, e.g. arg_ext or arg_int
        current_value = getattr(self.instance, f"arg_{kind}", None)

        value = port_input.value.strip()
        if value == "":
            value = current_value

        if not validate_port(value):
            error_label.update("That is not a valid port number. Please enter 1–65535.")
            self.set_focus(port_input)
            port_input.clear()
            return

        port = int(value)

        # Internal must not equal external
        if (
            require_diff
            and self.instance.arg_ext is not None
            and port == self.instance.arg_ext
        ):
            error_label.update(
                "Internal port must not be the same as external port. "
                "Please choose another port."
            )
            self.set_focus(port_input)
            port_input.clear()
            return

        in_use_by = port_in_use(
            app=self.app,
            port=port,
            current_instance_name=self.instance.name,
        )

        if in_use_by is not None:
            error_label.update(
                f"Port {port} is already in use by instance '{in_use_by}'. "
                "Please choose a different port."
            )
            self.set_focus(port_input)
            port_input.clear()
            return

        # Valid, distinct, and free
        setattr(self.instance, f"arg_{kind}", port)
        confirm_label.update(
            Text(
                f"Selected {'external' if kind == 'ext' else 'internal'} port: {port}",
                style="bold #22c55e",
            )
        )

        # If we just set external, reveal internal inputs
        if kind == "ext":
            self.query_one("#int-label", Label).display = True
            self.query_one("#int-input", Input).display = True
            self.query_one("#int-error", Label).display = True
            self.query_one("#int-confirm", Label).display = True
            self.set_focus(self.query_one("#int-input", Input))
        else:
            # Done with both ports, return instance to app
            self.app.handle_api_response(self, self.instance)

    # ---------------------------
    # Instance Name flow
    # ---------------------------

    def _handle_instance_name_submitted(self, instance_input: Input) -> None:
        instance_error = self.query_one("#instance-error", Label)
        instance_confirm = self.query_one("#instance-confirm", Label)

        instance_error.update("")
        instance_confirm.update("")

        value = instance_input.value.strip() or "tabsdata"

        if name_in_use(self.app, value):
            instance_error.update("That Name is Already in Use. Please Try Another:")
            self.set_focus(instance_input)
            instance_input.clear()
            return

        # Valid and free
        self.instance.name = value
        instance_confirm.update(
            Text(
                f"Defined an Instance with the following Name: {value}",
                style="bold #22c55e",
            )
        )

        # Reveal external port step and move focus there
        self.query_one("#title", Label).display = True
        self.query_one("#ext-label", Label).display = True
        self.query_one("#ext-input", Input).display = True
        self.query_one("#ext-error", Label).display = True
        self.query_one("#ext-confirm", Label).display = True

        self.set_focus(self.query_one("#ext-input", Input))


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

    def set_done(self) -> None:
        self.query_one(f"#{self.id}-spinner").display = False
        self.query_one(f"#{self.id}-label", Label).update(f"✅ {self.description}")


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

    def compose(self) -> ComposeResult:
        for index, task in enumerate(self.tasks):
            row = TaskRow(task.description, task_id=f"task-{index}")
            self.task_rows.append(row)

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

    def conclude_tasks(self):
        self.query_one(VerticalScroll).scroll_end(animate=False)

    async def on_mount(self) -> None:
        self.log_widget = self.query_one("#task-log", RichLog)
        self.log_line(None, "Starting setup tasks…")
        asyncio.create_task(self.run_tasks())

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "close-btn":
            self.app.handle_api_response(self)

    def log_line(self, task: str | None, msg: str) -> None:
        if task:
            color = self.task_colors.get(task, "white")
            line = f"[{color}][{task}]:[/] {msg}"
        else:
            line = msg

        if self.log_widget:
            self.log_widget.write(line)
        logging.info(line)

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

    async def run_single_task(self, idx: int, task: TaskSpec) -> None:
        row = self.task_rows[idx]
        row.set_running()
        self.log_line(task.description, "Starting")
        try:
            await task.func(task.description)
            self.log_line(task.description, "Finished")
        except Exception as e:
            self.log_line(task.description, f"Error: {e!r}")
            raise
        finally:
            row.set_done()

    def action_press_close(self) -> None:
        # Only act if the button exists
        try:
            btn = self.query_one("#close-btn", Button)
        except Exception:
            return
        btn.press()

    async def run_tasks(self) -> None:
        background = []
        for i, t in enumerate(self.tasks):
            if t.background:
                self.log_line(t.description, "Scheduling background task")
                background.append(asyncio.create_task(self.run_single_task(i, t)))
        for i, t in enumerate(self.tasks):
            if not t.background:
                await self.run_single_task(i, t)
        if background:
            await asyncio.gather(*background)
        self.log_line(None, "🎉 All tasks complete.")
        self.conclude_tasks()
        footer = self.query_one(Footer)
        button = await self.mount(Button("Done", id="close-btn"), before=footer)
        button.focus()


class BindAndStartInstance(SequentialTasksScreenTemplate):
    def __init__(self, instance) -> None:
        self.instance = instance
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

    def conclude_tasks(self):
        super().conclude_tasks()
        manage_working_instance(self.app.session, self.instance)
        self.app.session.merge(self.instance)
        self.app.session.commit()


class StartInstance(SequentialTasksScreenTemplate):
    def __init__(self, instance) -> None:
        self.instance = instance

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
    def __init__(self, instance) -> None:
        self.instance = instance

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
