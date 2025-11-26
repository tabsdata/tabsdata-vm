from tdtui.core.find_instances import main as find_instances
from tdtui.instance.select_instance import run_instance_selector
from tdtui.instance.display_instances import display_instances_rich
import typer
from InquirerPy import inquirer
from rich.console import Console
from rich.panel import Panel
from yaspin import yaspin
from tdtui.instance.instance_setters import set_config_yaml, start_instance, stop_instance, create_instance, delete_instance


def run_instance_management():

    choices = [
        "Display Instances",
        "Create An Instance",
        "Start An Instance",
        "Stop An Instance",
        "Delete An Instance",
        "Set Working Instance",
        "Exit"
    ]
    selection = None
    while selection != "Exit":
        selection = inquirer.select("What would you like to do", choices).execute()
        instances = find_instances()
        if selection == "Display Instances":
            display_instances_rich(instances)
        elif selection == "Start An Instance":
            instance = run_instance_selector(instances)
            start_instance(instance)
        elif selection == "Stop An Instance":
            instance = run_instance_selector(instances)
            stop_instance(instance)
        elif selection == "Set Working Instance":
            instance = run_instance_selector(instances)
        elif selection == "Create An Instance":
            instance = create_instance()
        elif selection == "Exit":
            pass
        elif selection == "Delete An Instance":
            instance = run_instance_selector(instances)
            delete_instance(instance)
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
