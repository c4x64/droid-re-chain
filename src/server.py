import os
import sys
import subprocess
import time
import re
import json
import asyncio
import threading
import queue
import signal as signal_module
import tempfile
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("droid-re-chain-monolith")

ADB_BINARY = "adb"
ADB_HOST = "127.0.0.1"
ADB_PORT = 5555

NDK_BASE = os.environ.get(
    "ANDROID_NDK_HOME",
    "/opt/homebrew/share/android-commandlinetools/ndk/25.2.9519653",
)
NDK_TOOLCHAIN = f"{NDK_BASE}/toolchains/llvm/prebuilt/darwin-x86_64"
NDK_CLANG = f"{NDK_TOOLCHAIN}/bin/aarch64-linux-android21-clang"
NDK_CLANGXX = f"{NDK_TOOLCHAIN}/bin/aarch64-linux-android21-clang++"
NDK_STRIP = f"{NDK_TOOLCHAIN}/bin/llvm-strip"
NDK_SYSROOT = f"{NDK_TOOLCHAIN}/sysroot"
NDK_MAKE = f"{NDK_BASE}/prebuilt/darwin-x86_64/bin/make"
NDK_CMAKE_TOOLCHAIN = f"{NDK_BASE}/build/cmake/android.toolchain.cmake"

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LIBS_DIR = PROJECT_ROOT / "libs"
SRC_DIR = PROJECT_ROOT / "src"
INCLUDE_DIR = PROJECT_ROOT / "include"
PATCHES_DIR = PROJECT_ROOT / "patches"
LOGS_DIR = PROJECT_ROOT / "logs"

LIBS_DIR.mkdir(exist_ok=True)
PATCHES_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

@dataclass
class CrashContext:
    timestamp: str = ""
    signal: str = ""
    pid: str = ""
    tid: str = ""
    process_name: str = ""
    fault_library: str = ""
    fault_pc: str = ""
    backtrace: list[dict] = field(default_factory=list)
    raw: str = ""

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "signal": self.signal,
            "pid": self.pid,
            "tid": self.tid,
            "process_name": self.process_name,
            "fault_library": self.fault_library,
            "fault_pc": self.fault_pc,
            "backtrace": self.backtrace,
            "raw_length": len(self.raw),
        }

class CrashTrapDaemon:
    def __init__(self):
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._queue: queue.Queue = queue.Queue()
        self._filter = ""

    def start(self, logcat_filter: str = "SIGSEGV|SIGILL|SIGABRT|FATAL EXCEPTION"):
        if self._running:
            return
        self._running = True
        self._filter = logcat_filter
        self._thread = threading.Thread(target=self._trap_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)

    def _trap_loop(self):
        cmd = [ADB_BINARY, "logcat", "-v", "threadtime", "-b", "crash"]
        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
        except FileNotFoundError:
            self._queue.put("FATAL: adb not found")
            self._running = False
            return

        buffer = []
        while self._running:
            try:
                line = proc.stdout.readline()
                if not line:
                    time.sleep(0.1)
                    continue
                if self._filter and re.search(self._filter, line, re.IGNORECASE):
                    buffer.append(line.strip())
                    timeout_count = 0
                    while timeout_count < 50:
                        extra = proc.stdout.readline()
                        if not extra:
                            break
                        buffer.append(extra.strip())
                        if re.match(r"^\s*$", extra):
                            break
                        timeout_count += 1
                    crash_text = "\n".join(buffer)
                    parsed = self._parse_crash_block(crash_text)
                    self._queue.put(parsed.to_dict() if parsed else crash_text)
                    buffer = []
            except Exception as exc:
                self._queue.put(f"TRAP ERROR: {exc}")
                break
        proc.terminate()

    def _parse_crash_block(self, text: str) -> Optional[CrashContext]:
        ctx = CrashContext(raw=text)
        patterns = {
            "signal": r"(signal \d+)\s+\(([^)]+)\)",
            "pid": r"pid:\s+(\d+)",
            "tid": r"tid:\s+(\d+)",
            "process_name": r"pid: \d+, tid: \d+, name:\s+(\S+)",
        }
        for key, pat in patterns.items():
            m = re.search(pat, text)
            if m:
                setattr(ctx, key, m.group(1))
        pc_match = re.search(r"pc\s+([0-9a-fA-F]+)", text)
        if pc_match:
            ctx.fault_pc = pc_match.group(1)
        for line in text.splitlines():
            m = re.match(r"\s*(#[0-9]+)\s+(pc|lr)\s+([0-9a-fA-F]+)\s+(\S+)", line)
            if m:
                ctx.backtrace.append({
                    "frame": m.group(1),
                    "type": m.group(2),
                    "address": m.group(3),
                    "library": m.group(4),
                })
                if not ctx.fault_library:
                    ctx.fault_library = m.group(4)
        if ctx.backtrace or ctx.signal:
            return ctx
        signal_match = re.search(r"(SIGSEGV|SIGILL|SIGABRT|SIGFPE)", text)
        if signal_match:
            ctx.signal = signal_match.group(1)
            return ctx
        return None

    def get_crashes(self, timeout: float = 1.0) -> list:
        results = []
        while True:
            try:
                item = self._queue.get_nowait()
                results.append(item)
            except queue.Empty:
                break
        return results

_crash_trap = CrashTrapDaemon()

def _adb_run(cmd: list[str], timeout: int = 30) -> str:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        out = r.stdout.strip()
        if r.stderr:
            out += "\nSTDERR: " + r.stderr.strip()
        if r.returncode != 0 and not out:
            return f"EXIT_CODE_{r.returncode}: {r.stderr.strip()}"
        return out
    except FileNotFoundError:
        return "FATAL: adb binary not found on PATH. Install platform-tools."
    except subprocess.TimeoutExpired:
        return f"TIMEOUT: command exceeded {timeout}s limit"
    except Exception as e:
        return f"ERROR: {e}"

def _adb_shell(command: str, su: bool = False) -> str:
    cmd = [ADB_BINARY, "shell"]
    if su:
        cmd += ["su", "-c", command]
    else:
        cmd += [command]
    return _adb_run(cmd, timeout=30)

def _check_ndk_toolchain() -> Optional[str]:
    if not os.path.isfile(NDK_CLANG):
        return f"NDK clang not found at {NDK_CLANG}. Set ANDROID_NDK_HOME or install NDK 25."
    return None

def _parse_ndk_errors(stderr: str, stdout: str) -> str:
    if not stderr and not stdout:
        return json.dumps({"status": "success", "errors": [], "warnings": []})
    errors = []
    warnings = []
    for line in stderr.splitlines():
        if "error:" in line.lower():
            errors.append(line.strip())
        elif "warning:" in line.lower():
            warnings.append(line.strip())
    for line in stdout.splitlines():
        if "error:" in line.lower():
            errors.append(line.strip())
        elif "warning:" in line.lower():
            warnings.append(line.strip())
    return json.dumps({
        "status": "failed" if errors else "success",
        "errors": errors[:30],
        "warnings": warnings[:30],
        "raw_stderr_length": len(stderr),
        "raw_stdout_length": len(stdout),
    })

@mcp.tool()
def adb_connect(host: str = "127.0.0.1", port: int = 5555) -> str:
    """Connect to an Android emulator or device over TCP/IP.

    Args:
        host: Device IP address (default 127.0.0.1 for BlueStacks loopback).
        port: ADB port (default 5555).
    """
    return _adb_run([ADB_BINARY, "connect", f"{host}:{port}"], timeout=10)

@mcp.tool()
def adb_disconnect(host: str = "127.0.0.1", port: int = 5555) -> str:
    """Disconnect from a previously connected Android device.

    Args:
        host: Device IP address.
        port: ADB port.
    """
    return _adb_run([ADB_BINARY, "disconnect", f"{host}:{port}"], timeout=10)

@mcp.tool()
def adb_devices() -> str:
    """List all connected Android devices and their connection state."""
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
def adb_push_binary(local_path: str, remote_path: str) -> str:
    """Push a binary file from the host to the device.

    Args:
        local_path: Absolute or relative path to the file on the host.
        remote_path: Destination path on the device (e.g. /data/local/tmp/libmod.so).
    """
    if not os.path.isfile(local_path):
        return f"ERROR: local file not found: {local_path}"
    push_result = _adb_run([ADB_BINARY, "push", local_path, remote_path], timeout=60)
    chmod_result = _adb_shell(f"chmod 755 {remote_path}", su=True)
    return f"push: {push_result}\npermissions: {chmod_result}"

@mcp.tool()
def adb_pull_data(remote_path: str, local_path: str = "") -> str:
    """Pull a file or directory from the device to the host.

    Args:
        remote_path: Path on the device.
        local_path: Destination on the host. Defaults to libs/<filename>.
    """
    if not local_path:
        basename = os.path.basename(remote_path)
        local_path = str(LIBS_DIR / basename)
    return _adb_run([ADB_BINARY, "pull", remote_path, local_path], timeout=60)

@mcp.tool()
def adb_shell_cmd(command: str, su: bool = False) -> str:
    """Execute a shell command on the Android device and return the output.

    Args:
        command: The shell command to execute.
        su: Whether to run via su (root).
    """
    return _adb_shell(command, su=su)

@mcp.tool()
def adb_install_apk(apk_path: str) -> str:
    """Install an Android APK on the connected device with -r (replace existing).

    Args:
        apk_path: The APK file path on the host.
    """
    return _adb_run([ADB_BINARY, "install", "-r", apk_path], timeout=120)

@mcp.tool()
def adb_start_activity(package: str, activity: str = "") -> str:
    """Start an Android package or specific activity.

    Args:
        package: Package name (e.g. com.dts.freefireth).
        activity: Optional activity name (e.g. .MainActivity).
    """
    if activity:
        return _adb_shell(f"am start -n {package}/{activity}")
    else:
        return _adb_shell(f"monkey -p {package} 1")

@mcp.tool()
def adb_force_stop(package: str) -> str:
    """Force-stop an Android package.

    Args:
        package: Package name.
    """
    return _adb_shell(f"am force-stop {package}")

@mcp.tool()
def adb_get_packages() -> str:
    """List all installed packages on the device."""
    return _adb_shell("pm list packages -3 | cut -d':' -f2 | sort -n | head -50", su=False)

@mcp.tool()
def ndk_build_clean() -> str:
    """Remove all compiled artifacts from the libs directory.

    Returns a count of deleted files.
    """
    count = 0
    for f in LIBS_DIR.glob("*"):
        try:
            f.unlink()
            count += 1
        except OSError:
            pass
    return f"cleaned {count} artifact(s) from {LIBS_DIR}"

@mcp.tool()
def ndk_build_module(source: str = "main.cpp", output: str = "libmod.so") -> str:
    """Compile an NDK shared library (.so) from C++ source using the arm64 toolchain.

    Parses compiler diagnostics and returns structured JSON with errors and warnings.

    Args:
        source: Source file name inside src/ (default main.cpp).
        output: Output .so name inside libs/ (default libmod.so).
    """
    toolchain_issue = _check_ndk_toolchain()
    if toolchain_issue:
        return toolchain_issue

    src_path = SRC_DIR / source
    if not src_path.exists():
        return f"ERROR: source not found at {src_path}"

    out_path = LIBS_DIR / output
    cmd = [
        NDK_CLANG,
        "-target", "aarch64-linux-android21",
        "--sysroot", NDK_SYSROOT,
        "-I", str(INCLUDE_DIR),
        "-fPIC", "-shared",
        "-O2", "-fvisibility=hidden",
        "-Wall", "-Wextra",
        "-o", str(out_path),
        str(src_path),
        "-llog", "-ldl",
        "-Wl,--gc-sections",
        "-Wl,--hash-style=sysv",
    ]

    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    except subprocess.TimeoutExpired:
        return json.dumps({"status": "timeout", "detail": "compilation exceeded 120s"})
    except FileNotFoundError:
        return json.dumps({"status": "fatal", "detail": f"compiler not found: {NDK_CLANG}"})
    except Exception as e:
        return json.dumps({"status": "error", "detail": str(e)})

    if r.returncode != 0:
        diag = json.loads(_parse_ndk_errors(r.stderr, r.stdout))
        diag["compiler_exit_code"] = r.returncode
        return json.dumps(diag, indent=2)

    size = out_path.stat().st_size

    stripped_path = LIBS_DIR / output.replace(".so", "_stripped.so")
    s = subprocess.run(
        [NDK_STRIP, "-o", str(stripped_path), str(out_path)],
        capture_output=True, text=True, timeout=30,
    )
    strip_info = ""
    if s.returncode == 0:
        stripped_size = stripped_path.stat().st_size
        strip_info = f", stripped: {stripped_size} bytes"
    else:
        strip_info = f", strip skipped: {s.stderr.strip()}"

    diag = json.loads(_parse_ndk_errors(r.stderr, r.stdout))
    diag["status"] = "success"
    diag["output"] = str(out_path)
    diag["size_bytes"] = size
    diag["strip"] = strip_info
    return json.dumps(diag, indent=2)

@mcp.tool()
def cmake_generate_config(build_dir: str = "build/cmake") -> str:
    """Generate CMake build configuration for the project using the Android NDK toolchain file.

    Args:
        build_dir: Relative or absolute path for the CMake build directory.
    """
    build_path = Path(build_dir)
    if not build_path.is_absolute():
        build_path = PROJECT_ROOT / build_path
    build_path.mkdir(parents=True, exist_ok=True)

    if not os.path.isfile(NDK_CMAKE_TOOLCHAIN):
        return f"ERROR: NDK CMake toolchain not found at {NDK_CMAKE_TOOLCHAIN}"

    android_mk = PROJECT_ROOT / "Android.mk"
    cmake_lists = PROJECT_ROOT / "CMakeLists.txt"

    if not cmake_lists.exists():
        cmake_content = f"""cmake_minimum_required(VERSION 3.18)
project(droid-re-chain C CXX)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

add_library(mod SHARED src/main.cpp)
target_include_directories(mod PRIVATE include)
target_link_libraries(mod log dl)
"""
        cmake_lists.write_text(cmake_content)
        return f"created CMakeLists.txt at {cmake_lists}. Re-run to configure."

    cmd = [
        "cmake",
        "-DCMAKE_TOOLCHAIN_FILE=" + NDK_CMAKE_TOOLCHAIN,
        "-DANDROID_ABI=arm64-v8a",
        "-DANDROID_PLATFORM=android-21",
        "-DCMAKE_BUILD_TYPE=Release",
        "-S", str(PROJECT_ROOT),
        "-B", str(build_path),
    ]

    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    except subprocess.TimeoutExpired:
        return "TIMEOUT: cmake configuration exceeded 60s"
    except FileNotFoundError:
        return "ERROR: cmake not found on PATH"
    except Exception as e:
        return f"ERROR: {e}"

    out = r.stdout.strip()
    err = r.stderr.strip()
    if r.returncode != 0:
        return f"CMAKE CONFIG FAILED (exit {r.returncode}):\n{err[:2000]}"
    return f"cmake configured: {build_path}\n{out[:1000]}"

@mcp.tool()
def cmake_compile_target(build_dir: str = "build/cmake", target: str = "mod") -> str:
    """Compile a CMake target using the generated build configuration.

    Args:
        build_dir: CMake build directory.
        target: CMake target name (default: mod).
    """
    build_path = Path(build_dir)
    if not build_path.is_absolute():
        build_path = PROJECT_ROOT / build_path
    if not (build_path / "CMakeCache.txt").exists():
        return f"ERROR: build not configured at {build_path}. Run cmake_generate_config first."

    cmd = ["cmake", "--build", str(build_path), "--target", target]
    if os.name == "posix":
        cmd.extend(["--", "-j$(sysctl -n hw.ncpu)"])

    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    except subprocess.TimeoutExpired:
        return "TIMEOUT: cmake build exceeded 180s"
    except FileNotFoundError:
        return "ERROR: cmake not found"
    except Exception as e:
        return f"ERROR: {e}"

    parsed = json.loads(_parse_ndk_errors(r.stderr, r.stdout))
    parsed["command"] = " ".join(cmd)
    if r.returncode == 0:
        lib_output = LIBS_DIR / "libmod.so"
        if lib_output.exists():
            parsed["output_size"] = lib_output.stat().st_size
        parsed["status"] = "success"
    else:
        parsed["status"] = "failed"
        parsed["compiler_exit_code"] = r.returncode
    return json.dumps(parsed, indent=2)

@mcp.tool()
def verify_binary_architecture(binary_path: str = "") -> str:
    """Verify that a compiled .so file is ARM64 (aarch64) ELF.

    Reads the ELF header directly to confirm architecture alignment.

    Args:
        binary_path: Path to the .so file. Defaults to libs/libmod_stripped.so.
    """
    if not binary_path:
        candidates = [
            LIBS_DIR / "libmod_stripped.so",
            LIBS_DIR / "libmod.so",
        ]
        for c in candidates:
            if c.exists():
                binary_path = str(c)
                break
        if not binary_path:
            return "ERROR: no binary found in libs/. Build the module first."

    if not os.path.isfile(binary_path):
        return f"ERROR: file not found: {binary_path}"

    try:
        with open(binary_path, "rb") as f:
            header = f.read(64)
    except IOError as e:
        return f"ERROR: cannot read {binary_path}: {e}"

    if len(header) < 16:
        return f"ERROR: file too small ({len(header)} bytes) for ELF header"

    if header[:4] != b"\x7fELF":
        return f"NOT AN ELF: {binary_path} (magic mismatch)"

    elf_class = header[4]
    if elf_class == 1:
        class_str = "32-bit"
    elif elf_class == 2:
        class_str = "64-bit"
    else:
        class_str = f"unknown ({elf_class})"

    elf_data = header[5]
    endian_str = "little" if elf_data == 1 else "big" if elf_data == 2 else f"unknown ({elf_data})"

    elf_machine = header[18] | (header[19] << 8)
    machine_map = {
        0: "No machine", 3: "i386", 40: "ARM", 62: "x86-64",
        183: "AArch64", 243: "RISC-V",
    }
    machine_str = machine_map.get(elf_machine, f"unknown ({hex(elf_machine)})")

    is_arm64 = (elf_machine == 183 and elf_class == 2)

    result = (
        f"File: {binary_path} ({os.path.getsize(binary_path)} bytes)\n"
        f"ELF class: {class_str}\n"
        f"Endian: {endian_str}\n"
        f"Machine: {machine_str}\n"
        f"ARM64 target: {'YES' if is_arm64 else 'NO'}"
    )
    return result

@mcp.tool()
def logcat_clear_buffer() -> str:
    """Clear the Android logcat buffer completely."""
    return _adb_run([ADB_BINARY, "logcat", "-c", "-b", "all"], timeout=10)

@mcp.tool()
def logcat_dump_stack_trace(lines: int = 200, filter_tag: str = "") -> str:
    """Dump recent logcat output focusing on stack traces and crash markers.

    Args:
        lines: Number of recent lines to fetch (default 200).
        filter_tag: Optional tag filter (e.g. 'REChainMod:S' for mod logs, 'DEBUG:S' for all).
    """
    cmd = [ADB_BINARY, "logcat", "-d", "-t", str(lines), "-b", "crash"]
    crash_output = _adb_run(cmd, timeout=15)

    cmd_main = [ADB_BINARY, "logcat", "-d", "-t", str(lines)]
    if filter_tag:
        cmd_main += ["-s", filter_tag]
    main_output = _adb_run(cmd_main, timeout=15)

    combined = []
    if crash_output and "FATAL" not in crash_output:
        combined.append("=== CRASH BUFFER ===")
        combined.append(crash_output)
    combined.append("=== MAIN BUFFER ===")
    combined.append(main_output or "(empty)")

    sig_patterns = ["SIGSEGV", "SIGILL", "SIGABRT", "FATAL EXCEPTION", "signal 11", "signal 6"]
    found_signals = [s for s in sig_patterns if s in (crash_output + main_output)]
    if found_signals:
        combined.insert(0, f"!!! SIGNALS DETECTED: {', '.join(found_signals)} !!!")

    return "\n".join(combined)

@mcp.tool()
def logcat_spawn_crash_trap(action: str = "start", filter_expr: str = "SIGSEGV|SIGILL|SIGABRT|FATAL EXCEPTION") -> str:
    """Spawn or manage a non-blocking background crash trap daemon.

    The trap watches the device's crash log buffer in real-time, intercepts fatal signals,
    extracts corrupted memory addresses, and caches them for retrieval.

    Args:
        action: 'start' to begin trapping, 'stop' to halt, 'status' to check, 'fetch' to retrieve crashes.
        filter_expr: Regex filter for signal detection.
    """
    global _crash_trap
    if action == "start":
        if _crash_trap._running:
            return "Crash trap already running"
        _crash_trap.start(filter_expr)
        return f"Crash trap started (filter: {filter_expr})"

    elif action == "stop":
        if not _crash_trap._running:
            return "Crash trap not running"
        _crash_trap.stop()
        return "Crash trap stopped"

    elif action == "status":
        return f"Running: {_crash_trap._running}\nFilter: {_crash_trap._filter}"

    elif action == "fetch":
        if not _crash_trap._running:
            _crash_trap.start(filter_expr)
            time.sleep(2)
        crashes = _crash_trap.get_crashes(timeout=2.0)
        if not crashes:
            return "No crashes captured yet"
        return json.dumps(crashes, indent=2)

    else:
        return f"Unknown action: {action}. Use start|stop|status|fetch."

@mcp.tool()
def analyze_crash_report(log_text: str) -> str:
    """Parse a raw Android crash log (tombstone or FATAL EXCEPTION) into structured data.

    Extracts signal, PID, TID, process name, backtrace frames, and fault library.

    Args:
        log_text: Raw crash log text from logcat or tombstone file.
    """
    if not log_text or len(log_text.strip()) < 10:
        return "ERROR: log_text is empty or too short"

    ctx = CrashContext(raw=log_text)
    patterns = {
        "signal": r"(signal \d+)\s+\(([^)]+)\)",
        "pid": r"pid:\s+(\d+)",
        "tid": r"tid:\s+(\d+)",
        "process_name": r"pid: \d+, tid: \d+, name:\s+(\S+)",
        "timestamp": r"Timestamp:\s+(.+?)(?:\n|$)",
    }
    for key, pat in patterns.items():
        m = re.search(pat, log_text)
        if m:
            setattr(ctx, key, m.group(1))

    signal_direct = re.search(r"(SIGSEGV|SIGILL|SIGABRT|SIGFPE|SIGBUS)", log_text)
    if signal_direct and not ctx.signal:
        ctx.signal = signal_direct.group(1)

    pc_match = re.search(r"pc\s+([0-9a-fA-F]+)", log_text)
    if pc_match:
        ctx.fault_pc = pc_match.group(1)

    for line in log_text.splitlines():
        m = re.match(r"\s*(#[0-9]+)\s+(pc|lr)\s+([0-9a-fA-F]+)\s+(\S+)", line)
        if m:
            frame = {
                "frame": m.group(1),
                "type": m.group(2),
                "address": m.group(3),
                "library": m.group(4),
            }
            ctx.backtrace.append(frame)
            if not ctx.fault_library:
                ctx.fault_library = m.group(4)

    if not ctx.backtrace and not ctx.signal:
        crash_keywords = re.findall(r"(SIGSEGV|SIGILL|SIGABRT|SIGFPE|signal 11|signal 6|signal 4|FATAL EXCEPTION)", log_text)
        if crash_keywords:
            ctx.signal = crash_keywords[0]
        else:
            return "No crash patterns detected in the provided text"

    return json.dumps(ctx.to_dict(), indent=2)

@mcp.tool()
def extract_il2cpp_offsets(log_text: str, lib_name: str = "libil2cpp.so") -> str:
    """Extract method pointer offsets from crash output for a specific il2cpp library.

    Useful for identifying which il2cpp method pointer caused the fault.

    Args:
        log_text: Raw logcat or tombstone text.
        lib_name: Target library name (default libil2cpp.so).
    """
    offsets = []
    for line in log_text.splitlines():
        if lib_name not in line:
            continue
        m = re.search(r"(?:pc|addr)\s+([0-9a-fA-F]+)", line)
        if m:
            offsets.append({"offset": m.group(1), "line": line.strip()})

    if not offsets:
        return f"No offsets found for {lib_name}"
    return json.dumps({"library": lib_name, "offsets": offsets[:50], "total_found": len(offsets)}, indent=2)

@mcp.tool()
def suggest_patch_strategy(crash_report: str) -> str:
    """Analyze a crash report and suggest a patch strategy for the mod's hook code.

    Maps the faulting library and PC offset back to an action plan.

    Args:
        crash_report: Raw crash log text from logcat.
    """
    parsed = json.loads(analyze_crash_report(crash_report))
    if "No crash patterns" in str(parsed) or "ERROR" in str(parsed):
        return str(parsed)

    bt = parsed.get("backtrace", [])
    if not bt:
        return json.dumps({
            "strategy": "unknown",
            "reason": "No backtrace frames found",
        }, indent=2)

    first_frame = bt[0]
    library = first_frame.get("library", "unknown")
    pc = first_frame.get("address", "unknown")
    frame_id = first_frame.get("frame", "#00")

    signal = parsed.get("signal", "unknown")
    pid = parsed.get("pid", "unknown")

    if "libil2cpp.so" in library:
        strategy = "il2cpp_method_hook_corrupted"
        action = (
            "The fault occurred inside libil2cpp.so while executing a hooked method. "
            "1) Check that the function pointer cast in src/main.cpp matches the original method's calling convention. "
            "2) Verify the MethodInfo slot index is valid for the target class. "
            "3) Ensure mprotect() covers the full method body, not just the entry point. "
            "4) Rebuild with ndk_build_module and redeploy."
        )
    elif "libmod.so" in library:
        strategy = "mod_self_fault"
        action = (
            "The fault occurred inside libmod.so itself. "
            "1) Check for null pointer dereferences or out-of-bounds memory access in src/main.cpp. "
            "2) Verify that il2cpp_init() succeeded before using any il2cpp function pointers. "
            "3) Add null checks before calling il2cpp.get_assemblies(), class_get_methods(), etc. "
            "4) Rebuild with ndk_build_module and redeploy."
        )
    elif "libunity.so" in library:
        strategy = "unity_engine_conflict"
        action = (
            "The fault occurred inside libunity.so, likely due to a corrupted Unity internal state. "
            "1) Reduce the scope of hooked methods. "
            "2) Add thread synchronization around il2cpp calls. "
            "3) Consider hooking later in the frame lifecycle. "
        )
    else:
        strategy = "system_library_crash"
        action = (
            f"The fault occurred in {library}, a system or third-party library. "
            "1) Verify the mod does not corrupt memory used by this library. "
            "2) Check for stale function pointers after il2cpp garbage collection. "
        )

    return json.dumps({
        "strategy": strategy,
        "signal": signal,
        "pid": pid,
        "fault_frame": frame_id,
        "fault_library": library,
        "fault_pc": pc,
        "action_plan": action,
        "all_frames": bt,
    }, indent=2)

@mcp.tool()
def build_deploy_loop(max_iterations: int = 5) -> str:
    """Run the full Edit-Compile-Deploy-Debug loop automatically.

    Builds libmod.so, deploys it to /data/local/tmp/libmod.so, restarts com.dts.freefireth,
    traps logcat for 15 seconds, analyzes any crashes, and returns the results.

    Args:
        max_iterations: Maximum number of build-debug cycles (default 5).
    """
    iteration_log = []

    for i in range(1, max_iterations + 1):
        iter_entry = {"iteration": i}
        iteration_log.append(iter_entry)

        build_result = ndk_build_module()
        build_data = json.loads(build_result)
        iter_entry["build"] = build_data
        if build_data.get("status") != "success":
            iter_entry["error"] = "Build failed, cannot deploy"
            break

        binary = LIBS_DIR / "libmod_stripped.so"
        if not binary.exists():
            binary = LIBS_DIR / "libmod.so"
        if not binary.exists():
            iter_entry["error"] = "Binary not found after build"
            break

        remote = "/data/local/tmp/libmod.so"
        push_out = _adb_run([ADB_BINARY, "push", str(binary), remote], timeout=30)
        _adb_shell(f"chmod 755 {remote}", su=True)
        iter_entry["deploy"] = push_out

        stop_out = _adb_shell("am force-stop com.dts.freefireth")
        iter_entry["stop"] = stop_out
        time.sleep(1)

        start_out = _adb_shell("monkey -p com.dts.freefireth 1")
        iter_entry["start"] = start_out

        time.sleep(15)

        logcat_out = logcat_dump_stack_trace(lines=300, filter_tag="REChainMod:S")
        iter_entry["logcat"] = logcat_out[:2000]

        crash_analysis = json.loads(analyze_crash_report(logcat_out))
        iter_entry["crash"] = crash_analysis

        if crash_analysis.get("backtrace") or crash_analysis.get("signal"):
            iter_entry["conclusion"] = "CRASH DETECTED - Review fault PC and patch hook code"
            break
        else:
            iter_entry["conclusion"] = "No crash - iteration stable"

        time.sleep(1)

    final = {
        "iterations_completed": len(iteration_log),
        "max_iterations": max_iterations,
        "log": iteration_log,
    }
    return json.dumps(final, indent=2)

@mcp.tool()
def deploy_payload_with_restart(local_path: str = "", remote_path: str = "/data/local/tmp/libmod.so", package: str = "com.dts.freefireth") -> str:
    """Deploy a payload .so to the device and restart the target package in one step.

    Args:
        local_path: Path to the .so on host. Defaults to libs/libmod_stripped.so.
        remote_path: Destination on device.
        package: Package name to restart.
    """
    if not local_path:
        candidates = [
            LIBS_DIR / "libmod_stripped.so",
            LIBS_DIR / "libmod.so",
        ]
        for c in candidates:
            if c.exists():
                local_path = str(c)
                break
        if not local_path:
            return "ERROR: no compiled module found in libs/. Run build_mod first."

    if not os.path.isfile(local_path):
        return f"ERROR: {local_path} not found"

    steps = []

    push_r = _adb_run([ADB_BINARY, "push", local_path, remote_path], timeout=30)
    steps.append(f"push: {push_r}")
    chmod_r = _adb_shell(f"chmod 755 {remote_path}", su=True)
    steps.append(f"chmod: {chmod_r}")

    stop_r = _adb_shell(f"am force-stop {package}")
    steps.append(f"stop: {stop_r}")
    time.sleep(1)

    start_r = _adb_shell(f"monkey -p {package} 1")
    steps.append(f"start: {start_r}")

    return "\n".join(steps)

@mcp.tool()
def device_info() -> str:
    """Return comprehensive information about the connected Android device."""
    arch = _adb_shell("getprop ro.product.cpu.abi")
    sdk = _adb_shell("getprop ro.build.version.sdk")
    release = _adb_shell("getprop ro.build.version.release")
    brand = _adb_shell("getprop ro.product.brand")
    model = _adb_shell("getprop ro.product.model")
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
        devices_list = ["(error listing devices)"]

    return (
        f"Device: {' '.join(devices_list)}\n"
        f"Arch: {arch}\n"
        f"SDK: {sdk} (Android {release})\n"
        f"Brand: {brand}\n"
        f"Model: {model}\n"
        f"Root: {is_root}"
    )

@mcp.tool()
def project_status() -> str:
    """Return the current project structure, build artifacts, and toolchain status."""
    structure = []
    for root, dirs, files in os.walk(PROJECT_ROOT):
        if ".git" in dirs:
            dirs.remove(".git")
        if "__pycache__" in dirs:
            dirs.remove("__pycache__")
        if "node_modules" in dirs:
            dirs.remove("node_modules")
        rel = os.path.relpath(root, PROJECT_ROOT)
        if rel == ".":
            for f in sorted(files):
                structure.append(f"  {f}")
        else:
            for f in sorted(files):
                structure.append(f"  {rel}/{f}")

    artifacts = []
    for f in sorted(LIBS_DIR.glob("*")):
        mtime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(f.stat().st_mtime))
        artifacts.append(f"{f.name} ({f.stat().st_size} bytes, modified {mtime})")

    ndk_ok = os.path.isfile(NDK_CLANG)
    ndk_version = "25.2.9519653"
    adb_ok = False
    adb_version = "unknown"
    try:
        r = subprocess.run([ADB_BINARY, "version"], capture_output=True, text=True, timeout=5)
        adb_ok = True
        adb_version = r.stdout.splitlines()[0] if r.stdout else "unknown"
    except Exception:
        pass

    hooks_available = 0
    if os.path.exists(INCLUDE_DIR / "il2cpp.h"):
        with open(INCLUDE_DIR / "il2cpp.h") as f:
            hooks_available = sum(1 for line in f if "il2cpp_" in line and "fn" in line and "//" not in line)

    patch_count = len(list(PATCHES_DIR.glob("*.py"))) + len(list(PATCHES_DIR.glob("*.patch")))
    log_count = len(list(LOGS_DIR.glob("*.log")))

    return (
        f"Project: {PROJECT_ROOT.name}\n"
        f"Root: {PROJECT_ROOT}\n"
        f"Workspace: {os.path.getsize(str(PROJECT_ROOT))} bytes across {len(structure)} paths\n"
        f"\n--- Toolchain ---\n"
        f"NDK ({'OK' if ndk_ok else 'MISSING'}): {NDK_BASE} (v{ndk_version})\n"
        f"ADB ({'OK' if adb_ok else 'MISSING'}): {adb_version}\n"
        f"Arm64 Clang: {NDK_CLANG}\n"
        f"Arm64 Strip: {NDK_STRIP}\n"
        f"Sysroot: {NDK_SYSROOT}\n"
        f"\n--- Source Files ---\n"
        + "\n".join(structure) +
        f"\n\n--- Build Artifacts ---\n" +
        ("\n".join(artifacts) if artifacts else "(none)") +
        f"\n\n--- Patches & Logs ---\n" +
        f"Patches available: {patch_count}\n" +
        f"Log files stored: {log_count}\n" +
        f"\n--- Config ---\n"
        f"ADB target: {ADB_HOST}:{ADB_PORT}\n"
        f"Module output: {LIBS_DIR}\n"
        f"il2cpp API functions available: {hooks_available}"
    )

def main():
    logcat_clear_buffer()
    mcp.run()

if __name__ == "__main__":
    main()