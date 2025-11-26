from rich.console import Console, Group
from rich.panel import Panel
from rich.text import Text
from rich.align import Align
from rich.table import Table

from tdtui.core.find_instances import main as find_instances


console = Console()


def make_instance_panel(inst: dict) -> Panel:
    name = inst.get("name", "?")
    status = inst.get("status", "Not_Running")
    cfg_ext = inst.get("cfg_ext", "None")
    cfg_int = inst.get("cfg_int", "None")
    arg_ext = inst.get("arg_ext", "None")
    arg_int = inst.get("arg_int", "None")

    if status == "Running":
        status_color = "#22c55e"
        status_line = f"{name}  ● Running"
        line1 = f"running on → ext: {arg_ext}"
        line2 = f"running on → int: {arg_int}"
    else:
        status_color = "#ef4444"
        status_line = f"{name}  ○ Not running"
        line1 = f"configured on → ext: {cfg_ext}"
        line2 = f"configured on → int: {cfg_int}"

    header = Text(status_line, style=f"bold {status_color}")
    body = Text(f"{line1}\n{line2}", style="#e2e8f0")

    return Panel(
        Group(header, body),
        border_style=status_color,
        padding=(0, 1),
        expand=False,
    )


def display_instances_rich(instances=None) -> None:
    if instances == None:
        instances=find_instances()

    running_panels: list[Panel] = []
    stopped_panels: list[Panel] = []

    for inst in instances:
        panel = make_instance_panel(inst)
        if inst.get("status") == "Running":
            running_panels.append(panel)
        else:
            stopped_panels.append(panel)

    # Build grid for left/right columns without using Columns
    grid = Table.grid(padding=(0, 4))
    grid.expand = False

    left_group: Group | None = None
    right_group: Group | None = None

    if stopped_panels:
        left_group = Group(
            Text(" Stopped", style="bold #ef4444"),
            *stopped_panels,
        )

    if running_panels:
        right_group = Group(
            Text(" Running", style="bold #22c55e"),
            *running_panels,
        )

    if left_group and right_group:
        grid.add_row(left_group, right_group)
    elif left_group:
        grid.add_row(left_group)
    elif right_group:
        grid.add_row(right_group)

    header = Group(
        Align.center(Text("📦 Tabsdata Instances", style="bold #22c55e")),
        Align.center(
            Text(
                "You have the following Tabsdata instances available:",
                style="#e2e8f0",
            )
        ),
        Text(""),  # spacer
    )

    inner = Group(
        header,
        Align.center(grid),
    )

    outer = Panel(
        inner,
        border_style="#0f766e",
        padding=(1, 2),
        expand=False,  # now respected because we are not using Columns
    )

    console.print(Align.center(outer))


if __name__ == "__main__":
    instances = find_instances()
    display_instances_rich(instances)
