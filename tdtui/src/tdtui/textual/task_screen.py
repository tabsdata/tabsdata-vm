from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Awaitable, Callable, List

from textual.app import App, ComposeResult
from textual.screen import Screen
from textual.containers import Vertical, Horizontal, VerticalScroll, Container
from textual.widgets import Label, Footer, Static, Button
from textual.widgets import RichLog  # ← Correct widget

from tdtui.textual.spinners import SpinnerWidget
import logging
from pathlib import Path
import asyncio.subprocess
import random
from tdtui.core.yaml_getter_setter import set_yaml_value
from time import sleep
from tdtui.core.find_instances import main as find_instances


# Configure file logging
logging.basicConfig(
    filename=Path(__file__).resolve().parent / "log.log",
    level=logging.INFO,
    format="%(message)s",
)


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
        if event.button.id == "close-btn":
            active_screen = self.app.screen
            self.app.push_screen("main")

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
        # self.app.port_selection = {
        #     "name": "tabsdata",
        #     "external_port": 2457,
        #     "internal_port": 2458,
        #     "status": "Running",
        # }
        self.instance_name = self.app.port_selection["name"]
        self.ext_port = self.app.port_selection["external_port"]
        self.int_port = self.app.port_selection["internal_port"]
        super().__init__(tasks)

    async def prepare_instance(self, label=None):
        logging.info("a: " + self.app.port_selection["status"])
        logging.info(f"b: {self.app.port_selection}")
        logging.info(
            f"c: {[
            i["name"]
            for i in find_instances()
            if i["name"] == self.app.port_selection["name"]
        ]}"
        )
        if self.app.port_selection["status"] == "Running":
            self.log_line(label, "STOP SERVER")
            process = await asyncio.create_subprocess_exec(
                "tdserver",
                "stop",
                "--instance",
                f"{self.instance_name}",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
        elif self.app.port_selection["name"] not in [
            i["name"]
            for i in find_instances()
            if i["name"] == self.app.port_selection["name"]
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


class DemoApp(App):
    BINDINGS = [("ctrl+c", "quit", "Quit")]

    def on_mount(self):
        self.push_screen(TaskScreen())


if __name__ == "__main__":
    DemoApp().run()
