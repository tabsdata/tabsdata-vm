import os
import platform
from pathlib import Path


def detect_os_name() -> str:
    system = platform.system().lower()
    if system == "darwin":
        return "macOS"
    if system == "linux":
        return "Linux"
    if system == "windows":
        return "Windows"
    return platform.system() or "Unknown"


def _read_sys_value(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore").strip().lower()
    except Exception:
        return ""


def is_ec2_instance() -> bool:
    # Fast environment signal used in many AWS runtimes.
    if os.environ.get("AWS_EXECUTION_ENV"):
        return True

    # EC2-specific hints on Linux hosts.
    if detect_os_name() != "Linux":
        return False

    uuid_candidates = (
        Path("/sys/hypervisor/uuid"),
        Path("/sys/devices/virtual/dmi/id/product_uuid"),
    )
    for candidate in uuid_candidates:
        if _read_sys_value(candidate).startswith("ec2"):
            return True

    vendor_candidates = (
        Path("/sys/devices/virtual/dmi/id/sys_vendor"),
        Path("/sys/devices/virtual/dmi/id/board_vendor"),
        Path("/sys/devices/virtual/dmi/id/bios_vendor"),
        Path("/sys/devices/virtual/dmi/id/product_name"),
    )
    for candidate in vendor_candidates:
        value = _read_sys_value(candidate)
        if "amazon" in value or "ec2" in value:
            return True

    return False


def detect_system_runtime_label() -> str:
    os_name = detect_os_name()
    compute = "EC2" if is_ec2_instance() else "Non-EC2"
    return f"{os_name} ({compute})"


def detect_vm_type() -> str:
    return "EC2" if is_ec2_instance() else "Not Available"
