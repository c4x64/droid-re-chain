"""15 Runtime Diagnostics & Logcat Trapping tools."""
import json
import time
from src.shared import (
    _adb_run, _adb_shell, _crash_trap,
    ADB_BINARY, LOGS_DIR,
)

def register(mcp):

    @mcp.tool()
    def trap_clear_buffers() -> str:
        """Flush Android logcat diagnostic buffers completely."""
        return _adb_run([ADB_BINARY, "logcat", "-c", "-b", "all"], timeout=10)

    @mcp.tool()
    def trap_start_stream(filter_expr: str = "REChainMod") -> str:
        """Spawn background thread capturing the emulator log stream. Args: filter_expr."""
        _crash_trap.start()
        return f"Log stream started with filter: {filter_expr}"

    @mcp.tool()
    def trap_stop_stream() -> str:
        """Safely close log processing handlers to free system resources."""
        _crash_trap.stop()
        return "Log stream stopped"

    @mcp.tool()
    def trap_set_filter(filter_expr: str = "SIGSEGV|SIGILL|SIGABRT|FATAL EXCEPTION") -> str:
        """Apply priority logging tags to limit to critical errors. Args: filter_expr."""
        _crash_trap._filter = filter_expr
        return f"Trap filter set to: {filter_expr}"

    @mcp.tool()
    def trap_scan_crash_signals(duration_sec: int = 5) -> str:
        """Monitor log streams to intercept fatal crashes. Args: duration_sec."""
        if not _crash_trap._running:
            _crash_trap.start()
        time.sleep(duration_sec)
        crashes = _crash_trap.get_crashes(timeout=2.0)
        if not crashes:
            return f"No crashes detected in {duration_sec}s"
        return json.dumps(crashes, indent=2)

    @mcp.tool()
    def trap_extract_pc_register(crash_log: str) -> str:
        """Extract Program Counter addresses from raw crash dumps. Args: crash_log."""
        import re
        pcs = re.findall(r"pc\s+([0-9a-fA-F]+)", crash_log)
        if not pcs:
            return "No PC values found"
        return "\n".join(f"PC: 0x{pc}" for pc in pcs[:20])

    @mcp.tool()
    def trap_parse_stack_trace(crash_log: str) -> str:
        """Convert raw crash lines into prioritized address list. Args: crash_log."""
        frames = []
        import re
        for line in crash_log.splitlines():
            m = re.match(r"\s*(#[0-9]+)\s+(pc|lr)\s+([0-9a-fA-F]+)\s+(\S+)", line)
            if m:
                frames.append({"frame": m.group(1), "type": m.group(2), "address": m.group(3), "library": m.group(4)})
        if not frames:
            return "No backtrace frames found"
        return json.dumps(frames, indent=2)

    @mcp.tool()
    def trap_isolate_fault_address(crash_log: str) -> str:
        """Identify exact memory address triggering page violation. Args: crash_log."""
        import re
        m = re.search(r"fault addr\s+([0-9a-fA-Fx]+)", crash_log)
        if m:
            return f"Fault address: {m.group(1)}"
        m = re.search(r"(?:SIGSEGV|SIGBUS).*?addr\s+([0-9a-fA-Fx]+)", crash_log)
        if m:
            return f"Fault address: {m.group(1)}"
        return "No fault address found"

    @mcp.tool()
    def trap_map_fault_to_rva(fault_pc: str, base_address: str = "0x0") -> str:
        """Subtract base from fault to pinpoint broken code block. Args: fault_pc, base_address."""
        try:
            pc = int(fault_pc, 16) if fault_pc.startswith("0x") else int(fault_pc, 16)
            base = int(base_address, 16) if base_address.startswith("0x") else int(base_address, 16)
            rva = pc - base
            return f"PC: 0x{fault_pc}\nBase: 0x{base:x}\nRVA: 0x{rva:x}"
        except ValueError:
            return f"RVA: {fault_pc} - {base_address}"

    @mcp.tool()
    def trap_dump_native_heap(pid: str = "") -> str:
        """Capture raw memory allocation states near active modules. Args: pid."""
        if not pid:
            return "ERROR: PID required"
        return _adb_shell(f"su -c 'cat /proc/{pid}/maps | grep -E \"(libil2cpp|libunity|libmod)\"'", su=True)

    @mcp.tool()
    def trap_monitor_anr() -> str:
        """Monitor system paths to detect app unresponsiveness."""
        return _adb_shell("ls -la /data/anr/ 2>/dev/null || echo 'no ANR traces found'", su=True)

    @mcp.tool()
    def trap_capture_tombstone(output_dir: str = "") -> str:
        """Locate and pull Android system tombstone diagnostic reports. Args: output_dir."""
        if not output_dir:
            output_dir = str(LOGS_DIR)
        result = _adb_shell("ls -la /data/tombstones/ 2>/dev/null || echo 'no tombstones'", su=True)
        if "no tombstones" in result:
            return "No tombstones found on device"
        return f"Tombstones available:\n{result}\nUse adb_pull_data to retrieve"

    @mcp.tool()
    def trap_log_custom_payload(tag: str = "REChainMod", message: str = "") -> str:
        """Format debug inputs through __android_log_print. Args: tag, message."""
        import json
        return json.dumps({"tag": tag, "msg": message, "code": f'__android_log_print(ANDROID_LOG_INFO, "{tag}", "{message}");'}, indent=2)

    @mcp.tool()
    def trap_get_thread_list(package: str = "") -> str:
        """List active process execution handles. Args: package."""
        if package:
            return _adb_shell(f"ps -ef | grep {package} | head -20")
        return _adb_shell("ps -ef | head -30")

    @mcp.tool()
    def trap_detect_anticheat_log() -> str:
        """Scan log streams for integrity monitor check failures."""
        return _adb_run([ADB_BINARY, "logcat", "-d", "-t", "200", "-s", "Unity:*", "DEBUG:*"], timeout=15)
