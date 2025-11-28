from pathlib import Path
import os
from os import listdir
from tdtui.core.yaml_getter_setter import (
    get_yaml_value,
)
import psutil
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict, List, Union


@dataclass
class TabsdataInstance:
    name: str
    pid: Optional[str]
    status: str
    cfg_ext: Optional[str]
    cfg_int: Optional[str]
    arg_ext: Optional[str]
    arg_int: Optional[str]

    def to_dict(self) -> Dict[str, str | None]:
        return {
            "name": self.name,
            "pid": self.pid,
            "status": self.status,
            "cfg_ext": self.cfg_ext,
            "cfg_int": self.cfg_int,
            "arg_ext": self.arg_ext,
            "arg_int": self.arg_int,
        }

    @property
    def is_running(self) -> bool:
        return bool(self.status == "Running")


def define_root(*parts):
    root = Path.home() / ".tabsdata"

    for part in parts:
        if part[0] == "/":
            part = part[1:]
        if not part:
            continue

        if isinstance(part, (list, tuple)):
            for sub in part:
                if sub:
                    root = root / Path(sub)
        else:
            root = root / Path(part)
    if root.exists() == False:
        return None

    return root


def find_tabsdata_instance_names():
    root = define_root("instances")
    matches = []

    if root == None:
        return matches

    for i in listdir(root):
        instance = root / i
        for current_root, dirs, files in os.walk(instance):
            if "tabsdata.db" in files:
                matches.append(i)
                break

    return matches


def find_instance_pid(instance_name: str):
    pid_path = define_root(
        "instances", instance_name, "/workspace/work/proc/regular/apiserver/work/pid"
    )
    if pid_path != None:
        pid = pid_path.read_text().strip() or None
    else:
        pid = None
    return pid


def find_sockets(instance_name: str, pid=None):
    cfg_path = define_root(
        "instances",
        instance_name,
        "/workspace/config/proc/regular/apiserver/config/config.yaml",
    )
    cfg_ext = get_yaml_value(path=cfg_path, key="addresses")
    cfg_int = get_yaml_value(path=cfg_path, key="internal_addresses")
    arg_ext = cfg_ext
    arg_int = cfg_int
    status = "Not Running"

    # if no arg is passed, try to find pid
    if pid == None:
        pid = find_instance_pid(instance_name)

    # if no pid then assume server not running
    if pid == None:
        return {
            "cfg_ext": cfg_ext,
            "cfg_int": cfg_int,
            "arg_ext": arg_ext,
            "arg_int": arg_int,
            "status": status,
        }
    else:
        # if no process, then not running
        try:
            p = psutil.Process(int(pid)).cmdline()
            status = "Running"
        except:
            pass

        # if no arg assume running external socket same as config
        try:
            arg_ext = p[p.index("--address") + 1]
        except:
            pass

        # if no arg assume running internal socket same as config
        try:
            arg_int = p[p.index("--internal-address") + 1]
        except:
            pass

    return {
        "status": status,
        "cfg_ext": cfg_ext,
        "cfg_int": cfg_int,
        "arg_ext": arg_ext,
        "arg_int": arg_int,
    }


def instance_name_to_tabsdata_instance(instance_name: str):
    available_instances = find_tabsdata_instance_names()
    if instance_name not in available_instances:
        raise ValueError(f"No Tabsdata instance exists with name '{instance_name}'")
    pid = find_instance_pid(instance_name)
    sockets = find_sockets(instance_name, pid)

    return TabsdataInstance(
        name=instance_name,
        pid=pid,
        status=sockets["status"],
        cfg_ext=sockets["cfg_ext"],
        cfg_int=sockets["cfg_int"],
        arg_ext=sockets["arg_ext"],
        arg_int=sockets["arg_int"],
    )


def pull_all_tabsdata_instance_data() -> list[TabsdataInstance]:
    instances: list[TabsdataInstance] = []
    for name in find_tabsdata_instance_names():
        pid = find_instance_pid(name)
        sockets = find_sockets(name, pid)

        instances.append(instance_name_to_tabsdata_instance(name))
    return instances


def convert_instance_name_to_TabsdataInstance(
    target: Union[str, TabsdataInstance],
    all_instances: Optional[List[TabsdataInstance]] = None,
) -> TabsdataInstance:
    if all_instances is None:
        all_instances = pull_all_tabsdata_instance_data()

    if isinstance(target, TabsdataInstance):
        pass
    elif isinstance(target, str):
        for inst in all_instances:
            if inst.name == target:
                target = inst
                break
    else:
        raise TypeError(
            f"Expected name to be a string or TabsdataInstance object, got {type(name).__name__}"
        )
