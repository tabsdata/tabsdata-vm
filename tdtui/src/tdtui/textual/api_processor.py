from textual.app import App, ComposeResult
from textual.screen import Screen
from textual.widgets import ListView, ListItem, Label
from pathlib import Path
import logging

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer


def process_response(screen: Screen, label=None):
    app = screen.app
    screen_name = type(app.screen).__name__
    if label == "Instance Management":
        app.push_screen("PortConfig")
    if label == "Bind An Instance":
        app.push_screen("InstanceSelection")
    if screen_name == "InstanceSelectionScreen":
        app.instance_name = label
        app.push_screen("PortConfig")
    if screen_name == "PortConfigScreen":
        app.push_screen("InstanceStartup")
    return
