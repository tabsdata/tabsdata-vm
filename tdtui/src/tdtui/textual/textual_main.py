from textual.app import App, ComposeResult
from textual.screen import Screen
from textual.widgets import Static, Button, ListView, ListItem, Label, ContentSwitcher
from textual.containers import Vertical, Horizontal
from textual import on


class TabsdataStatus(Static):
    """Top component that always shows the active Tabsdata instance."""

    def __init__(self, instance_name: str = "demo", **kwargs):
        super().__init__(**kwargs)
        self.instance_name = instance_name

    def compose(self) -> ComposeResult:
        yield Label(f"📦 Active Tabsdata instance: {self.instance_name}")


class MenuList(ListView):
    """ListView that hands focus to the footer when you press Down on the last item."""

    def key_down(self) -> None:
        # If we are on the last item, move focus to footer instead of going nowhere
        if self.index is not None and self.index == len(self.children) - 1:
            # Ask the current screen to move focus to the footer
            self.app.screen.action_focus_footer()
        else:
            super().key_down()


class FooterBar(Horizontal):
    """Bottom bar with Back / Exit buttons."""

    def compose(self) -> ComposeResult:
        yield Button("Back", id="back")
        yield Button("Exit", id="exit")

    @on(Button.Pressed)
    def handle_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.app.screen.go_back()
        elif event.button.id == "exit":
            self.app.exit()

    def key_up(self) -> None:
        """Up arrow from the footer moves focus back into the main content."""
        self.app.screen.action_focus_main()


class MainMenu(Static):
    """One of the middle 'pages'."""

    def compose(self) -> ComposeResult:
        yield Label("Main menu")
        yield MenuList(
            ListItem(Label("Quickstart")),
            ListItem(Label("Advanced setup")),
        )

    @on(ListView.Selected)
    def on_selected(self, event: ListView.Selected) -> None:
        label = event.item.label.renderable
        if label == "Quickstart":
            self.app.screen.show_page("quickstart")
        elif label == "Advanced setup":
            self.app.screen.show_page("advanced")


class QuickstartPage(Static):
    """Another middle page."""

    def compose(self) -> ComposeResult:
        yield Label("Quickstart")
        yield MenuList(
            ListItem(Label("Use defaults")),
            ListItem(Label("Custom config")),
        )

    @on(ListView.Selected)
    def on_selected(self, event: ListView.Selected) -> None:
        # Do stuff, then maybe go back to main or another page
        self.app.screen.show_page("main")


class AdvancedPage(Static):
    def compose(self) -> ComposeResult:
        yield Label("Advanced config")
        yield MenuList(
            ListItem(Label("Edit raw config")),
            ListItem(Label("Danger zone")),
        )


class ShellScreen(Screen):
    """Single screen that wraps top / middle / bottom."""

    BINDINGS = [
        ("b", "focus_footer", "Focus Back / Exit"),
        ("m", "focus_main", "Focus main content"),
    ]

    def compose(self) -> ComposeResult:
        with Vertical():
            yield TabsdataStatus(id="status")
            yield ContentSwitcher(id="body")
            yield FooterBar(id="footer")

    def on_mount(self) -> None:
        body = self.query_one("#body", ContentSwitcher)

        # Mount your "pages" once
        body.mount(MainMenu(id="main"))
        body.mount(QuickstartPage(id="quickstart"))
        body.mount(AdvancedPage(id="advanced"))

        # Start on main
        body.current = "main"

        # Focus the initial page
        self.action_focus_main()

    # Navigation helpers the inner pages can call

    def show_page(self, page_id: str) -> None:
        body = self.query_one("#body", ContentSwitcher)
        body.current = page_id
        self.action_focus_main()

    def go_back(self) -> None:
        """Your custom 'back' logic – could be a stack or a simple rule."""
        body = self.query_one("#body", ContentSwitcher)
        if body.current != "main":
            body.current = "main"
        else:
            self.app.exit()
        self.action_focus_main()

    # Focus helpers

    def action_focus_footer(self) -> None:
        footer = self.query_one("#footer", FooterBar)
        # Focus the Back button in the footer
        self.set_focus(footer.query_one("#back", Button))

    def action_focus_main(self) -> None:
        body = self.query_one("#body", ContentSwitcher)
        page_id = body.current  # "main", "quickstart", "advanced"
        # Current page widget by id
        page = self.query_one(f"#{page_id}")
        # Focus the ListView inside that page
        list_view = page.query_one(ListView)
        self.set_focus(list_view)


class TabsdataApp(App):

    def on_mount(self) -> None:
        self.push_screen(ShellScreen())


if __name__ == "__main__":
    TabsdataApp().run()
