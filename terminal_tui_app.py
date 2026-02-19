from __future__ import annotations

import asyncio
import os
import shlex
from pathlib import Path

from textual.app import App, ComposeResult
from textual.containers import Vertical
from textual.geometry import Offset, Region, Spacing
from textual.widgets import Footer, Header, Input, RichLog, Static
from textual_autocomplete._autocomplete import DropdownItem, TargetState

from src.tdconsole.core.construct_command_trie import CliAutoComplete, Node


class BottomAwareCliAutoComplete(CliAutoComplete):
    """Place the dropdown above the input when bottom space is limited."""

    def _align_to_target(self) -> None:
        x, y = self.target.cursor_screen_offset
        dropdown = self.option_list
        width, height = dropdown.outer_size
        region = self.screen.scrollable_content_region

        below_space = max(0, region.bottom - (y + 1))
        above_space = max(0, y - region.y)
        show_above = below_space < min(height, 4) and above_space > below_space
        desired_y = y - height if show_above else y + 1

        x, y, _width, _height = Region(x - 1, desired_y, width, height).constrain(
            "inside",
            "none",
            Spacing.all(0),
            region,
        )
        self.absolute_offset = Offset(x, y)


class TerminalLikeApp(App[None]):
    TITLE = "Terminal TUI"
    SUB_TITLE = "Enter commands and press Enter"

    CSS = """
    Screen {
        layout: vertical;
    }

    #root {
        height: 1fr;
    }

    #prompt {
        height: 1;
        padding: 0 1;
        background: $surface;
        color: $text-muted;
    }

    #log {
        height: 1fr;
        border: round $accent;
    }

    #command-input {
        dock: bottom;
    }
    """

    BINDINGS = [
        ("ctrl+c", "quit", "Quit"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.cwd = Path.cwd()
        self.root = self._build_cli_tree()
        self.prompt_widget: Static | None = None
        self.log_widget: RichLog | None = None
        self.input_widget: Input | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="root"):
            yield Static("", id="prompt")
            yield RichLog(id="log", wrap=True, highlight=True, markup=False)
        input_widget = Input(
            placeholder="Type a command and press Enter", id="command-input"
        )
        yield input_widget
        yield BottomAwareCliAutoComplete(
            input_widget, candidates=self.candidates_callback
        )
        yield Footer()

    def on_mount(self) -> None:
        self.prompt_widget = self.query_one("#prompt", Static)
        self.log_widget = self.query_one("#log", RichLog)
        self.input_widget = self.query_one("#command-input", Input)
        self._refresh_prompt()
        self.input_widget.focus()
        self._log_line("Built-ins: cd, clear, pwd, exit")

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        command = event.value.strip()
        event.input.value = ""
        if not command:
            return

        self._log_line(f"$ {command}")
        await self._run_command(command)
        self._refresh_prompt()

    async def _run_command(self, command: str) -> None:
        if command == "clear":
            self.log_widget.clear()
            return
        if command in {"exit", "quit"}:
            self.exit()
            return
        if command == "pwd":
            self._log_line(str(self.cwd))
            return
        if command.startswith("cd"):
            self._handle_cd(command)
            return

        process = await asyncio.create_subprocess_shell(
            command,
            cwd=str(self.cwd),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            env=os.environ.copy(),
        )

        assert process.stdout is not None
        while True:
            line = await process.stdout.readline()
            if not line:
                break
            self._log_line(line.decode(errors="replace").rstrip("\n"))

        return_code = await process.wait()
        if return_code != 0:
            self._log_line(f"[exit code: {return_code}]")

    def _handle_cd(self, command: str) -> None:
        parts = shlex.split(command)
        target_raw = parts[1] if len(parts) > 1 else "~"
        target = Path(target_raw).expanduser()
        if not target.is_absolute():
            target = (self.cwd / target).resolve()

        if not target.exists():
            self._log_line(f"cd: no such file or directory: {target_raw}")
            return
        if not target.is_dir():
            self._log_line(f"cd: not a directory: {target_raw}")
            return

        self.cwd = target

    def _refresh_prompt(self) -> None:
        if self.prompt_widget is not None:
            self.prompt_widget.update(f"{self.cwd} $")

    def _log_line(self, text: str) -> None:
        if self.log_widget is not None:
            self.log_widget.write(text)

    def candidates_callback(self, state: TargetState) -> list[DropdownItem]:
        items = self._pull_command_suggestions(self.root, state.text)
        return [DropdownItem(i) for i in items]

    def _build_cli_tree(self) -> Node:
        root = Node("root")
        td_node = Node(name="td")
        root.add_child(td_node)

        table = td_node.add_child(Node("table"))
        sample = table.add_child("sample")
        schema = table.add_child("schema")

        sample.add_child(["--coll", "--name"])
        schema.add_child(["--coll", "--name"])

        colls = root.recur_search("--coll")
        for node in colls:
            node.add_child(["a", "b", "c"])
            node.parameter = True
            for child in node.children:
                child.parameter_arg = True

        names = root.recur_search("--name")
        for node in names:
            node.add_child(["d", "e", "f"])
            node.parameter = True
            for child in node.children:
                child.parameter_arg = True

        return root

    def _pull_command_suggestions(self, root: Node, text: str) -> list[str]:
        try:
            split_text = shlex.split(text)
        except ValueError:
            split_text = text.split(" ")

        cursor = root
        children = cursor.children
        param_list = []

        for word in split_text:
            if not word:
                continue
            found_child = cursor.get_child(word)
            if not found_child:
                if cursor.parameter is True:
                    return []
                break
            if found_child.parameter is True:
                param_list = cursor.children
            if found_child.parameter_arg is True:
                param_list = cursor.parent.children
                cursor = cursor.parent
            else:
                cursor = found_child
            children = cursor.children

        results = children
        if len(children) == 0 and len(param_list) > 0:
            results = param_list

        names = [node.name for node in results]
        existing_params = [token for token in split_text if token.startswith("--")]
        return [name for name in names if name not in existing_params]


if __name__ == "__main__":
    TerminalLikeApp().run()
