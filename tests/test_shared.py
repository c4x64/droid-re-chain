"""Comprehensive tests for shared.py — the most critical module."""
import os
import sys
import json
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.shared import (HOST_OS, IS_MACOS, IS_LINUX, IS_WINDOWS,
                        ADB_BINARY, NDK_BASE, NDK_CLANG, NDK_TOOLCHAIN,
                        NDK_STRIP, NDK_MAKE, NDK_CMAKE_TOOLCHAIN,
                        NDK_SYSROOT, _HOST_TAG,
                        CrashContext, CrashTrapDaemon,
                        _adb_run, _adb_shell, _check_ndk_toolchain,
                        _parse_ndk_errors, _ADB_RETRIES,
                        ADB_HOST, ADB_PORT, LIBS_DIR, LOGS_DIR,
                        PROJECT_ROOT, PATCHES_DIR, SRC_DIR, INCLUDE_DIR)


def test_os_detection():
    assert HOST_OS in ("darwin", "linux", "windows")
    assert isinstance(IS_MACOS, bool)
    assert isinstance(IS_LINUX, bool)
    assert isinstance(IS_WINDOWS, bool)
    assert sum([IS_MACOS, IS_LINUX, IS_WINDOWS]) == 1


def test_host_tag_format():
    parts = _HOST_TAG.split("-")
    assert len(parts) >= 2
    assert parts[0] in ("darwin", "linux", "windows")
    assert parts[1] in ("x86_64", "aarch64")


def test_adb_binary():
    if IS_WINDOWS:
        assert ADB_BINARY == "adb.exe"
    else:
        assert ADB_BINARY == "adb"


def test_adb_host_port():
    assert isinstance(ADB_HOST, str)
    assert isinstance(ADB_PORT, int)
    assert ADB_PORT > 0


def test_adb_retries():
    assert _ADB_RETRIES >= 1
    assert isinstance(_ADB_RETRIES, int)


def test_directory_existence():
    assert isinstance(PROJECT_ROOT, Path)
    assert isinstance(SRC_DIR, Path)
    assert isinstance(INCLUDE_DIR, Path)
    assert isinstance(LIBS_DIR, Path)
    assert isinstance(LOGS_DIR, Path)
    assert isinstance(PATCHES_DIR, Path)
    assert SRC_DIR.exists()
    assert INCLUDE_DIR.exists()
    assert PROJECT_ROOT.exists()


def test_ndk_paths():
    if NDK_BASE:
        assert os.path.isdir(NDK_BASE)
    assert isinstance(NDK_CLANG, str)
    assert isinstance(NDK_TOOLCHAIN, str)
    assert isinstance(NDK_STRIP, str)
    assert isinstance(NDK_MAKE, str)
    assert isinstance(NDK_CMAKE_TOOLCHAIN, str)
    assert isinstance(NDK_SYSROOT, str)


def test_ndk_clang_contains_arch():
    if NDK_CLANG:
        assert "aarch64" in NDK_CLANG or "arm64" in NDK_CLANG
        assert "clang" in NDK_CLANG


def test_ndk_toolchain_contains_host():
    if NDK_TOOLCHAIN:
        assert _HOST_TAG in NDK_TOOLCHAIN


def test_ndk_cmake_toolchain():
    if NDK_CMAKE_TOOLCHAIN:
        assert "android.toolchain.cmake" in NDK_CMAKE_TOOLCHAIN


def test_check_ndk_toolchain():
    result = _check_ndk_toolchain()
    if NDK_BASE and os.path.isfile(NDK_CLANG):
        assert result is None
    else:
        assert result is not None
        assert "Set ANDROID_NDK_HOME" in result or "not found" in result


def test_ndk_fallback_not_found():
    original = os.environ.get("ANDROID_NDK_HOME", "")
    try:
        os.environ.pop("ANDROID_NDK_HOME", None)
        import importlib
        import src.shared as shared
        importlib.reload(shared)
        if not shared.NDK_BASE:
            assert shared._check_ndk_toolchain() is not None
    finally:
        if original:
            os.environ["ANDROID_NDK_HOME"] = original


def test_parse_ndk_errors_empty():
    result = _parse_ndk_errors("", "")
    assert "success" in result


def test_parse_ndk_errors_error():
    result = _parse_ndk_errors("error: foo", "")
    parsed = json.loads(result)
    assert parsed["status"] == "failed"
    assert len(parsed["errors"]) == 1


def test_parse_ndk_errors_warning():
    result = _parse_ndk_errors("warning: bar", "")
    parsed = json.loads(result)
    assert parsed["status"] == "success"
    assert len(parsed["warnings"]) == 1


def test_parse_ndk_errors_mixed():
    result = _parse_ndk_errors("error: X\nwarning: Y\ninfo: Z", "")
    parsed = json.loads(result)
    assert parsed["status"] == "failed"
    assert len(parsed["errors"]) == 1
    assert len(parsed["warnings"]) == 1


def test_parse_ndk_errors_stdout_scan():
    result = _parse_ndk_errors("", "error: in stdout")
    parsed = json.loads(result)
    assert len(parsed["errors"]) >= 1


def test_parse_ndk_errors_limits():
    errors = "\n".join([f"error: line {i}" for i in range(100)])
    result = json.loads(_parse_ndk_errors(errors, ""))
    assert len(result["errors"]) == 30


class TestCrashContext:
    def test_defaults(self):
        ctx = CrashContext()
        assert ctx.timestamp == ""
        assert ctx.signal == ""
        assert ctx.pid == ""
        assert ctx.tid == ""
        assert ctx.process_name == ""
        assert ctx.fault_library == ""
        assert ctx.fault_pc == ""
        assert ctx.backtrace == []
        assert ctx.raw == ""
        d = ctx.to_dict()
        assert d["raw_length"] == 0
        assert d["backtrace"] == []

    def test_with_data(self):
        ctx = CrashContext(signal="SIGSEGV", pid="1234", tid="5678",
                           process_name="com.test", raw="crash data")
        assert ctx.signal == "SIGSEGV"
        d = ctx.to_dict()
        assert d["signal"] == "SIGSEGV"
        assert d["pid"] == "1234"
        assert d["tid"] == "5678"
        assert d["process_name"] == "com.test"
        assert d["raw_length"] == 10

    def test_with_backtrace(self):
        bt = [{"frame": "#00", "type": "pc", "address": "0x1234", "library": "libc.so"}]
        ctx = CrashContext(backtrace=bt)
        assert len(ctx.backtrace) == 1
        assert ctx.backtrace[0]["library"] == "libc.so"
        d = ctx.to_dict()
        assert len(d["backtrace"]) == 1


class TestCrashTrapDaemon:
    def test_parse_crash_block_signal(self):
        daemon = CrashTrapDaemon()
        text = "FATAL EXCEPTION: main\nProcess: com.test\nsignal 11 (SIGSEGV)"
        ctx = daemon._parse_crash_block(text)
        assert ctx is not None
        assert ctx.signal == "signal 11"
        assert ctx.process_name == ""

    def test_parse_crash_block_full(self):
        daemon = CrashTrapDaemon()
        text = """FATAL EXCEPTION: main
Process: com.test
pid: 1234, tid: 5678, name: com.test.thread
signal 6 (SIGABRT)
pc 0000abcd  libc.so
#00 pc 00001234  libutils.so
#01 lr 00005678  libil2cpp.so
"""
        ctx = daemon._parse_crash_block(text)
        assert ctx is not None
        assert ctx.signal == "signal 6"
        assert ctx.pid == "1234"
        assert ctx.tid == "5678"
        assert ctx.process_name == "com.test.thread"
        assert ctx.fault_pc == "0000abcd"
        assert len(ctx.backtrace) == 2
        assert ctx.backtrace[0]["frame"] == "#00"
        assert ctx.backtrace[0]["library"] == "libutils.so"
        assert ctx.backtrace[1]["library"] == "libil2cpp.so"
        assert ctx.fault_library == "libutils.so"

    def test_parse_crash_block_no_match(self):
        daemon = CrashTrapDaemon()
        ctx = daemon._parse_crash_block("normal logcat line")
        assert ctx is None

    def test_parse_crash_block_signal_only(self):
        daemon = CrashTrapDaemon()
        ctx = daemon._parse_crash_block("some log noise\nSIGFPE\ntrailing")
        assert ctx is not None
        assert ctx.signal == "SIGFPE"

    def test_parse_crash_block_empty(self):
        daemon = CrashTrapDaemon()
        ctx = daemon._parse_crash_block("")
        assert ctx is None

    def test_parse_crash_block_multiline_signal(self):
        daemon = CrashTrapDaemon()
        text = "SIGSEGV\npc 00007fff\n#00 pc 00001000  libfoo.so\n"
        ctx = daemon._parse_crash_block(text)
        assert ctx is not None
        assert ctx.signal == "SIGSEGV"

    def test_start_stop(self):
        daemon = CrashTrapDaemon()
        daemon.start()
        assert daemon._running is True
        daemon.stop()
        assert daemon._running is False

    def test_get_crashes_empty(self):
        daemon = CrashTrapDaemon()
        assert daemon.get_crashes() == []

    def test_double_start(self):
        daemon = CrashTrapDaemon()
        daemon.start()
        daemon.start()
        assert daemon._running is True
        daemon.stop()

    def test_set_filter_default(self):
        daemon = CrashTrapDaemon()
        assert daemon._filter == ""
        daemon.start()
        assert "SIGSEGV" in daemon._filter
        daemon.stop()


def test_adb_run_invalid():
    result = _adb_run(["nonexistent_adb_binary_xyz"], timeout=5)
    assert "FATAL" in result


def test_adb_shell_invalid():
    result = _adb_shell("echo test", su=False)
    assert isinstance(result, str)
    assert len(result) > 0


def test_adb_run_empty_command():
    result = _adb_run([], timeout=5)
    assert isinstance(result, str)


def test_adb_run_retry_message():
    result = _adb_run(["nonexistent_adb"], timeout=3)
    assert "FATAL" in result or "ERROR" in result


def test_adb_run_timeout_message():
    result = _adb_run(["nonexistent_adb"], timeout=1)
    assert isinstance(result, str)


if __name__ == "__main__":
    import subprocess
    r = subprocess.run([sys.executable, "-m", "pytest", __file__, "-v"], capture_output=True, text=True)
    print(r.stdout)
    if r.returncode != 0:
        print(r.stderr)
        sys.exit(1)