from textual.screen import Screen
from tdconsole.textual_assets import textual_screens
from tdconsole.core.find_instances import instance_name_to_instance
import os
from pathlib import Path


def process_response(screen: Screen, label=None):
    app = screen.app
    screen_name = type(screen).__name__

    # Ensure we have a place to track the current flow
    if not hasattr(app, "flow_mode"):
        app.flow_mode = None

    # 1. Initial mount from App
    if label == "_mount":
        app.flow_mode = None
        app.push_screen(textual_screens.HomeTabbedScreen())
        return

    # 2. From the main GettingStartedScreen menu
    if screen_name == "InstanceManagementScreen":
        if label == "Bind An Instance":
            app.flow_mode = "bind"
            instances = app.app_query_session("instances")
            app.push_screen(
                textual_screens.InstanceSelectionScreen(instances=instances)
            )
            return

        if label == "Start an Instance":
            app.flow_mode = "start"
            # only instances that are not running
            instances = app.app_query_session("instances", status="Not Running")
            # for inst in instances:
            #     print({c.name: getattr(inst, c.name) for c in inst.__table__.columns})
            app.push_screen(
                textual_screens.InstanceSelectionScreen(instances=instances)
            )
            return

        if label == "Stop An Instance":
            app.flow_mode = "stop"
            # only running instances
            instances = app.app_query_session("instances", status="Running")
            app.push_screen(
                textual_screens.InstanceSelectionScreen(instances=instances)
            )
            return

        if label == "Exit":
            app.exit()
            return

        # fall through if none matched
        return

    if screen_name == "MainScreen":
        if label == "Instance Management":
            app.push_screen(textual_screens.InstanceManagementScreen())
            return

        if label == "Asset Management":
            if Path.home() == Path.cwd():
                app.notify(
                    "❌ Cannot scan root directory! Please run `tdconsole` in a more specific directory to avoid scanning your entire home path.",
                    severity="error",
                )
            else:
                app.push_screen(textual_screens.PyFileTreeScreen(root=os.getcwd()))
            return

        if label == "Exit":
            app.exit()
            return

    # 3. From InstanceSelectionScreen
    if screen_name == "InstanceSelectionScreen":
        # label is always a string from the ListItem: instance name or "_Create_Instance"
        if app.flow_mode == "stop":
            result = app.app_query_session("instances", limit=1, name=label)
            app.push_screen(textual_screens.StopInstance(instance=result))
            return
        if label == "_Create_Instance":
            # Build a brand new Instance obj (not in DB yet)
            instance = instance_name_to_instance("_Create_Instance")
            # Make sure status is something like "Not Created"
            instance.status = "Not Created"
        else:
            # Lookup existing instance in DB by name
            result = app.app_query_session("instances", limit=1, name=label)
            # If you changed app_query_session to always return list:
            instance = result if result else None

        if instance is None:
            # You can show an error screen or go back instead of crashing
            # For now, just bail
            return

        app.selected_instance = instance
        # Now always pass an Instance object into PortConfigScreen
        app.push_screen(textual_screens.PortConfigScreen(instance))
        return

    # 4. From PortConfigScreen
    if screen_name == "PortConfigScreen":
        # Here I assume PortConfigScreen calls handle_api_response(self, instance)
        # so `label` is an instance object with arg_ext/arg_int set.
        instance = label
        app.selected_instance = instance

        if app.flow_mode == "bind":
            # This screen runs the sequential tasks (prepare, bind ports, start, status)
            app.push_screen(textual_screens.BindAndStartInstance(instance))
            return

        if app.flow_mode == "start":
            # This screen runs the sequential tasks (prepare, bind ports, start, status)
            app.push_screen(textual_screens.StartInstance(instance))
            return

    # 5. From BindAndStartInstance (sequential tasks screen)
    if screen_name in ["BindAndStartInstance", "StopInstance", "StartInstance"]:
        # When the tasks screen finishes it should call handle_api_response(self)
        # and we just take the user back to the main menu or wherever
        app.flow_mode = None
        app.push_screen(textual_screens.HomeTabbedScreen())
        return
    app.push_screen(textual_screens.BSOD())
