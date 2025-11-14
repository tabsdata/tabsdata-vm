from typing import Optional

from rich.text import Text
from textual.app import App, ComposeResult
from textual.widgets import Tree
from textual.widgets.tree import TreeNode


class TreeApp(App):
    CSS = """
    Screen {
        align: center middle;
        background: black;
    }

    Tree {
        color: #cccccc;
        background: black;
    }

    Tree > .tree--cursor {
        background: black;
        color: white;
    }
    """

    selected_value: Optional[str] = None

    def compose(self) -> ComposeResult:
        tree: Tree[str] = Tree(Text("Tabsdata Instances", style="bold cyan"))
        tree.root.expand()

        # prod (collection)
        prod_label = Text("prod", style="bold orange")
        prod_label.append(" [collection]", style="bold orange")
        prod: TreeNode = tree.root.add(prod_label, expand=True)

        prod.add_leaf(Text("postres_pub [function]", style="gray"))
        prod.add_leaf(Text("s3_sub [function]", style="gray"))

        # staging (collection)
        staging_label = Text("staging", style="bold orange")
        staging_label.append(" [collection]", style="bold orange")
        staging: TreeNode = tree.root.add(staging_label, expand=True)

        staging.add_leaf(Text("postgres_pub_test [function]", style="gray"))
        staging.add_leaf(Text("s3_sub_test [function]", style="gray"))

        yield tree

    async def on_tree_node_selected(self, event: Tree.NodeSelected):
        self.selected_value = str(event.node.label)
        await self.action_quit()

    async def on_key(self, event):
        if event.key == "ctrl+c":
            await self.action_quit()


def pick_instance() -> Optional[str]:
    app = TreeApp()
    try:
        app.run()
    except KeyboardInterrupt:
        # Ctrl C while Textual loads or before UI fully starts
        return None
    return app.selected_value


if __name__ == "__main__":
    value = pick_instance()
    print("Picker returned:", value)
