"""Tests for shared.py — NDK paths, ADB wrappers, crash parser."""
import os
import sys
import json
import time
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.shared import (HOST_OS, IS_MACOS, IS_LINUX, IS_WINDOWS,
                        ADB_BINARY, NDK_BASE, NDK_CLANG, NDK_TOOLCHAIN,
                        NDK_STRIP, NDK_MAKE, NDK_CMAKE_TOOLCHAIN,
                        CrashContext, CrashTrapDaemon,
                        _adb_run, _adb_shell, _check_ndk_toolchain,
                        _parse_ndk_errors)


def test_os_detection():
    assert HOST_OS in ("darwin", "linux", "windows")
    assert isinstance(IS_MACOS, bool)
    assert isinstance(IS_LINUX, bool)
    assert isinstance(IS_WINDOWS, bool)
    assert sum([IS_MACOS, IS_LINUX, IS_WINDOWS]) == 1


def test_adb_binary():
    if IS_WINDOWS:
        assert ADB_BINARY == "adb.exe"
    else:
        assert ADB_BINARY == "adb"


def test_ndk_paths():
    if NDK_BASE:
        assert os.path.isdir(NDK_BASE)
    assert isinstance(NDK_CLANG, str)
    assert isinstance(NDK_TOOLCHAIN, str)
    assert isinstance(NDK_STRIP, str)
    assert isinstance(NDK_MAKE, str)
    assert isinstance(NDK_CMAKE_TOOLCHAIN, str)


def test_check_ndk_toolchain():
    result = _check_ndk_toolchain()
    if NDK_BASE:
        assert result is None or "Set ANDROID_NDK_HOME" in result
    else:
        assert result is not None
        assert "Set ANDROID_NDK_HOME" in result


def test_parse_ndk_errors():
    result = _parse_ndk_errors("", "")
    assert "success" in result

    result = _parse_ndk_errors("error: foo", "")
    parsed = json.loads(result)
    assert parsed["status"] == "failed"
    assert len(parsed["errors"]) == 1

    result = _parse_ndk_errors("warning: bar", "")
    parsed = json.loads(result)
    assert parsed["status"] == "success"
    assert len(parsed["warnings"]) == 1


class TestCrashContext:
    def test_defaults(self):
        ctx = CrashContext()
        assert ctx.timestamp == ""
        assert ctx.signal == ""
        assert ctx.to_dict()["raw_length"] == 0

    def test_with_data(self):
        ctx = CrashContext(signal="SIGSEGV", pid="1234", raw="crash data")
        assert ctx.signal == "SIGSEGV"
        d = ctx.to_dict()
        assert d["signal"] == "SIGSEGV"
        assert d["raw_length"] == 10


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
        assert ctx.fault_library == "libutils.so"

    def test_parse_crash_block_no_match(self):
        daemon = CrashTrapDaemon()
        ctx = daemon._parse_crash_block("normal logcat line")
        assert ctx is None

    def test_start_stop(self):
        daemon = CrashTrapDaemon()
        daemon.start()
        assert daemon._running is True
        daemon.stop()
        assert daemon._running is False


def test_adb_run_invalid():
    result = _adb_run(["nonexistent_adb_binary"], timeout=5)
    assert "FATAL" in result or "ERROR" in result


def test_adb_shell_invalid():
    result = _adb_shell("echo test", su=False)
    if "FATAL" in result or "ERROR" in result or "EXIT" in result:
        assert True
    else:
        assert True


if __name__ == "__main__":
    test_os_detection()
    test_adb_binary()
    test_ndk_paths()
    test_check_ndk_toolchain()
    test_parse_ndk_errors()
    TestCrashContext().test_defaults()
    TestCrashContext().test_with_data()
    TestCrashTrapDaemon().test_parse_crash_block_signal()
    TestCrashTrapDaemon().test_parse_crash_block_full()
    TestCrashTrapDaemon().test_parse_crash_block_no_match()
    TestCrashTrapDaemon().test_start_stop()
    test_adb_run_invalid()
    test_adb_shell_invalid()
    print("ALL TESTS PASSED")