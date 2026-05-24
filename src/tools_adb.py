"""15 ADB & Emulator Management tools."""
import os
import subprocess
import time
from src.shared import _adb_run, _adb_shell, ADB_BINARY, ADB_HOST, ADB_PORT, LIBS_DIR

def register(mcp):
    @mcp.tool()
    def adb_connect(host: str = "127.0.0.1", port: int = 5555) -> str:
        """Connect to an Android emulator or device over TCP/IP.
        Args: host (device IP), port (ADB port, default 5555)."""
        return _adb_run([ADB_BINARY, "connect", f"{host}:{port}"], timeout=10)

    @mcp.tool()
    def adb_disconnect(host: str = "127.0.0.1", port: int = 5555) -> str:
        """Disconnect from a previously connected Android device.
        Args: host, port."""
        return _adb_run([ADB_BINARY, "disconnect", f"{host}:{port}"], timeout=10)

    @mcp.tool()
    def adb_device_info() -> str:
        """Extract device model, API level, kernel version, and display density."""
        arch = _adb_shell("getprop ro.product.cpu.abi")
        sdk = _adb_shell("getprop ro.build.version.sdk")
        release = _adb_shell("getprop ro.build.version.release")
        brand = _adb_shell("getprop ro.product.brand")
        model = _adb_shell("getprop ro.product.model")
        kernel = _adb_shell("uname -r")
        density = _adb_shell("getprop ro.sf.lcd_density")
        root_check = _adb_shell("id", su=True)
        is_root = "uid=0" in root_check
        devices_list = []
        try:
            r = subprocess.run([ADB_BINARY, "devices"], capture_output=True, text=True, timeout=5)
            for line in r.stdout.strip().splitlines()[1:]:
                parts = line.strip().split()
                if len(parts) >= 2:
                    devices_list.append(f"{parts[0]} [{parts[1]}]")
        except Exception:
            pass
        return (
            f"Device: {' '.join(devices_list)}\n"
            f"Arch: {arch}\nSDK: {sdk} (Android {release})\n"
            f"Brand: {brand}\nModel: {model}\nKernel: {kernel}\nDensity: {density}\nRoot: {is_root}"
        )

    @mcp.tool()
    def adb_devices() -> str:
        """List connected Android devices and their connection state."""
        try:
            r = subprocess.run([ADB_BINARY, "devices"], capture_output=True, text=True, timeout=10)
            lines = r.stdout.strip().splitlines()
            if len(lines) <= 1:
                return "No devices connected"
            result = []
            for line in lines[1:]:
                parts = line.strip().split()
                if len(parts) >= 2:
                    result.append(f"{parts[0]}\t{parts[1]}")
            return "\n".join(result) if result else "No devices connected"
        except FileNotFoundError:
            return "FATAL: adb binary not found"
        except subprocess.TimeoutExpired:
            return "TIMEOUT: adb devices"

    @mcp.tool()
    def adb_list_packages() -> str:
        """Scan and return third-party app identifiers on the device."""
        return _adb_shell("pm list packages -3 | cut -d':' -f2 | sort", su=False)

    @mcp.tool()
    def adb_current_app() -> str:
        """Pinpoint the active foreground package and activity layout."""
        return _adb_shell("dumpsys window | grep -E 'mCurrentFocus|mFocusedApp'")

    @mcp.tool()
    def adb_force_stop(package: str) -> str:
        """Kill a target package instance to reset memory space.
        Args: package (e.g. com.dts.freefireth)."""
        return _adb_shell(f"am force-stop {package}")

    @mcp.tool()
    def adb_clear_data(package: str) -> str:
        """Wipe an app's localized cache and sandbox preferences.
        Args: package name."""
        return _adb_shell(f"pm clear {package}")

    @mcp.tool()
    def adb_install_apk(apk_path: str) -> str:
        """Deploy a modified APK file from host storage using -r.
        Args: apk_path on host."""
        return _adb_run([ADB_BINARY, "install", "-r", apk_path], timeout=120)

    @mcp.tool()
    def adb_uninstall_package(package: str) -> str:
        """Safely remove a package signature from the device registry.
        Args: package name."""
        return _adb_shell(f"pm uninstall {package}")

    @mcp.tool()
    def adb_grant_permissions(package: str) -> str:
        """Force global runtime permission verification (storage, overlay).
        Args: package name."""
        perms = ["android.permission.WRITE_EXTERNAL_STORAGE",
                 "android.permission.READ_EXTERNAL_STORAGE",
                 "android.permission.SYSTEM_ALERT_WINDOW"]
        results = []
        for p in perms:
            results.append(_adb_shell(f"pm grant {package} {p}", su=False))
        return "\n".join(results)

    @mcp.tool()
    def adb_file_push(local_path: str, remote_path: str) -> str:
        """Write a binary stub from host to /data/local/tmp.
        Args: local_path, remote_path."""
        if not os.path.isfile(local_path):
            return f"ERROR: local file not found: {local_path}"
        push_r = _adb_run([ADB_BINARY, "push", local_path, remote_path], timeout=60)
        _adb_shell(f"chmod 755 {remote_path}", su=True)
        return f"pushed: {push_r}"

    @mcp.tool()
    def adb_file_pull(remote_path: str, local_path: str = "") -> str:
        """Extract a dump or database layer back into host project folder.
        Args: remote_path, local_path (default libs/<filename>)."""
        if not local_path:
            basename = os.path.basename(remote_path)
            local_path = str(LIBS_DIR / basename)
        return _adb_run([ADB_BINARY, "pull", remote_path, local_path], timeout=60)

    @mcp.tool()
    def adb_file_chmod(remote_path: str, mode: str = "755") -> str:
        """Grant executable permissions to a remote binary.
        Args: remote_path, mode (default 755)."""
        return _adb_shell(f"chmod {mode} {remote_path}", su=True)

    @mcp.tool()
    def adb_file_remove(remote_path: str) -> str:
        """Delete residual analysis artifacts from device storage.
        Args: remote_path."""
        return _adb_shell(f"rm -f {remote_path}", su=True)

    @mcp.tool()
    def adb_mkdir(remote_path: str) -> str:
        """Generate dedicated target output directories on the device.
        Args: remote_path to create."""
        return _adb_shell(f"mkdir -p {remote_path}", su=True)