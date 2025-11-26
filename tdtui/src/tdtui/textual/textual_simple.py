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
            id="GettingStartedScreen",
            header="Welcome to Tabsdata. Select an Option to get started below",
        )


class NestedMenuApp(App):
    CSS = """

    VerticalScroll {
        width: 1fr;
    }

    #right {
        overflow-y: hidden;
    }
    """
    SCREENS = {
        "main": MainScreen,
        "instancemanagement": InstanceManagementScreen,
        "PortConfig": lambda: PortConfigScreen(),
        "GettingStarted": GettingStartedScreen,
        "InstanceSelection": InstanceSelectionScreen,
        "Overflow": OverflowScreen,
        "InstanceStartup": lambda: InstanceStartup(),
    }
    BINDINGS = [
        ("ctrl+c", "quit", "Quit"),
        ("ctrl+b", "go_back", "Go Back"),
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.port_selection = {
            "name": None,
            "external_port": None,
            "internal_port": None,
            "status": "Not Running",
        }

    def on_mount(self) -> None:
        # start with a MainMenu instance
        self.push_screen("GettingStarted")

    def action_go_back(self):
        logging.info(
            f'screen is { {k: v for k, v in self.screen.__dict__.items() if "InstanceSelection" in str(v)} }'
        )

        if self.screen.id not in ["MainScreen", "GettingStartedScreen"]:
            active_screen = self.screen
            active_screen_class = self.screen.__class__
            active_screen_name = self.screen.name
            self.pop_screen()
            # self.install_screen(active_screen_class(), active_screen_name)


def run_app():
    NestedMenuApp().run()


if __name__ == "__main__":
    NestedMenuApp().run()
