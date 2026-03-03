# tdconsole/core/tasks/instance_tasks.py

import ipaddress
from pathlib import Path
import shutil
import socket
import tempfile

import tabsdata as td
from packaging.version import Version

from tdconsole.core.find_instances import (
    instance_name_to_instance,
    is_remote_instance_name,
)
from tdconsole.core.yaml_getter_setter import get_yaml_value, set_yaml_value

# ------------------------------------------------------------
# Low level instance operations
# ------------------------------------------------------------


def is_remote_instance(instance) -> bool:
    return (
        getattr(instance, "status", None) == "Remote"
        or bool(getattr(instance, "is_remote", False))
        or is_remote_instance_name(getattr(instance, "name", None))
    )


HTTPS_CERT_MODE_SELF_GENERATED = "self_generated"
HTTPS_CERT_MODE_PROVIDED = "provided"


def resolve_https_cert_mode(instance) -> str:
    mode = str(getattr(instance, "https_cert_mode", "") or "").strip().lower()
    if mode in {HTTPS_CERT_MODE_SELF_GENERATED, HTTPS_CERT_MODE_PROVIDED}:
        return mode
    if is_remote_instance(instance):
        return HTTPS_CERT_MODE_PROVIDED
    if str(getattr(instance, "https_cert_path", "") or "").strip():
        return HTTPS_CERT_MODE_PROVIDED
    return HTTPS_CERT_MODE_SELF_GENERATED


def resolve_https_cert_path(instance) -> Path:
    cert_path = getattr(instance, "https_cert_path", None)
    if cert_path:
        return Path(str(cert_path)).expanduser()
    return Path.home() / "cert.pem"


def resolve_https_cert_identity(instance) -> tuple[str, str]:
    dns_name = socket.gethostname().strip() or "localhost"
    ip_candidate = str(getattr(instance, "public_ip", "") or "").strip()
    try:
        ipaddress.ip_address(ip_candidate)
        san_ip = ip_candidate
    except ValueError:
        san_ip = "127.0.0.1"
    return dns_name, san_ip


async def generate_https_cert(runner, instance, label=None) -> int:
    """
    Generate a self-signed cert/key pair using the same OpenSSL shape as td-setup.sh:
      - CN = hostname
      - SAN = DNS:<hostname>,IP:<public_ip_or_127.0.0.1>
      - keyUsage=digitalSignature
      - extendedKeyUsage=serverAuth
    """
    if is_remote_instance(instance):
        runner.log_line(label, "Skipping self-generated cert for remote instance.")
        return 0

    if getattr(instance, "use_https", False) is not True:
        runner.log_line(label, "HTTPS disabled; skipping cert generation.")
        return 0

    if resolve_https_cert_mode(instance) != HTTPS_CERT_MODE_SELF_GENERATED:
        runner.log_line(label, "HTTPS cert source is user-provided; skipping generation.")
        return 0

    cert_path = resolve_https_cert_path(instance)
    key_path = cert_path.parent / "key.pem"
    cert_path.parent.mkdir(parents=True, exist_ok=True)

    if cert_path.exists() and key_path.exists():
        runner.log_line(label, f"Self-generated cert already exists at {cert_path.parent}")
        return 0

    dns_name, san_ip = resolve_https_cert_identity(instance)
    subj = f"/CN={dns_name}"
    config = (
        f"[dn]\n"
        f"CN={dns_name}\n"
        f"[req]\n"
        f"distinguished_name = dn\n"
        f"[EXT]\n"
        f"subjectAltName=DNS:{dns_name},IP:{san_ip}\n"
        f"keyUsage=digitalSignature\n"
        f"extendedKeyUsage=serverAuth\n"
    )

    config_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".cnf",
            delete=False,
        ) as config_file:
            config_file.write(config)
            config_path = Path(config_file.name)

        runner.log_line(
            label,
            f"Generating self-signed HTTPS certificate for DNS:{dns_name}, IP:{san_ip}",
        )
        code = await runner.run_logged_subprocess(
            label,
            "openssl",
            "req",
            "-x509",
            "-out",
            str(cert_path),
            "-keyout",
            str(key_path),
            "-newkey",
            "rsa:4096",
            "-nodes",
            "-sha256",
            "-subj",
            subj,
            "-extensions",
            "EXT",
            "-config",
            str(config_path),
        )
        if code != 0:
            runner.log_line(label, "OpenSSL certificate generation failed.")
            return code
    finally:
        if config_path is not None:
            config_path.unlink(missing_ok=True)

    runner.log_line(label, f"Certificate created: {cert_path} and {key_path}")
    return 0


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
    if is_remote_instance(instance):
        runner.log_line(label, "Skipping local instance creation for remote instance.")
        return 0

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


async def upgrade_instance(runner, instance, label=None) -> int:
    """Create a new Tabsdata instance."""
    if is_remote_instance(instance):
        runner.log_line(label, "Skipping local instance upgrade for remote instance.")
        return 0

    runner.log_line(label, f"Checking instance version state for {instance.name}...")
    version_path = (
        Path.home()
        / ".tabsdata"
        / "instances"
        / instance.name
        / "workspace"
        / "work"
        / "etc"
        / "server-version.yaml"
    )
    instance_version = get_yaml_value(version_path, "version")
    if instance_version is None:
        return 0
    tabsdata_version = td.__version__

    runner.log_line(
        label,
        f"Tabsdata Version is {tabsdata_version} and Instance Version is {instance_version}...",
    )
    if Version(tabsdata_version) > Version(instance_version):
        runner.log_line(label, f"Instance upgrade to {tabsdata_version} is required...")
        if instance.status == "Running":
            await stop_instance(runner, instance, label)
        code = await runner.run_logged_subprocess(
            label,
            "tdserver",
            "upgrade",
            "--instance",
            instance.name,
        )
        runner.log_line(label, f"Upgrade command exited with code {code}")
        return code
    runner.log_line(label, f"Instance is up to date at version {instance_version}...")
    return 0


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
    if is_remote_instance(instance):
        return await noop_instance(runner, instance, label)
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
    if is_remote_instance(instance):
        runner.log_line(label, "Skipping local port binding for remote instance.")
        return

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


async def configure_https_cert(runner, instance, label=None) -> int:
    """
    Configure local instance TLS certificate files under instance config/ssl.

    For `https_cert_mode == self_generated`, cert/key are created first (if missing),
    then copied into instance config/ssl.
    For `https_cert_mode == provided`, cert PEM must exist at instance.https_cert_path
    (or ~/cert.pem fallback), with sibling key.pem.
    """
    if is_remote_instance(instance):
        runner.log_line(label, "Skipping local HTTPS cert copy for remote instance.")
        return 0

    if getattr(instance, "use_https", False) is not True:
        runner.log_line(label, "HTTPS disabled; skipping local certificate setup.")
        return 0

    cert_mode = resolve_https_cert_mode(instance)
    if cert_mode == HTTPS_CERT_MODE_SELF_GENERATED:
        generation_code = await generate_https_cert(runner, instance, label)
        if generation_code != 0:
            return generation_code

    cert_path = resolve_https_cert_path(instance)
    key_path = cert_path.parent / "key.pem"

    if cert_path.exists() is False or cert_path.is_file() is False:
        runner.log_line(label, f"Certificate PEM not found: {cert_path}")
        return 1
    if key_path.exists() is False or key_path.is_file() is False:
        runner.log_line(label, f"HTTPS key file not found: {key_path}")
        return 1

    ssl_path = (
        Path.home()
        / ".tabsdata"
        / "instances"
        / instance.name
        / "workspace"
        / "config"
        / "ssl"
    )
    ssl_path.mkdir(parents=True, exist_ok=True)

    shutil.copy2(cert_path, ssl_path / "cert.pem")
    shutil.copy2(key_path, ssl_path / "key.pem")
    runner.log_line(label, f"Copied HTTPS certs into {ssl_path}")
    return 0


async def add_https_cert(runner, instance, label=None) -> int:
    """
    Trust a server certificate via `td auth add-cert`.

    Non-fatal when command returns non-zero (for example if cert already exists).
    """
    if getattr(instance, "use_https", False) is not True:
        runner.log_line(label, "HTTPS disabled; skipping add-cert step.")
        return 0

    cert_path = resolve_https_cert_path(instance)
    if cert_path.exists() is False or cert_path.is_file() is False:
        runner.log_line(label, f"Certificate PEM not found: {cert_path}")
        return 1

    server_url = f"https://{instance.public_ip}:{instance.arg_ext}"
    runner.log_line(label, f"Adding trusted certificate for {server_url}...")
    code = await runner.run_logged_subprocess(
        label,
        "td",
        "auth",
        "add-cert",
        "--server",
        server_url,
        "--pem",
        str(cert_path),
    )
    if code != 0:
        runner.log_line(
            label,
            "add-cert exited non-zero; continuing because certificate may already be trusted.",
        )
        return 0

    return 0


# ------------------------------------------------------------
# Server lifecycle and status
# ------------------------------------------------------------


async def connect_tabsdata(runner, instance, label=None) -> int:
    """Start the Tabsdata server."""
    if is_remote_instance(instance):
        runner.log_line(label, "Skipping local tdserver start for remote instance.")
        return 0

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
    if is_remote_instance(instance):
        runner.log_line(label, "Skipping local tdserver status for remote instance.")
        return 0

    runner.log_line(label, "Checking Tabsdata server status...")
    code = await runner.run_logged_subprocess(
        label,
        "tdserver",
        "status",
        "--instance",
        instance.name,
    )
    runner.log_line(label, f"Status command exited with code {code}")

    # refresh instance state from filesystem/process so UI/DB reflect reality
    try:
        refreshed = instance_name_to_instance(instance.name)
        for field in (
            "pid",
            "status",
            "cfg_ext",
            "cfg_int",
            "arg_ext",
            "arg_int",
            "public_ip",
            "private_ip",
        ):
            setattr(instance, field, getattr(refreshed, field))
        runner.log_line(label, f"Refreshed instance status -> {instance.status}")
    except Exception as exc:
        runner.log_line(label, f"Could not refresh local instance metadata: {exc!r}")

    return code


async def connect_remote_tabsdata(runner, instance, label=None) -> int:
    """Connect to remote instance by logging in with host/port only."""
    runner.log_line(
        label,
        f"Connecting to remote instance at {instance.public_ip}:{instance.arg_ext}...",
    )
    code = await tabsdata_login(runner, instance, label)
    runner.log_line(label, f"Remote connection command exited with code {code}")
    return code
