import shlex

from textual.app import App, ComposeResult
from textual.widgets import Input
from textual_autocomplete import AutoComplete
from textual_autocomplete._autocomplete import DropdownItem, TargetState


class Node:
    def __repr__(self):
        return f"{self.name!r}"
        return f"Node(name={self.name!r}, children={self.children})"

    def __init__(
        self, name, parent=None, children=None, parameter=False, parameter_arg=False
    ):
        self.name = name
        self.parent = parent
        self.children = children if children is not None else []
        self.parameter = parameter
        self.parameter_arg = parameter_arg

    def add_child(self, child):
        if isinstance(child, list):
            child = [self.convert_str_to_node(i) for i in child]
            self.children.extend(child)
        else:
            child = self.convert_str_to_node(child)
            self.children.append(child)
        return child

    def convert_str_to_node(self, child: str):
        if isinstance(child, str):
            child = Node(child)

        if not child.parent:
            child.parent = self
        return child

    def get_child(self, child_name):
        for i in self.children:
            if i.name == child_name:
                return i
        return None

    def recur_search(self, name):
        results = []
        cursor = self
        children = cursor.children
        if len(children) == 0:
            return []
        else:
            for i in children:
                if i.name == name:
                    results.append(i)
                new_search = i.recur_search(name)
                results.extend(new_search)
        return results

    def get_colls(self):
        return ["a", "b", "c"]

    def get_names(self):
        return ["c", "d", "f"]


class CliAutoComplete(AutoComplete):
    def get_search_string(self, state: TargetState) -> str:
        return state.text.split(" ")[-1]

    def should_show_dropdown(self, search_string: str) -> bool:
        return True

    def apply_completion(self, completion, state: TargetState) -> None:
        val = str(getattr(completion, "main", completion))

        t = state.text
        if t.endswith(" "):
            new = t + val + " "
        else:
            parts = t.split(" ")
            parts[-1] = val
            new = " ".join(parts) + " "

        self.target.value = new
        self.target.cursor_position = len(new)

    def post_completion(self) -> None:
        self._handle_target_update()


class DynamicDataApp(App[None]):
    BINDINGS = [
        ("ctrl+c", "quit", "Quit"),
        ("ctrl+b", "go_back", "Go Back"),
    ]

    def __init__(self):
        self.root = self.build_cli_tree()  # click.Command tree
        super().__init__()

    def compose(self) -> ComposeResult:
        input_widget = Input()
        yield input_widget
        yield CliAutoComplete(input_widget, candidates=self.candidates_callback)

    def candidates_callback(self, state: TargetState) -> list[DropdownItem]:
        items = self.pull_command_suggestions(self.root, state.text)
        return [DropdownItem(i) for i in items]

    def build_cli_tree(self):
        root = Node("root")

        td_node = Node(name="td")

        root.add_child(td_node)
        table = td_node.add_child(Node("table"))
        sample = table.add_child("sample")
        schema = table.add_child("schema")

        sample.add_child(["--coll", "--name"])
        schema.add_child(["--coll", "--name"])

        colls = root.recur_search("--coll")
        for i in colls:
            i.add_child(["a", "b", "c"])
            i.parameter = True
            for child in i.children:
                child.parameter_arg = True

        names = root.recur_search("--name")
        for i in names:
            i.add_child(["d", "e", "f"])
            i.parameter = True
            for child in i.children:
                child.parameter_arg = True

        return root

    def pull_command_suggestions(self, root, text):
        split_x = shlex.split(text)
        cursor = root
        children = cursor.children
        param_list = []

        for i in range(len(split_x)):
            word = split_x[i]
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
        results = [i.name for i in results]
        existing_params = [i for i in split_x if i.startswith("--")]
        results = [i for i in results if i not in existing_params]

        return results


if __name__ == "__main__":
    if True:
        DynamicDataApp().run()
