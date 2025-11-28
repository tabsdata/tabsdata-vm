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

from __future__ import annotations

from typing import Optional, Dict, Any, List

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Input, Label, Static, Footer
from textual.containers import Vertical, VerticalScroll
from rich.text import Text
from typing import Optional, Dict, List, Union

from tdtui.core.find_instances import pull_all_tabsdata_instance_data as find_instances
import logging
from pathlib import Path

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
        elif inst_name == "_Create_Instance" or inst == "_Create_Instance":
            pass
        elif inst_name is not None:
            inst = [i for i in find_instances() if i["name"] == inst_name][0]
        elif hasattr(self.app, "instance_name"):
            inst = [i for i in find_instances() if i["name"] == self.app.instance_name][
                0
            ]

        if (
            inst is None
            or inst_name == "_Create_Instance"
            or inst == "_Create_Instance"
        ):
            status = None
        else:
            name = inst.get("name", None)
            status = inst.get("status", None)
            cfg_ext = inst.get("cfg_ext", None)
            cfg_int = inst.get("cfg_int", None)
            arg_ext = inst.get("arg_ext", None)
            arg_int = inst.get("arg_int", None)
        if inst_name == "_Create_Instance":
            status_color = "#1F66D1"
            status_line = f"Create a New Instance"
            line1 = f""
            line2 = f""
            self.app.instance_start_configuration["status"] = "Running"
        elif status == "Running":
            status_color = "#22c55e"
            status_line = f"{name}  ● Running"
            line1 = f"running on → ext: {arg_ext}"
            line2 = f"running on → int: {arg_int}"
            self.app.instance_start_configuration["status"] = "Running"
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
        if id is not None:
            self.id = id
        self.header = header

    def compose(self) -> ComposeResult:
        logging.info(self.app.instance_start_configuration)
        instance = self.app.instance_start_configuration.get("name")
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
        instanceWidgets.insert(
            0,
            LabelItem(
                label=InstanceWidget(inst_name="_Create_Instance"),
                override_label="_Create_Instance",
            ),
        )
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
            id="MainScreen",
        )


class InstanceManagementScreen(ScreenTemplate):
    def __init__(self):
        super().__init__(
            choices=["Start an Instance", "Stop an Instance", "Set Working Instance"],
            id="InstanceManagementScreen",
        )


class GettingStartedScreen(ScreenTemplate):
    def __init__(self):
        super().__init__(
            choices=["Bind An Instance", "Help", "Exit"],
            header="Welcome to Tabsdata. Select an Option to get started below",
        )


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
      app.instance_start_configuration (dict)
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
            self.external_port = "2457"
            self.internal_port = "2458"

    def compose(self) -> ComposeResult:
        logging.info(self.virtual_size)

        # import here to avoid circulars if needed
        from tdtui.app import CurrentInstanceWidget

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
        if self.instance_name is not None and self.instance_name != "_Create_Instance":
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
        app.instance_start_configuration["name"] = self.selected_instance_name
        app.instance_start_configuration["external_port"] = self.external_port
        app.instance_start_configuration["internal_port"] = self.internal_port
        app.instance_start_configuration["status"] = self.status
        logging.info(app.instance_start_configuration)
        process_response(self)


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
    CSS = """
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

    async def on_mount(self) -> None:
        self.log_widget = self.query_one("#task-log", RichLog)
        self.log_line(None, "Starting setup tasks…")
        asyncio.create_task(self.run_tasks())

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        from tdtui.app import GettingStartedScreen

        if event.button.id == "close-btn":
            active_screen = self.app.screen
            self.app.push_screen(GettingStartedScreen())

    def log_line(self, task: str | None, msg: str) -> None:
        if task:
            color = self.task_colors.get(task, "white")
            line = f"[{color}][{task}]:[/] {msg}"
        else:
            line = msg

        if self.log_widget:
            self.log_widget.write(line)
        logging.info(line)

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
        footer = self.query_one(Footer)
        await self.mount(Button("Done", id="close-btn"), before=footer)


class TaskScreen(SequentialTasksScreenTemplate):
    def __init__(self) -> None:
        tasks = [
            TaskSpec("Preparing Instance", self.prepare_instance),
            TaskSpec("Binding Ports", self.bind_ports),
            TaskSpec("Connecting to Tabsdata instance", self.connect_tabsdata),
            TaskSpec("Checking Server Status", self.run_tdserver_status),
        ]
        # self.app.instance_start_configuration = {
        #     "name": "tabsdata",
        #     "external_port": 2457,
        #     "internal_port": 2458,
        #     "status": "Running",
        # }
        self.instance_name = self.app.instance_start_configuration["name"]
        self.ext_port = self.app.instance_start_configuration["external_port"]
        self.int_port = self.app.instance_start_configuration["internal_port"]
        super().__init__(tasks)

    async def prepare_instance(self, label=None):
        logging.info("a: " + self.app.instance_start_configuration["status"])
        logging.info(f"b: {self.app.instance_start_configuration}")
        logging.info(
            f"c: {[
            i["name"]
            for i in find_instances()
            if i["name"] == self.app.instance_start_configuration["name"]
        ]}"
        )
        if self.app.instance_start_configuration["status"] == "Running":
            self.log_line(label, "STOP SERVER")
            process = await asyncio.create_subprocess_exec(
                "tdserver",
                "stop",
                "--instance",
                f"{self.instance_name}",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
        elif self.app.instance_start_configuration["name"] not in [
            i["name"]
            for i in find_instances()
            if i["name"] == self.app.instance_start_configuration["name"]
        ]:
            self.log_line(label, "START SERVER")
            process = await asyncio.create_subprocess_exec(
                "tdserver",
                "create",
                "--instance",
                f"{self.instance_name}",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
        else:
            pass

        if "process" in locals():
            while True:
                line = await process.stdout.readline()
                if not line:
                    break
                self.log_line(label, line.decode().rstrip("\n"))
            code = await process.wait()
            self.log_line(label, f"Exited with code {code}")

    async def bind_ports(self, label=None):
        CONFIG_PATH = root = (
            Path.home()
            / ".tabsdata"
            / "instances"
            / self.instance_name
            / "workspace"
            / "config"
            / "proc"
            / "regular"
            / "apiserver"
            / "config"
            / "config.yaml"
        )
        logging.info(CONFIG_PATH)

        cfg_ext = set_yaml_value(
            path=CONFIG_PATH,
            key="addresses",
            value=f"127.0.0.1:{self.ext_port}",
            value_type="list",
        )
        self.log_line(label, cfg_ext)
        cfg_int = set_yaml_value(
            path=CONFIG_PATH,
            key="internal_addresses",
            value=f"127.0.0.1:{self.int_port}",
            value_type="list",
        )
        self.log_line(label, cfg_int)

    async def connect_tabsdata(self, label=None):
        process = await asyncio.create_subprocess_exec(
            "tdserver",
            "start",
            "--instance",
            f"{self.instance_name}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        self.log_line(label, "Running tdserver status…")
        while True:
            line = await process.stdout.readline()
            if not line:
                break
            self.log_line(label, line.decode().rstrip("\n"))
        code = await process.wait()
        self.log_line(label, f"Exited with code {code}")

    async def run_tdserver_status(self, label=None):
        process = await asyncio.create_subprocess_exec(
            "tdserver",
            "status",
            "--instance",
            f"{self.instance_name}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        self.log_line(label, "Running tdserver status…")
        while True:
            line = await process.stdout.readline()
            if not line:
                break
            self.log_line(label, line.decode().rstrip("\n"))
        code = await process.wait()
        self.log_line(label, f"Exited with code {code}")
