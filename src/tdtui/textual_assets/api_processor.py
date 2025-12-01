from textual.app import App, ComposeResult
from textual.screen import Screen
from textual.widgets import ListView, ListItem, Label
from pathlib import Path
import logging

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer
from tdtui.textual_assets.textual_screens import (
    PortConfigScreen,
    InstanceStartupTask,
    GettingStartedScreen,
    InstanceManagementScreen,
    MainScreen,
    InstanceSelectionScreen,
)


def process_response(screen: Screen, label=None):
    app = screen.app
    screen_name = type(app.screen).__name__

    if label == "_mount":
        app.push_screen(GettingStartedScreen())
    elif label == "Instance Management":
        pass
    elif label == "Bind An Instance":
        app.push_screen(InstanceSelectionScreen())
    elif screen_name == "InstanceSelectionScreen":
        app.instance_name = label
        app.push_screen(PortConfigScreen(label))
    elif screen_name == "PortConfigScreen":
        app.push_screen(InstanceStartupTask(label))
    elif screen_name == "GettingStartedScreen" and label == "Exit":
        app.exit()
    return
