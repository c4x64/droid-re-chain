import os
import subprocess
import time
import re
import json
import threading
import queue
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field

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
                ctx.backtrace.append({"frame": m.group(1), "type": m.group(2), "address": m.group(3), "library": m.group(4)})
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
                results.append(self._queue.get_nowait())
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