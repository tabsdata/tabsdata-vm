from textual.app import App, ComposeResult
from textual.widgets import Static
from textual.containers import Vertical
from textual import events

from tdtui.core.find_instances import main as find_instances


import logging
import os


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
            # Only wrap in style tags when selected
            return f"[bold white on #3b3b4f]{content}[/]"
        else:
            # No extra tags when not selected
            return content


class InstanceSelector(App):
    CSS = """

    ExitCard {
        width: auto;               /* size to content, not 100% */
        padding: 1 1;
        border: round #404040;
        width: 40; 
        border: round red;
    }

    CreateCard {
        width: auto;               /* size to content, not 100% */
        padding: 1 1;
        border: round #404040;
        width: 40; 
        border: round blue;
    }

    InstanceCard {
        width: auto;               /* size to content, not 100% */
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

    def __init__(self, instances=None):
        super().__init__()
        if instances == None:
            self.instances = find_instances()
        else:
            self.instances = instances
        self.cards: list[InstanceCard] = []
        self.index = 0
        self.selected: InstanceCard = None
        self.log("started1234")

    def compose(self) -> ComposeResult:
        yield Vertical(id="list")

    def on_mount(self) -> None:
        container = self.query_one("#list")

        create_card = CreateCard()
        self.cards.append(create_card)
        container.mount(create_card)

        # build cards
        for inst in self.instances:
            card = InstanceCard(inst)
            self.cards.append(card)
            container.mount(card)

        exit_card = ExitCard()
        self.cards.append(exit_card)
        container.mount(exit_card)

        if self.cards:
            self.cards[0].is_selected = True
            self.cards[0].refresh()

    def update_selection(self, new_index: int):
        if not self.cards:
            return

        # unselect old
        self.cards[self.index].is_selected = False
        self.cards[self.index].refresh()

        # select new
        self.index = new_index
        self.cards[self.index].is_selected = True
        self.cards[self.index].scroll_visible()
        self.cards[self.index].refresh()

    async def on_key(self, event: events.Key) -> None:
        if not self.cards:
            return

        if event.key in ["ctrl+c", "escape", "ctrl+q"]:
            await self.action_quit()

        key = event.key

        if key == "down":
            if self.index < len(self.cards) - 1:
                self.update_selection(self.index + 1)

        elif key == "up":
            if self.index > 0:
                self.update_selection(self.index - 1)

        elif key == "enter":
            inst = self.cards[self.index].inst
            self.selected = inst
            await self.action_quit()
            # instance dict has "name", n


def run_instance_selector(instances=None):
    app = InstanceSelector(instances)
    app.run()
    return app.selected


if __name__ == "__main__":
    run_instance_selector()
