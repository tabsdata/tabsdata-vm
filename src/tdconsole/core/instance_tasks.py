# tdconsole/core/tasks/instance_tasks.py

from pathlib import Path
from tdconsole.core.yaml_getter_setter import set_yaml_value


# ------------------------------------------------------------
# Low level instance operations
# ------------------------------------------------------------


async def stop_instance(runner, instance, label=None) -> int:
    """Stop a running Tabsdata instance."""
    runner.log_line(label, f"Stopping instance {instance.name}...")
    code = await runner.run_logged_subprocess(
        label,
        "tdserver",
        "stop",
        "--instance",
        instance.name,
    )
    runner.log_line(label, f"Stop command exited with code {code}")
    return code


async def delete_instance(runner, instance, label=None) -> int:
    """Delete a running Tabsdata instance."""
    runner.log_line(label, f"Deleting instance {instance.name}...")
    if instance.status == "Running":
        await stop_instance(runner, instance)
    code = await runner.run_logged_subprocess(
        label,
        "tdserver",
        "delete",
        "--instance",
        instance.name,
        "--force",
    )
    runner.log_line(label, f"Stop command exited with code {code}")
    return code


async def tabsdata_login(runner, instance, label=None) -> int:
    """Login to a Tabsdata Instance"""
    runner.log_line(label, f"Logging User into {instance.name}...")
    https_config = "https://" if instance.use_https is True else ""
    code = await runner.run_logged_subprocess(
        label,
        "td",
        "login",
        "--server",
        f"{https_config}{instance.public_ip}:{instance.arg_ext}",
        "--user",
        "admin",
        "--role",
        "sys_admin",
        "--password",
        "tabsdata",
    )
    runner.log_line(label, f"Stop command exited with code {code}")
    return code


async def tabsdata_logout(runner, instance, label=None) -> int:
    """Login to a Tabsdata Instance"""
    runner.log_line(label, f"Logging User out of {instance.name}...")
    code = await runner.run_logged_subprocess(label, "td", "logout")
    runner.log_line(label, f"Logout command exited with code {code}")
    return code


async def create_instance(runner, instance, label=None) -> int:
    """Create a new Tabsdata instance."""
    runner.log_line(label, f"Creating instance {instance.name}...")
    code = await runner.run_logged_subprocess(
        label,
        "tdserver",
        "create",
        "--instance",
        instance.name,
    )
    runner.log_line(label, f"Create command exited with code {code}")
    return code


async def noop_instance(runner, instance, label=None) -> int:
    """No operation for statuses that do not need preparation."""
    runner.log_line(
        label,
        f"No server preparation steps required (status={instance.status}).",
    )
    return 0


# Map of instance.status -> handler function
STATUS_HANDLERS = {
    "Running": stop_instance,
    "Not Created": create_instance,
}


# ------------------------------------------------------------
# Composite task: prepare instance based on status
# ------------------------------------------------------------


async def prepare_instance(runner, instance, label=None) -> int:
    """
    Prepare the server depending on the instance status.

    - If status is "Running" -> stop it
    - If status is "Not Created" -> create it
    - Otherwise -> no op
    """
    if instance.status == "Not Created":
        return await create_instance(runner, instance, label)
    elif runner.new["arg_ext"] == False and runner.new["arg_int"] == False:
        return await noop_instance(runner, instance, label)
    elif instance.status == "Running":
        return await stop_instance(runner, instance, label)
    else:
        return await noop_instance(runner, instance, label)


# ------------------------------------------------------------
# Port binding
# ------------------------------------------------------------


async def bind_ports(runner, instance, label=None) -> None:
    """Update instance config.yaml with external and internal ports."""
    config_path = (
        Path.home()
        / ".tabsdata"
        / "instances"
        / instance.name
        / "workspace"
        / "config"
        / "proc"
        / "regular"
        / "apiserver"
        / "config"
        / "config.yaml"
    )

    runner.log_line(label, f"Updating port config at {config_path}")

    # external
    if runner.new["arg_ext"] is True:
        cfg_ext = set_yaml_value(
            path=config_path,
            key="addresses",
            value=f"127.0.0.1:{instance.arg_ext}",
            value_type="list",
        )
        runner.log_line(label, f"Set external port -> {cfg_ext}")

    # internal
    if runner.new["arg_int"] is True:
        cfg_int = set_yaml_value(
            path=config_path,
            key="internal_addresses",
            value=f"127.0.0.1:{instance.arg_int}",
            value_type="list",
        )
        runner.log_line(label, f"Set internal port -> {cfg_int}")


# ------------------------------------------------------------
# Server lifecycle and status
# ------------------------------------------------------------


async def connect_tabsdata(runner, instance, label=None) -> int:
    """Start the Tabsdata server."""
    runner.log_line(label, "Starting Tabsdata server...")
    code = await runner.run_logged_subprocess(
        label,
        "tdserver",
        "start",
        "--instance",
        instance.name,
    )
    runner.log_line(label, f"Start command exited with code {code}")
    return code


async def run_tdserver_status(runner, instance, label=None) -> int:
    """Check server status and update DB for working instance."""
    runner.log_line(label, "Checking Tabsdata server status...")
    code = await runner.run_logged_subprocess(
        label,
        "tdserver",
        "status",
        "--instance",
        instance.name,
    )
    runner.log_line(label, f"Status command exited with code {code}")

    # update the working instance in DB
    runner.log_line(label, "Updating working instance record in the database...")

    return code
