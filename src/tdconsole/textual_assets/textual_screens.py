from __future__ import annotations
from textual.app import App, ComposeResult
from textual.screen import Screen
from textual.widgets import ListView, ListItem, Label, Static, Button
from pathlib import Path
from tdconsole.textual_assets.spinners import SpinnerWidget
from typing import Awaitable, Callable, List, Iterable
from textual.widgets import RichLog, DirectoryTree, Pretty, Tree
from textual.containers import Center
from tdconsole.core import input_validators
from textual import on

import ast

from tdconsole.core.find_instances import (
    sync_filesystem_instances_to_db,
    instance_name_to_instance,
    manage_working_instance,
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
from tdconsole.core.yaml_getter_setter import get_yaml_value, set_yaml_value
from functools import partial

from tdconsole.core.find_instances import (
    sync_filesystem_instances_to_db as sync_filesystem_instances_to_db,
)
import logging
from pathlib import Path
from tdconsole.textual_assets.textual_instance_config import (
    name_in_use,
    port_in_use,
    get_running_ports,
    validate_port,
)
from tdconsole.core.models import Instance


from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Static


from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Static, Button
from textual.containers import Horizontal, Vertical
import os
from textual.widgets._tree import TreeNode


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


from tdconsole.core import instance_tasks


class InstanceWidget(Static):
    """Rich panel showing the current working instance."""

    def __init__(self, inst: Optional[str] = None):
        super().__init__()
        if isinstance(inst, str):
            inst = instance_name_to_instance(inst)
        self.inst = inst

    def _make_instance_panel(self) -> Panel:

        inst = self.inst

        status_color = "#e4e4e6"
        status_line = f"○ No Instance Selected"
        line1 = f"No External Running Port"
        line2 = f"No Internal Running Port"

        if inst is None:
            pass
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


# push instance


class ListScreenTemplate(Screen):
    def __init__(self, choices=None, id=None, header="Select a File: "):
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
        if selected not in ["Asset Management", "Register a Function"]:
            self.app.handle_api_response(self, selected)  # push instance


class InstanceSelectionScreen(Screen):
    BINDINGS = [
        ("enter", "press_close", "Done"),
    ]

    def __init__(self, instances=None):
        super().__init__()
        if instances is None and self.app.flow_mode != "stop":
            self.instances = sync_filesystem_instances_to_db(app=self.app)
        else:
            self.instances = instances

    def compose(self) -> ComposeResult:
        instances = self.instances
        if instances is None:
            self.list = Vertical(
                Static("No Instances Found"), Button("Back", id="back-btn")
            )
        else:
            if isinstance(instances, Instance):
                instances = [instances]

            instanceWidgets = [
                LabelItem(label=InstanceWidget(i), override_label=i.name)
                for i in instances
            ]

            if self.app.flow_mode != "stop":
                instanceWidgets.insert(
                    0,
                    LabelItem(
                        label=InstanceWidget(inst="_Create_Instance"),
                        override_label="_Create_Instance",
                    ),
                )
            self.list = ListView(
                *instanceWidgets,
            )
        with VerticalScroll():
            # self.list = ListView(*[LabelItem('a'), LabelItem('b')])
            yield self.list
        yield Footer()
        try:
            btn = self.query_one("#back-btn")
            btn.focus()
        except:
            pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back-btn":
            self.app.pop_screen()

    def on_show(self) -> None:
        # called again when you push this screen a
        #  second time (if reused)
        self.set_focus(self.list)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        selected = event.item.label
        self.app.handle_api_response(self, selected)  # push instance

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
            choices=[
                "Instance Management",
                "Asset Management",
                "Workflow Management (Not Built Yet)",
                "Config Management (Not Built Yet)",
                "Exit",
            ],
        )

    @on(ListView.Selected)
    def handle_api_response(self, event: ListView.Selected):
        value = event.item.label
        if value == "Asset Management":
            self.app.push_screen(AssetManagementScreen())


class AssetManagementScreen(ListScreenTemplate):

    def __init__(self):
        super().__init__(
            choices=[
                "Register a Function",
                "Update a Function",
                "Delete a Function",
                "Create a Collection",
                "Delete a Collection",
                "Delete a Table",
                "Sample Table Schema",
                "Sample Table Data" "Exit",
            ],
        )

    @on(ListView.Selected)
    def handle_api_response(self, event: ListView.Selected):
        value = event.item.label
        if value == "Register a Function":
            self.app.push_screen(PyFileTreeScreen())


class InstanceManagementScreen(ListScreenTemplate):
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

#     Input {
#   height: 5;      
# }
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
            Vertical(
                Horizontal(
                    Label(
                        "What Would Like to call your Tabsdata Instance:",
                        id="title-instance",
                    ),
                    Input(
                        placeholder=self.placeholder,
                        validate_on=["submitted"],
                        validators=[
                            input_validators.ValidInstanceName(self.app, self.instance)
                        ],
                        id="instance-input",
                        classes="inputs",
                    ),
                ),
                Pretty("", id="instance-message"),
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
                        validate_on=["submitted"],
                        validators=[
                            input_validators.ValidExtPort(self.app, self.instance)
                        ],
                        id="ext-input",
                        classes="inputs",
                    ),
                ),
                Pretty("", id="ext-message"),
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
                        max_length=5,
                        validators=[
                            input_validators.ValidIntPort(self.app, self.instance)
                        ],
                        id="int-input",
                        classes="inputs",
                    ),
                ),
                Pretty("", id="int-message"),
                id="int-container",
                classes="input_container",
            ),
            Static(""),
        )
        yield Footer()

    def set_visibility(self):
        input_containers = self.query(".input_container")
        instance_container = self.query_one("#instance-container")
        ext_container = self.query_one("#ext-container")
        int_container = self.query_one("#int-container")

        instance_input = self.query_one("#instance-input")
        ext_input = self.query_one("#ext-input")
        int_input = self.query_one("#int-input")

        for i in input_containers:
            i.display = False

        if self.instance.name == "_Create_Instance":
            instance_container.display = True
            self.set_focus(instance_input)
            return

        ext_container.display = True
        self.set_focus(ext_input)
        return

    def on_mount(self) -> None:
        self.set_visibility()

    def on_screen_resume(self, event) -> None:
        self.set_visibility()

    @on(Input.Submitted, "#instance-input")
    def handle_instance_input(self, event: Input.Submitted) -> None:
        value = event.value
        if value == "":
            value = "tabsdata"
            event.input.value = value  # update UI
            validation_result = event.input.validate(
                value
            )  # re-run validators with new value
        else:
            validation_result = event.validation_result

        if not validation_result.is_valid:
            ext_message = self.query_one("#instance-message")
            ext_message.update(validation_result.failure_descriptions)
            event.input.clear()
        else:
            self.instance.name = value
            ext_message = self.query_one("#instance-message")
            ext_message.update(f"Instance Name Set to {value}")
            ext_container = self.query_one("#ext-container")
            ext_input = self.query_one("#ext-input")
            ext_container.display = True
            self.set_focus(ext_input)

    @on(Input.Submitted, "#ext-input")
    async def handle_ext_input(self, event: Input.Submitted) -> None:
        value = event.value
        if value == "":
            value = self.instance.arg_ext
            event.input.value = value
            await event.input.action_submit()
            return

        if not event.validation_result.is_valid:
            ext_message = self.query_one("#ext-message")
            ext_message.update(event.validation_result.failure_descriptions)
            event.input.clear()
        else:
            self.instance.arg_ext = value
            ext_message = self.query_one("#ext-message")
            ext_message.update(f"External Port Set to {value}")
            int_container = self.query_one("#int-container")
            int_input = self.query_one("#int-input")
            int_container.display = True
            self.set_focus(int_input)

    @on(Input.Submitted, "#int-input")
    async def handle_int_input(self, event: Input.Submitted) -> None:
        value = event.value
        if value == "":
            value = self.instance.arg_int
            event.input.value = value
            await event.input.action_submit()
            return

        if not event.validation_result.is_valid:
            ext_message = self.query_one("#int-message")
            ext_message.update(event.validation_result.failure_descriptions)
            event.input.clear()
        else:
            self.instance.arg_int = value
            ext_message = self.query_one("#int-message")
            ext_message.update(f"External Port Set to {value}")
            self.app.handle_api_response(self, self.instance)


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
            self.app.handle_api_response(self)

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
            TaskSpec(
                "Logging you In",
                partial(instance_tasks.tabsdata_login, self, self.instance),
            ),
        ]

        super().__init__(tasks)

    def conclude_tasks(self, status=None):
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
