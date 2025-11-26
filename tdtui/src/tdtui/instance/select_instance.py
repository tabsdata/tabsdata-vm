from textual.app import App, ComposeResult
from textual.widgets import Static
from textual.containers import VerticalScroll  # 👈 changed this
from textual import events

from tdtui.core.find_instances import main as find_instances

import logging
import os
from pathlib import Path

logging.basicConfig(
    filename= Path.home() / "tabsdata-vm" / "log.log",
    level=logging.INFO,
    format="%(message)s"
)


class CreateCard(Static):
    """Special selectable card for creating a new instance."""

    def __init__(self):
        super().__init__()
        self.inst = {"name": "Create"}
        self.title = "➕  Create a New Instance"
        self.subtitle = "Start a brand-new Tabsdata instance"
        self.border_color = "#38bdf8"  # light blue
        self.is_selected = False
        self.add_class("create")

    def render(self):
        header = f"[{self.border_color}]{self.title}[/]"
        body = f"{self.subtitle}"

        content = f"{header}\n{body}"

        if self.is_selected:
            return f"[bold white on #3b3b4f]{content}[/]"
        return content


class ExitCard(Static):
    """Special selectable card for exiting the quickstart."""

    def __init__(self):
        super().__init__()
        self.inst = {"name": "Exit"}
        self.title = "🚪  Exit Quickstart"
        self.subtitle = "Return to your shell"
        self.border_color = "#f87171"  # soft red
        self.is_selected = False
        self.add_class("exit")

    def render(self):
        header = f"[{self.border_color}]{self.title}[/]"
        body = f"{self.subtitle}"

        content = f"{header}\n{body}"

        if self.is_selected:
            return f"[bold white on #3b3b4f]{content}[/]"
        return content


class InstanceCard(Static):
    """Clickable/selectable card representing an instance."""

    def __init__(self, inst: dict):
        super().__init__()
        self.inst = inst
        self.inst_name = inst["name"]
        self.status = inst["status"]
        self.is_selected = False
        if self.status == "Running":
            self.add_class("running")
        else:
            self.add_class("stopped")

    def render(self):
        border = "green" if self.status == "Running" else "red"

        header = (
            f"[{border}]{self.inst_name}[/]  "
            f"{'● Running' if self.status == 'Running' else '○ Not running'}"
        )

        if self.status == "Running":
            line1 = f"running on → ext: {self.inst['arg_ext']}"
            line2 = f"running on → int: {self.inst['arg_int']}"
        else:
            line1 = f"configured on → ext: {self.inst['cfg_ext']}"
            line2 = f"configured on → int: {self.inst['cfg_int']}"

        content = f"{header}\n{line1}\n{line2}"

        if self.is_selected:
            return f"[bold white on #3b3b4f]{content}[/]"
        else:
            return content


class InstanceSelector(App):
    CSS = """
    Screen {
        background: black;
    }

    #list {
        height: 100%;
    }

    ExitCard {
        padding: 1 1;
        border: round red;
        width: 40;
    }

    CreateCard {
        padding: 1 1;
        border: round blue;
        width: 40;
    }

    InstanceCard {
        padding: 1 1;
        border: round #404040;
        width: 40;
    }

    InstanceCard.running {
        border: round green;
    }

    InstanceCard.stopped {
        border: round red;
    }
    """

    def __init__(self, instances=None, existing_only=True):
        super().__init__()
        if instances is None:
            self.instances = find_instances()
        else:
            self.instances = instances
        self.existing_only = existing_only
        if len(self.instances) == 0:
            self.existing_only = False
        self.cards: list[InstanceCard] = []
        self.index = 0
        self.selected: InstanceCard | None = None

    def compose(self) -> ComposeResult:
        # 👇 use a scrollable container
        yield VerticalScroll(id="list")

    def on_mount(self) -> None:
        container = self.query_one("#list")
        if self.existing_only == False:
            create_card = CreateCard()
            self.cards.append(create_card)
            container.mount(create_card)

        for inst in self.instances:
            card = InstanceCard(inst)
            self.cards.append(card)
            container.mount(card)

        if self.existing_only == False:
            exit_card = ExitCard()
            self.cards.append(exit_card)
            container.mount(exit_card)

        if self.cards:
            self.cards[0].is_selected = True
            self.cards[0].refresh()
            # optional: focus first card so keyboard focus is “inside”
            self.cards[0].focus()

    def update_selection(self, new_index: int):
        if not self.cards:
            return

        self.cards[self.index].is_selected = False
        self.cards[self.index].refresh()

        self.index = new_index
        self.cards[self.index].is_selected = True
        # 👇 this now actually scrolls because parent is scrollable
        self.cards[self.index].scroll_visible()
        self.cards[self.index].refresh()

    async def on_key(self, event: events.Key) -> None:
        logging.info(event.key)
        if not self.cards:
            return

        if event.key in ["ctrl+c", "escape", "ctrl+q"]:
            logging.info(event.key)
            await self.action_quit()
            return
        
        if event.key ==  "escape":
            self.action_quit()
            return

        key = event.key

        if key == "down":
            if self.index < len(self.cards) - 1:
                self.update_selection(self.index + 1)
                event.stop()
        elif key == "up":
            if self.index > 0:
                self.update_selection(self.index - 1)
                event.stop()
        elif key == "enter":
            inst = self.cards[self.index].inst
            self.selected = inst
            await self.action_quit()
            event.stop()


def run_instance_selector(instances=None):
    app = InstanceSelector(instances)
    app.run()
    return app.selected


if __name__ == "__main__":
    print(run_instance_selector())
