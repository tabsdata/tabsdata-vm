from pathlib import Path
import os
from os import listdir
from tdconsole.core.yaml_getter_setter import (
    get_yaml_value,
)
import psutil
from dataclasses import dataclass
from tdconsole.core.td_dataclasses import TabsdataInstance, FieldChange
from pathlib import Path
from typing import Optional, Dict, List, Union
from tdconsole.core.models import Instance
from textual.app import App


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


from tdconsole.core.models import Instance as InstanceRow  # avoid name clash

from tdconsole.core.models import Instance  # ORM model


def instance_name_to_instance(instance_name: str) -> Instance:
    """
    Build an Instance ORM object from filesystem state only.
    Does NOT interact with the database.
    """
    available_instances = find_tabsdata_instance_names()
    if instance_name not in available_instances and instance_name == "_Create_Instance":
        return Instance(
            name=instance_name,
            status="Not Created",
            cfg_ext="2457",
            cfg_int="2458",
            arg_ext="2457",
            arg_int="2458",
            public_ip="127.0.0.1",
            private_ip="127.0.0.1",
        )

    pid = find_instance_pid(instance_name)
    sockets = find_sockets(instance_name, pid)
    split_public_socket = sockets["arg_ext"].split(":")
    split_private_socket = sockets["arg_int"].split(":")
    public_ip = split_public_socket[0]
    public_port = split_public_socket[-1]
    private_ip = split_private_socket[0]
    private_port = split_private_socket[-1]

    return Instance(
        name=instance_name,
        pid=pid,
        status=sockets["status"],
        cfg_ext=sockets["cfg_ext"],
        cfg_int=sockets["cfg_int"],
        arg_ext=public_port,
        arg_int=private_port,
        public_ip=public_ip,
        private_ip=private_ip,
    )


def sync_filesystem_instances_to_db(app=None, session=None) -> list[Instance]:
    """
    Sync filesystem state into the DB using ORM models created by instance_name_to_instance.
    Returns the ORM models from the DB after upsert.
    """
    if session is not None:
        pass
    elif hasattr(app, "session"):
        session = app.session
    else:
        raise TypeError(f"Expected either an app or session to be provided")

    instance_names = find_tabsdata_instance_names()

    with session as session:
        working_instance = session.query(Instance).filter_by(working=True).first()
        for name in instance_names:
            # Instance from filesystem only
            fs_instance = instance_name_to_instance(name)
            if (
                working_instance is not None
                and fs_instance.name == working_instance.name
            ):
                fs_instance.working = True

            # Try to find existing record in DB
            db_instance = session.query(Instance).filter_by(name=name).first()

            if db_instance is None:
                # Create if not found
                session.add(fs_instance)
            else:
                session.merge(fs_instance)

        session.query(Instance).filter(~Instance.name.in_(instance_names)).delete(
            synchronize_session=False
        )

        session.commit()

        # Return database versions of instances
        instances_in_db = session.query(Instance).order_by(Instance.name).all()

    return instances_in_db


from sqlalchemy import and_, or_


def query_session(session, model, limit=None, *conditions, **filters):
    query = session.query(model)
    if filters:
        query = query.filter_by(**filters)
    if conditions:
        query = query.filter(*conditions)

    if limit is not None:
        query = query.limit(limit)

    if query.all() == []:
        return None
    elif len(query.all()) == 1:
        return query.all()[0]

    return query.all()


# def manage_working_instance(session, instance):
#     # Make sure we have a session-attached object
#     db_instance = session.merge(instance)

#     # Clear working on all others
#     (
#         session.query(Instance)
#         .filter(Instance.name != db_instance.name, Instance.working.is_(True))
#         .update({Instance.working: False}, synchronize_session=False)
#     )

#     db_instance.working = True
#     session.commit()
#     return True


# session = start_session()
# sync_filesystem_instances_to_db(session)
# x = query_session(session, Instance, status="Running")
# for inst in x:
#     print({c.name: getattr(inst, c.name) for c in inst.__table__.columns})


# def print_all_instance_data(session):
#     sync_filesystem_instances_to_db(session=session)
#     x = query_session(session, Instance)
#     for inst in x:
#         print({c.name: getattr(inst, c.name) for c in inst.__table__.columns})
