from textual.app import App
from textual.widgets import Label


class ContentAlignApp(App):
    CSS = """#box1 {
    content-align: left top;
    background: red;
}

#box2 {
    content-align-horizontal: center;
    content-align-vertical: middle;
    background: green;
}

#box3 {
    content-align: right bottom;
    background: blue;
}

Label {
    width: 100%;
    height: 1fr;
    padding: 1;
    color: white;
}"""

    def compose(self):
        yield Label("With [i]content-align[/] you can...", id="box1")
        yield Label("...[b]Easily align content[/]...", id="box2")
        yield Label("...Horizontally [i]and[/] vertically!", id="box3")


if __name__ == "__main__":
    app = ContentAlignApp()
    app.run()
