import json
import os
from os import listdir
from pathlib import Path
from urllib.parse import urlparse

import psutil

from tdconsole.core.models import Instance
from tdconsole.core.yaml_getter_setter import (
    get_yaml_value,
)

REMOTE_INSTANCE_PREFIX = "remote@"


def is_remote_instance_name(name: str | None) -> bool:
    return bool(name) and str(name).startswith(REMOTE_INSTANCE_PREFIX)


def make_remote_instance_name(host: str, port: str | int) -> str:
    return f"{REMOTE_INSTANCE_PREFIX}{host}:{port}"


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


def instance_name_to_instance(instance_name: str) -> Instance:
    """
    Build an Instance ORM object from filesystem state only.
    Does NOT interact with the database.
    """
    available_instances = find_tabsdata_instance_names()
    if is_remote_instance_name(instance_name):
        remote_target = instance_name.removeprefix(REMOTE_INSTANCE_PREFIX)
        host = remote_target
        port = "2457"
        if ":" in remote_target:
            host, port = remote_target.rsplit(":", 1)
        return Instance(
            name=instance_name,
            status="Remote",
            cfg_ext=port,
            cfg_int="2458",
            arg_ext=port,
            arg_int="2458",
            public_ip=host,
            private_ip=host,
        )

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
        cfg_ext=sockets["cfg_ext"].split(":")[-1],
        cfg_int=sockets["cfg_int"].split(":")[-1],
        arg_ext=public_port,
        arg_int=private_port,
        public_ip=public_ip,
        private_ip=private_ip,
    )


def resolve_working_instance(app=None, session=None):

    if session is not None:
        pass
    elif hasattr(app, "session"):
        session = app.session
    else:
        raise TypeError("Expected either an app or session to be provided")

    current_td_login = resolve_login_credentials()
    current_session_url, current_session_port = (
        current_td_login["url"],
        current_td_login["port"],
    )

    current_working_instance = (
        session.query(Instance)
        .filter_by(status="Running", arg_ext=current_session_port)
        .first()
    )
    if current_working_instance:
        working_instance = current_working_instance
    elif session.query(Instance).filter_by(working=True, status="Running").first():
        working_instance = session.query(Instance).filter_by(working=True).first()
    elif session.query(Instance).filter_by(working=True, status="Remote").first():
        working_instance = (
            session.query(Instance).filter_by(working=True, status="Remote").first()
        )
    else:
        working_instance = None
    return working_instance


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
        raise TypeError("Expected either an app or session to be provided")

    instance_names = find_tabsdata_instance_names()

    working_instance = resolve_working_instance(app, session)

    for name in instance_names:
        # Instance from filesystem only
        fs_instance = instance_name_to_instance(name)
        if working_instance is not None and fs_instance.name == working_instance.name:
            fs_instance.working = True
        else:
            fs_instance.working = False

        # Try to find existing record in DB
        db_instance = session.query(Instance).filter_by(name=name).first()

        if db_instance is None:
            # Create if not found
            session.add(fs_instance)
        else:
            # Preserve UI-managed settings that are not discoverable from filesystem state.
            fs_instance.use_https = db_instance.use_https
            fs_instance.https_cert_path = getattr(db_instance, "https_cert_path", None)
            fs_instance.https_cert_mode = getattr(db_instance, "https_cert_mode", None)
            session.merge(fs_instance)

    # Keep remote instances that are not represented on the local filesystem.
    missing_local_instances = session.query(Instance).filter(
        ~Instance.name.in_(instance_names),
        ~Instance.name.like(f"{REMOTE_INSTANCE_PREFIX}%"),
    )
    missing_local_instances.delete(synchronize_session=False)
    if hasattr(app, "working_instance"):
        working_instance = app.working_instance
        if hasattr(working_instance, "name"):
            working_instance_name = working_instance.name
            db_instance = (
                session.query(Instance).filter_by(name=working_instance_name).first()
            )
            if db_instance is None or db_instance.status == "Not Running":
                app.working_instance = None

    session.commit()

    # Return database versions of instances
    instances_in_db = session.query(Instance).order_by(Instance.name).all()

    return instances_in_db


def query_session(session, model, limit=None, *conditions, **filters):
    query = session.query(model)
    if filters:
        query = query.filter_by(**filters)
    if conditions:
        query = query.filter(*conditions)

    if limit is not None:
        query = query.limit(limit)

    results = query.all()
    if results == []:
        return None
    if len(results) == 1:
        return results[0]

    return results


def resolve_login_credentials(app=None):
    json_path = os.path.expanduser("~/.tabsdata/connection.json")
    url = json.load(open(json_path))["url"] if os.path.exists(json_path) else None
    port = urlparse(url).port
    if app:
        app.working_url = url
        app.working_port = port
    return {"url": url, "port": port}
