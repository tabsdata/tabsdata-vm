from tdconsole.textual_assets.screens.base import (
    ListScreenTemplate,
    PyOnlyDirectoryTree,
    SequentialTasksScreenTemplate,
    TaskSpec,
    TaskStatus,
)
from tdconsole.textual_assets.screens.bsod import BSOD
from tdconsole.textual_assets.screens.widgets import (
    CurrentInstanceWidget,
    InstanceWidget,
    LabelItem,
)
# Legacy screens still live in textual_screens.py; re-export for compatibility.
from tdconsole.textual_assets.textual_screens import (
    BindAndStartInstance,
    DeleteInstance,
    HomeTabbedScreen,
    InstanceManagementScreen,
    InstanceSelectionScreen,
    MainScreen,
    PortConfigScreen,
    PyFileTreeScreen,
    StartInstance,
    StopInstance,
)

# Legacy re-exports: keep naming consistent with old textual_screens.py

__all__ = [
    "BSOD",
    "ListScreenTemplate",
    "PyOnlyDirectoryTree",
    "SequentialTasksScreenTemplate",
    "TaskSpec",
    "TaskStatus",
    "CurrentInstanceWidget",
    "InstanceWidget",
    "LabelItem",
    "MainScreen",
    "HomeTabbedScreen",
    "InstanceManagementScreen",
    "InstanceSelectionScreen",
    "PortConfigScreen",
    "BindAndStartInstance",
    "StartInstance",
    "StopInstance",
    "DeleteInstance",
    "PyFileTreeScreen",
]
