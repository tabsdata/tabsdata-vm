import typer
from InquirerPy import inquirer
from rich.console import Console
from rich.panel import Panel
from tdtui.instance.cli import run_instance_management
from yaspin import yaspin


app = typer.Typer()


@app.command()
def init(selection=None):
    while selection != "Exit":
        choices = [
            "Instance Management",
            "Workflow Management",
            "Asset Management",
            "Config Management",
            "Exit",
        ]
        selection = inquirer.select(
            "Welcome to the tabsdata TUI. Please select an option", choices
        ).execute()
        if selection == "Instance Management":
            run_instance_management()
        elif selection == "Workflow Management":
            exit
        elif selection == "Asset Management":
            exit
        elif selection == "Config Management":
            exit
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



def main():
    app()


if __name__ == "__main__":
    main()
