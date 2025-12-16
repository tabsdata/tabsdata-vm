from tabsdata.api.tabsdata_server import TabsdataServer


def initialize_tabsdata_server_connection(app):
    instance = app.working_instance
    if instance is not None:
        socket = instance.ext_socket
        username = "admin"
        password = "tabsdata"
        role = "sys_admin"
        server = TabsdataServer(socket, username, password, role)
        return server
    else:
        return None
