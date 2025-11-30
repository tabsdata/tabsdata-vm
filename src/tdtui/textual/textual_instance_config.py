from __future__ import annotations

from typing import Optional, Dict, Any, List

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Input, Label, Static, Footer
from textual.containers import Vertical, VerticalScroll
from rich.text import Text

from tdtui.core.find_instances import pull_all_tabsdata_instance_data as find_instances
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


def get_running_ports(screen) -> List[Dict[str, Any]]:
    """
    Python equivalent of get_running_ports() from bash.

    Returns a list of dicts for running instances, each with:
      name, status, external_port, internal_port
    """
    instances

    for inst in instances:
        status = inst.get("status")
        if status != "Running":
            continue

        name = inst.get("name", "?")
        arg_ext = inst.get("arg_ext") or ""
        arg_int = inst.get("arg_int") or ""

        # Extract port from "host:port" or use as-is if just "port"
        ext_port_str = arg_ext.split(":")[-1] if arg_ext else ""
        int_port_str = arg_int.split(":")[-1] if arg_int else ""

        # Only keep if they look like valid ports; otherwise ignore
        ext_port = int(ext_port_str) if ext_port_str.isdigit() else None
        int_port = int(int_port_str) if int_port_str.isdigit() else None

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
    port: int, current_instance_name: Optional[str] = None
) -> Optional[str]:
    """
    Return the instance name using this port, or None if free.
    """
    for inst in get_running_ports():
        name = inst.get("name")
        if current_instance_name and name == current_instance_name:
            continue

        ext_port = inst.get("external_port")
        int_port = inst.get("internal_port")

        if ext_port == port or int_port == port:
            return name

    return None


def name_in_use(selected_name: str) -> bool:
    """
    Return True if an instance already uses this name.
    """
    for inst in find_instances():
        name = inst.get("name")
        if selected_name == name:
            return True
    return False
