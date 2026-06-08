import platform
import shutil
import subprocess
from pathlib import Path


def _run_command(args):
    try:
        return subprocess.check_output(args, text=True).strip()
    except Exception:
        return ""


def get_total_memory_gb():
    raw = _run_command(["sysctl", "-n", "hw.memsize"])
    try:
        return round(int(raw) / (1024 ** 3), 1)
    except Exception:
        return 0.0


def get_available_disk_gb(path=None):
    target = Path(path or Path.home())
    usage = shutil.disk_usage(target)
    return round(usage.free / (1024 ** 3), 1)


def get_hardware_profile():
    arch = platform.machine() or _run_command(["uname", "-m"])
    cpu_brand = _run_command(["sysctl", "-n", "machdep.cpu.brand_string"])
    macos_version = _run_command(["sw_vers", "-productVersion"])

    return {
        "architecture": arch,
        "is_apple_silicon": arch == "arm64",
        "cpu_brand": cpu_brand or "Unknown CPU",
        "macos_version": macos_version or "Unknown macOS",
        "total_memory_gb": get_total_memory_gb(),
        "available_disk_gb": get_available_disk_gb(),
    }


if __name__ == "__main__":
    import json
    print(json.dumps(get_hardware_profile(), ensure_ascii=False, indent=2))
