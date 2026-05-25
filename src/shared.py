import os
import platform
import subprocess
import time
import re
import json
import threading
import queue
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field

HOST_OS = platform.system().lower()
IS_MACOS = HOST_OS == "darwin"
IS_LINUX = HOST_OS == "linux"
IS_WINDOWS = HOST_OS == "windows"

if IS_WINDOWS:
    ADB_BINARY = "adb.exe"
    _HOST_TAG = "windows-x86_64"
elif IS_MACOS:
    ADB_BINARY = "adb"
    import platform as _p
    _HOST_TAG = "darwin-x86_64" if _p.machine() != "arm64" else "darwin-aarch64"
else:
    ADB_BINARY = "adb"
    _HOST_TAG = "linux-x86_64"

ADB_HOST = "127.0.0.1"
ADB_PORT = 5555

NDK_BASE = os.environ.get("ANDROID_NDK_HOME", "")
if not NDK_BASE:
    for _candidate in [
        "/opt/homebrew/share/android-commandlinetools/ndk/25.2.9519653",
        "/usr/local/share/android-ndk",
        os.path.expanduser("~/Android/Sdk/ndk/25.2.9519653"),
        os.path.expanduser("~/android-ndk"),
    ]:
        if os.path.isdir(_candidate):
            NDK_BASE = _candidate
            break

NDK_TOOLCHAIN = f"{NDK_BASE}/toolchains/llvm/prebuilt/{_HOST_TAG}" if NDK_BASE else ""
NDK_CLANG = f"{NDK_TOOLCHAIN}/bin/aarch64-linux-android21-clang" if NDK_TOOLCHAIN else ""
NDK_CLANGXX = f"{NDK_TOOLCHAIN}/bin/aarch64-linux-android21-clang++" if NDK_TOOLCHAIN else ""
NDK_STRIP = f"{NDK_TOOLCHAIN}/bin/llvm-strip" if NDK_TOOLCHAIN else ""
NDK_SYSROOT = f"{NDK_TOOLCHAIN}/sysroot" if NDK_TOOLCHAIN else ""
NDK_MAKE = f"{NDK_BASE}/prebuilt/{_HOST_TAG}/bin/make" if NDK_BASE else ""
NDK_CMAKE_TOOLCHAIN = f"{NDK_BASE}/build/cmake/android.toolchain.cmake" if NDK_BASE else ""

GHIDRA_HOME = os.environ.get("GHIDRA_HOME", "")
if not GHIDRA_HOME:
    for _candidate in [
        "/opt/ghidra",
        "/opt/ghidra_*",
        os.path.expanduser("~/ghidra"),
        os.path.expanduser("~/tools/ghidra"),
    ]:
        if _candidate.endswith("*"):
            import glob as _glob
            matches = sorted(_glob.glob(_candidate))
            if matches:
                GHIDRA_HOME = matches[-1]
                break
        elif os.path.isdir(_candidate):
            # Look for actual ghidra_* subdirectory inside (e.g. /opt/ghidra/ghidra_11.2)
            subdirs = sorted([d for d in Path(_candidate).iterdir() if d.name.startswith("ghidra_") and d.is_dir()])
            if subdirs:
                GHIDRA_HOME = str(subdirs[-1])
            else:
                GHIDRA_HOME = _candidate
            break

GHIDRA_ANALYZE = f"{GHIDRA_HOME}/support/analyzeHeadless" if GHIDRA_HOME else ""

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LIBS_DIR = PROJECT_ROOT / "libs"
SRC_DIR = PROJECT_ROOT / "src"
INCLUDE_DIR = PROJECT_ROOT / "include"
PATCHES_DIR = PROJECT_ROOT / "patches"
LOGS_DIR = PROJECT_ROOT / "logs"

for d in [LIBS_DIR, PATCHES_DIR, LOGS_DIR]:
    d.mkdir(exist_ok=True)

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
        if self._running: return
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
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
        except FileNotFoundError:
            self._queue.put("FATAL: adb not found")
            self._running = False
            return
        buffer = []
        while self._running:
            try:
                line = proc.stdout.readline()
                if not line:
                    time.sleep(0.1); continue
                if self._filter and re.search(self._filter, line, re.IGNORECASE):
                    buffer.append(line.strip())
                    for _ in range(50):
                        extra = proc.stdout.readline()
                        if not extra: break
                        buffer.append(extra.strip())
                        if re.match(r"^\s*$", extra): break
                    crash_text = "\n".join(buffer)
                    parsed = self._parse_crash_block(crash_text)
                    self._queue.put(parsed.to_dict() if parsed else crash_text)
                    buffer = []
            except Exception as exc:
                self._queue.put(f"TRAP ERROR: {exc}"); break
        proc.terminate()

    def _parse_crash_block(self, text: str) -> Optional[CrashContext]:
        ctx = CrashContext(raw=text)
        for key, pat in {"signal": r"(signal \d+)\s+\(([^)]+)\)", "pid": r"pid:\s+(\d+)", "tid": r"tid:\s+(\d+)", "process_name": r"pid: \d+, tid: \d+, name:\s+(\S+)"}.items():
            m = re.search(pat, text)
            if m: setattr(ctx, key, m.group(2) if key == "signal" else m.group(1))
        m = re.search(r"pc\s+([0-9a-fA-F]+)", text)
        if m: ctx.fault_pc = m.group(1)
        for line in text.splitlines():
            m = re.match(r"\s*(#[0-9]+)\s+(pc|lr)\s+([0-9a-fA-F]+)\s+(\S+)", line)
            if m:
                ctx.backtrace.append({"frame": m.group(1), "type": m.group(2), "address": m.group(3), "library": m.group(4)})
                if not ctx.fault_library: ctx.fault_library = m.group(4)
        if not ctx.signal:
            m = re.search(r"(SIGSEGV|SIGILL|SIGABRT|SIGFPE)", text)
            if m: ctx.signal = m.group(1)
        if ctx.backtrace or ctx.signal: return ctx
        return None

    def get_crashes(self, timeout: float = 1.0) -> list:
        results = []
        try:
            results.append(self._queue.get(timeout=timeout))
            while True:
                results.append(self._queue.get_nowait())
        except queue.Empty:
            pass
        return results

_crash_trap = CrashTrapDaemon()

_ADB_RETRIES = 3

def _adb_run(cmd: list[str], timeout: int = 30) -> str:
    last_err = ""
    for attempt in range(_ADB_RETRIES):
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            out = r.stdout.strip()
            if r.stderr: out += "\nSTDERR: " + r.stderr.strip()
            if r.returncode != 0 and not out:
                last_err = f"EXIT_CODE_{r.returncode}: {r.stderr.strip()}"
                if attempt < _ADB_RETRIES - 1:
                    time.sleep(1 * (attempt + 1))
                    continue
                return last_err
            return out
        except FileNotFoundError:
            return "FATAL: adb binary not found on PATH. Install platform-tools."
        except subprocess.TimeoutExpired:
            last_err = f"TIMEOUT: command exceeded {timeout}s limit (attempt {attempt+1})"
            time.sleep(1)
        except Exception as e:
            last_err = f"ERROR: {e}"
            break
    return last_err

def _adb_shell(command: str, su: bool = False) -> str:
    cmd = [ADB_BINARY, "shell"]
    if su:
        cmd += ["su", "-c", command]
    else:
        cmd += [command]
    return _adb_run(cmd, timeout=30)

def _check_ndk_toolchain() -> Optional[str]:
    if not NDK_CLANG or not os.path.isfile(NDK_CLANG):
        return (f"NDK clang not found at {NDK_CLANG}. "
                f"Set ANDROID_NDK_HOME to your NDK r25+ root. "
                f"Detected host: {HOST_OS}/{_HOST_TAG}")
    return None

def _parse_ndk_errors(stderr: str, stdout: str) -> str:
    if not stderr and not stdout:
        return json.dumps({"status": "success", "errors": [], "warnings": []})
    errors, warnings = [], []
    for line in stderr.splitlines():
        if "error:" in line.lower(): errors.append(line.strip())
        elif "warning:" in line.lower(): warnings.append(line.strip())
    for line in stdout.splitlines():
        if "error:" in line.lower(): errors.append(line.strip())
        elif "warning:" in line.lower(): warnings.append(line.strip())
    return json.dumps({"status": "failed" if errors else "success", "errors": errors[:30], "warnings": warnings[:30],
                        "raw_stderr_length": len(stderr), "raw_stdout_length": len(stdout)})
