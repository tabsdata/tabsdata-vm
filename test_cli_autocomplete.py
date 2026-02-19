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


x = "td table sample --coll a --name s"

split_x = x.split(" ")
cursor = root
children = cursor.children
active_coll = None
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
print(results)
