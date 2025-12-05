from __future__ import annotations

from typing import Optional, Dict, Any, List

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Input, Label, Static, Footer
from textual.containers import Vertical, VerticalScroll
from rich.text import Text

from tdtui.core.find_instances import (
    sync_filesystem_instances_to_db as sync_filesystem_instances_to_db,
)
import logging
from pathlib import Path
from textual import events


logging.basicConfig(
    filename=Path(__file__).resolve().parent / "log.log",
    level=logging.INFO,
    format="%(message)s",
)


def validate_port(port_str: str) -> bool:
    """Return True if port_str is an integer between 1 and 65535."""
    port_str = str(port_str)
    if not port_str.isdigit():
        return False
    port = int(port_str)
    return 1 <= port <= 65535


def get_running_ports(app) -> List[Dict[str, Any]]:
    """
    Python equivalent of get_running_ports() from bash.

    Returns a list of dicts for running instances, each with:
      name, status, external_port, internal_port
    """
    instances = sync_filesystem_instances_to_db(app=app)
    running = []

    for inst in instances:
        status = inst.status
        if status != "Running":
            continue

        name = inst.name
        arg_ext = inst.arg_ext or ""
        arg_int = inst.arg_int or ""

        # Only keep if they look like valid ports; otherwise ignore
        ext_port = int(arg_ext) if arg_ext.isdigit() else None
        int_port = int(arg_int) if arg_int.isdigit() else None

        running.append(
            {
                "name": name,
                "status": status,
                "external_port": ext_port,
                "internal_port": int_port,
            }
        )

    return running


def port_in_use(
    app, port: int, current_instance_name: Optional[str] = None
) -> Optional[str]:
    """
    Return the instance name using this port, or None if free.
    """
    for inst in get_running_ports(app):
        name = inst.get("name")
        if current_instance_name and name == current_instance_name:
            continue

        ext_port = inst.get("external_port")
        int_port = inst.get("internal_port")

        if ext_port == port or int_port == port:
            return name

    return None


def name_in_use(app, selected_name: str) -> bool:
    """
    Return True if an instance already uses this name.
    """
    for inst in sync_filesystem_instances_to_db(app):
        name = inst.name
        if selected_name == name:
            return True
    return False
