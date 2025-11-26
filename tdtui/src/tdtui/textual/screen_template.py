from textual.screen import Screen
from textual.app import ComposeResult
from textual.widgets import ListView, ListItem, Label


class IntermediateScreenTemplate(Screen):

    def __init__(self, id, choices):
        self.id = id
        self.choices = choices
    

    def compose(self) -> ComposeResult:
        yield Label("Quickstart intro")
        view_choices = [ListItem(Label(i)) for i in self.choices]
        yield ListView(*view_choices,
        )

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        label = event.item.label.renderable
        next_screen = self.choices['label']
        if label in self.choices:
            self.app.push_screen("qs:summary")

