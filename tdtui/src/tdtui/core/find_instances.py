from pathlib import Path
import os
from os import listdir
from tdtui.core.yaml_getter_setter import (
    get_yaml_value,
)
import psutil


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


def find_tabsdata_instances():
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
            "status": status
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


def main():
    instance_store = []
    instance_names = find_tabsdata_instances()
    for i in instance_names:
        instance_dict = {}
        pid = find_instance_pid(i)
        sockets = find_sockets(i, pid)

        instance_dict["name"] = i
        instance_dict["pid"] = pid
        instance_dict.update(sockets)
        instance_store.append(instance_dict)
    return instance_store


if __name__ == "__main__":
    x = main()
    for i in x:
        print(i)
