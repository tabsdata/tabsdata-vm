from tdtui.core.find_instances import main as find_instances
from tdtui.instance.select_instance import run_instance_selector
from tdtui.instance.display_instances import display_instances_rich
import typer
from InquirerPy import inquirer
from rich.console import Console
from rich.panel import Panel


def run_instance_management():

    choices = [
        "Display Instances",
        "Create An Instance",
        "Start An Instance",
        "Stop An Instance",
        "Set Working Instance",
    ]
    selection = inquirer.select("What would you like to do", choices).execute()
    instances = find_instances()
    if selection == "Display Instances":
        display_instances_rich(instances)
    elif selection == "Start An Instance":
        instance = run_instance_selector(instances)
    elif selection == "Stop An Instance":
        instance = run_instance_selector(instances)
    elif selection == "Set Working Instance":
        instance = run_instance_selector(instances)
    elif selection == "Create An Instance":
        instance = run_instance_selector(instances)
    else:

        console = Console()

        console.print(
            Panel(
                "🚀 Exiting TUI",
                border_style="green",
                title="Success",
                padding=(1, 2),
            )
        )
    return


if __name__ == "__main__":
    run_instance_management()
