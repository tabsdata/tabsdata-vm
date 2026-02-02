from sqlalchemy.orm import Session
from tabsdata.api.tabsdata_server import TabsdataServer

from tdconsole.core.models import Collection, Function, Instance, Table
from tdconsole.core.subprocess_runner import run_bash


def initialize_tabsdata_server_connection(app):
    instance = app.working_instance
    try:
        if instance is not None:
            socket = instance.ext_socket
            username = "admin"
            password = "tabsdata"
            role = "sys_admin"
            server = TabsdataServer(socket, username, password, role)
        else:
            server = None
    except:
        server = None

    if server:
        try:
            run_bash(
                f"td login --server {socket} --user {username} --role {role} --password {password}"
            )
            app.notify("Login Successful")
        except:
            app.notify("Login Failed")
    return server


def pull_all_collections(app):
    server = app.tabsdata_server
    server: TabsdataServer
    collections = server.list_collections()
    return collections


def pull_functions_from_collection(app, collection):
    server = app.tabsdata_server
    server: TabsdataServer
    functions = server.list_functions(collection)
    return functions


def pull_tables_from_collection(app, collection):
    server = app.tabsdata_server
    server: TabsdataServer
    tables = server.list_tables(collection)
    return tables


def check_server_status(app, server: TabsdataServer = None):
    if not server:
        server = app.tabsdata_server

    if not server:
        return False

    try:
        auth_status = server.auth_info()
        return True
    except:
        False


def sync_instance_to_db(app):
    session = app.session
    session: Session
    server = app.tabsdata_server
    instance = app.working_instance
    server: TabsdataServer
    server_status = check_server_status(app, server)

    if not server_status:
        return None

    collections = pull_all_collections(app)

    if len(collections) == 0:
        return None

    data = {
        i.name: {
            "tables": pull_tables_from_collection(app, i.name),
            "functions": pull_functions_from_collection(app, i.name),
        }
        for i in collections
    }

    instance = session.query(Instance).filter_by(name=instance.name).one()
    instance.collections.clear()
    session.commit()

    if True:
        for name, v in data.items():
            c = Collection(name=name, instance=instance)
            c.tables = [Table(name=getattr(t, "name")) for t in v["tables"]]
            c.functions = [Function(name=getattr(f, "name")) for f in v["functions"]]
            session.add(c)
        session.commit()
