import subprocess
import os
import re
from typing import Optional

ADB = "adb"

class ADBError(Exception):
    pass

def _run(cmd: list[str], timeout: int = 30) -> str:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        out = r.stdout.strip()
        if r.stderr:
            out += "\nSTDERR: " + r.stderr.strip()
        if r.returncode != 0 and not out:
            raise ADBError(f"exit code {r.returncode}: {r.stderr.strip()}")
        return out
    except FileNotFoundError:
        raise ADBError("adb not found on PATH")
    except subprocess.TimeoutExpired:
        raise ADBError(f"command timed out ({timeout}s)")

def devices() -> list[dict]:
    raw = _run([ADB, "devices"])
    result = []
    for line in raw.splitlines()[1:]:
        parts = line.strip().split()
        if len(parts) >= 2:
            result.append({"serial": parts[0], "state": parts[1]})
    return result

def shell(command: str, su: bool = False) -> str:
    cmd = [ADB, "shell"]
    if su:
        cmd += ["su", "-c", command]
    else:
        cmd += [command]
    return _run(cmd, timeout=30)

def push(local: str, remote: str) -> str:
    return _run([ADB, "push", local, remote], timeout=60)

def pull(remote: str, local: str) -> str:
    return _run([ADB, "pull", remote, local], timeout=60)

def logcat(filter_expr: str = "", lines: int = 100) -> str:
    cmd = [ADB, "logcat", "-d", "-t", str(lines)]
    if filter_expr:
        cmd += ["-s", filter_expr]
    return _run(cmd, timeout=15)

def logcat_stream(filter_expr: str = "", timeout_sec: int = 10) -> str:
    cmd = [ADB, "logcat", "-v", "threadtime"]
    if filter_expr:
        cmd += ["-s", filter_expr]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_sec)
        return r.stdout.strip()
    except subprocess.TimeoutExpired:
        return "stream ended (timeout)"

def force_stop(package: str) -> str:
    return shell(f"am force-stop {package}")

def start_activity(package: str, activity: Optional[str] = None) -> str:
    if activity:
        return shell(f"am start -n {package}/{activity}")
    return shell(f"monkey -p {package} 1")

def device_arch() -> str:
    return shell("getprop ro.product.cpu.abi")

def is_root() -> bool:
    r = shell("id", su=True)
    return "uid=0" in r

def install_apk(path: str) -> str:
    return _run([ADB, "install", "-r", path], timeout=120)

def chmod(path: str, mode: str = "755", su: bool = True) -> str:
    return shell(f"chmod {mode} {path}", su=su)

def register(mcp):
    """Register all ADB tools with the FastMCP server."""

    @mcp.tool()
    def adb_devices() -> str:
        """List connected Android devices and their state."""
        try:
            devs = devices()
            if not devs:
                return "No devices connected"
            return "\n".join(f"{d['serial']}\t{d['state']}" for d in devs)
        except ADBError as e:
            return f"ERROR: {e}"

    @mcp.tool()
    def adb_shell(command: str, su: bool = False) -> str:
        """Execute a shell command on the Android device.

        Args:
            command: Shell command to execute.
            su: Whether to run via su (root).
        """
        try:
            return shell(command, su=su)
        except ADBError as e:
            return f"ERROR: {e}"

    @mcp.tool()
    def adb_push_file(local_path: str, remote_path: str) -> str:
        """Push a local file to a path on the Android device.

        Args:
            local_path: Path on the host machine.
            remote_path: Destination path on the device.
        """
        try:
            return push(local_path, remote_path)
        except ADBError as e:
            return f"ERROR: {e}"

    @mcp.tool()
    def adb_pull_file(remote_path: str, local_path: str) -> str:
        """Pull a file from the Android device to the host.

        Args:
            remote_path: Path on the device.
            local_path: Destination path on the host.
        """
        try:
            return pull(remote_path, local_path)
        except ADBError as e:
            return f"ERROR: {e}"

    @mcp.tool()
    def adb_logcat(filter_tag: str = "", lines: int = 100) -> str:
        """Retrieve recent Android logcat output.

        Args:
            filter_tag: Logcat filter expression (e.g. 'REChainMod:S').
            lines: Number of recent lines to fetch.
        """
        try:
            return logcat(filter_expr=filter_tag, lines=lines)
        except ADBError as e:
            return f"ERROR: {e}"

    @mcp.tool()
    def adb_force_stop(package: str) -> str:
        """Force-stop an Android package.

        Args:
            package: Package name (e.g. com.dts.freefireth).
        """
        try:
            return force_stop(package)
        except ADBError as e:
            return f"ERROR: {e}"

    @mcp.tool()
    def adb_start_activity(package: str, activity: str = "") -> str:
        """Start an Android app or specific activity.

        Args:
            package: Package name.
            activity: Optional activity name (e.g. .MainActivity).
        """
        try:
            return start_activity(package, activity or None)
        except ADBError as e:
            return f"ERROR: {e}"

    @mcp.tool()
    def adb_restart_package(package_name: str) -> str:
        """Force-stop and then restart a package. Equivalent to a clean relaunch.

        Args:
            package_name: Package name to restart.
        """
        try:
            stop = force_stop(package_name)
            start = start_activity(package_name)
            return f"stopped: {stop}\nstarted: {start}"
        except ADBError as e:
            return f"ERROR: {e}"

    @mcp.tool()
    def adb_push_payload(local_path: str, remote_path: str) -> str:
        """Push a compiled .so payload to the device and set executable permissions.

        This is the primary deploy tool for libmod.so and similar modules.

        Args:
            local_path: Path to the .so file on the host.
            remote_path: Destination path on the device (e.g. /data/local/tmp/libmod.so).
        """
        try:
            out = push(local_path, remote_path)
            chmod(remote_path, "755", su=True)
            return f"pushed: {out}\npermissions set: {remote_path} (755)"
        except ADBError as e:
            return f"ERROR: {e}"

    @mcp.tool()
    def device_info() -> str:
        """Return Android device architecture and root status."""
        try:
            arch = device_arch()
            root = is_root()
            return f"Arch: {arch}\nRoot: {root}"
        except ADBError as e:
            return f"ERROR: {e}"