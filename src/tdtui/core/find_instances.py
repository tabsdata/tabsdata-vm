from pathlib import Path
import os
from os import listdir
from tdtui.core.yaml_getter_setter import (
    get_yaml_value,
)
import psutil
from dataclasses import dataclass
from tdtui.core.td_dataclasses import TabsdataInstance, FieldChange
from pathlib import Path
from typing import Optional, Dict, List, Union
from tdtui.core.models import Instance
from tdtui.core.db import start_session


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


def resync_app_instance_store(app):
    instances = pull_all_tabsdata_instance_data()
    app.instances = instances
    return True


def pull_all_tabsdata_instance_data(app) -> list[TabsdataInstance]:
    instances: list[TabsdataInstance] = []
    for name in find_tabsdata_instance_names():
        pid = find_instance_pid(name)
        sockets = find_sockets(name, pid)

        instances.append(instance_name_to_instance(name))
    return instances


from tdtui.core.models import Instance as InstanceRow  # avoid name clash

from tdtui.core.models import Instance  # ORM model


def instance_name_to_instance(instance_name: str) -> Instance:
    """
    Build an Instance ORM object from filesystem state only.
    Does NOT interact with the database.
    """
    available_instances = find_tabsdata_instance_names()
    if instance_name not in available_instances:
        raise ValueError(f"No Tabsdata instance exists with name '{instance_name}'")

    pid = find_instance_pid(instance_name)
    sockets = find_sockets(instance_name, pid)

    return Instance(
        name=instance_name,
        pid=pid,
        status=sockets["status"],
        cfg_ext=sockets["cfg_ext"],
        cfg_int=sockets["cfg_int"],
        arg_ext=sockets["arg_ext"],
        arg_int=sockets["arg_int"],
    )


def sync_filesystem_instances_to_db(app) -> list[Instance]:
    """
    Sync filesystem state into the DB using ORM models created by instance_name_to_instance.
    Returns the ORM models from the DB after upsert.
    """
    instance_names = find_tabsdata_instance_names()

    with app.session as session:
        for name in instance_names:
            # Instance from filesystem only
            fs_instance = instance_name_to_instance(name)

            # Try to find existing record in DB
            db_instance = session.query(Instance).filter_by(name=name).first()

            if db_instance is None:
                # Create if not found
                session.add(fs_instance)
            else:
                # Update existing with latest filesystem values
                db_instance.pid = fs_instance.pid
                db_instance.status = fs_instance.status
                db_instance.cfg_ext = fs_instance.cfg_ext
                db_instance.cfg_int = fs_instance.cfg_int
                db_instance.arg_ext = fs_instance.arg_ext
                db_instance.arg_int = fs_instance.arg_int

        session.commit()

        # Return database versions of instances
        instances_in_db = session.query(Instance).order_by(Instance.name).all()

    if app is not None:
        app.instances = instances_in_db

    return instances_in_db
