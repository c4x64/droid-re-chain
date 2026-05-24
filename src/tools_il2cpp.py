import re
from pathlib import Path
from typing import Any


def parse_crash(log_text: str) -> dict[str, Any] | None:
    if not log_text:
        return None

    crash: dict[str, Any] = {}
    patterns = {
        "signal": r"(signal \d+)\s+\(([^)]+)\)",
        "fault_addr": r"fault addr\s+([0-9a-fA-Fx]+)",
        "pc": r"pc\s+([0-9a-fA-F]+)",
        "lr": r"lr\s+([0-9a-fA-F]+)",
        "sp": r"sp\s+([0-9a-fA-F]+)",
        "pid": r"pid:\s+(\d+)",
        "tid": r"tid:\s+(\d+)",
        "process_name": r"pid: \d+, tid: \d+, name:\s+(\S+)",
        "timestamp": r"Timestamp:\s+(.+?)(?:\n|$)",
        "abi": r"ABI:\s+'([^']+)'",
    }
    for key, pat in patterns.items():
        m = re.search(pat, log_text)
        if m:
            crash[key] = m.group(1)

    backtrace: list[dict[str, str]] = []
    for line in log_text.splitlines():
        m = re.match(r"\s*(#[0-9]+)\s+(pc|lr)\s+([0-9a-fA-F]+)\s+(\S+)", line)
        if m:
            backtrace.append({
                "frame": m.group(1),
                "type": m.group(2),
                "address": m.group(3),
                "library": m.group(4),
            })
    if backtrace:
        crash["backtrace"] = backtrace
        crash["fault_library"] = backtrace[0]["library"]

    return crash if (backtrace or "signal" in crash) else None


def extract_crashes(log_text: str) -> list[dict[str, Any]]:
    crashes: list[dict[str, Any]] = []
    for block in re.split(r"(?=--------- crashed tombstones)", log_text):
        parsed = parse_crash(block)
        if parsed:
            crashes.append(parsed)
    for m in re.finditer(
        r"(?:FATAL EXCEPTION|SIGSEGV|SIGABRT|SIGILL).*?(?=\n---|\Z)",
        log_text, re.DOTALL,
    ):
        parsed = parse_crash(m.group(0))
        if parsed and parsed not in crashes:
            crashes.append(parsed)
    return crashes


def extract_method_offsets(
    logcat_dump: str, lib_name: str = "libil2cpp.so",
) -> list[dict[str, str]]:
    offsets: list[dict[str, str]] = []
    for line in logcat_dump.splitlines():
        if lib_name not in line:
            continue
        m = re.search(r"(?:pc|addr)\s+([0-9a-fA-F]+)", line)
        if m:
            offsets.append({"offset": m.group(1), "line": line.strip()})
    return offsets


def suggest_patch(crash: dict[str, Any]) -> dict[str, str] | None:
    bt = crash.get("backtrace", [])
    if not bt:
        return None
    return {
        "fault_library": crash.get("fault_library", ""),
        "fault_pc": bt[0].get("address", ""),
        "fault_frame": bt[0].get("frame", ""),
        "suggestion": "strip fault offset, re-analyze with Ghidra/IDA, "
                      "then patch src/main.cpp and re-run build_deploy_loop",
    }


def register(mcp):
    """Register all il2cpp / crash-analysis tools with the FastMCP server."""

    @mcp.tool()
    def analyze_crash(log_text: str) -> str:
        """Parse a crash log and extract structured backtrace, signal, and fault info.

        Handles tombstone and FATAL EXCEPTION formats. Returns JSON-like fields
        for immediate consumption by the patch loop.

        Args:
            log_text: Raw tombstone or logcat crash output.
        """
        parsed = parse_crash(log_text)
        if not parsed:
            crashes = extract_crashes(log_text)
            if not crashes:
                return "No crash pattern detected in the provided text"
            parsed = crashes[0]

        if "backtrace" in parsed:
            bt_lines = []
            for f in parsed["backtrace"]:
                bt_lines.append(
                    f"  {f['frame']} {f['type']} {f['address']} {f['library']}"
                )
            return (
                f"Signal: {parsed.get('signal', 'N/A')}\n"
                f"PID: {parsed.get('pid', 'N/A')}  "
                f"TID: {parsed.get('tid', 'N/A')}\n"
                f"Fault lib: {parsed.get('fault_library', 'N/A')}\n"
                f"Backtrace:\n" + "\n".join(bt_lines)
            )
        return str(parsed)

    @mcp.tool()
    def extract_crash_offsets(log_text: str, lib_name: str = "libil2cpp.so") -> str:
        """Extract method pointer offsets from crash output for a specific library.

        Useful for identifying which il2cpp method caused the fault.

        Args:
            log_text: Raw logcat/tombstone text.
            lib_name: Library to filter offsets for (default libil2cpp.so).
        """
        offsets = extract_method_offsets(log_text, lib_name)
        if not offsets:
            return f"No offsets found for {lib_name}"
        lines = [f"Offset: {o['offset']}" for o in offsets[:50]]
        return "\n".join(lines)

    @mcp.tool()
    def suggest_patch_target(crash_report: str) -> str:
        """Suggest a patch target based on crash analysis.

        Ingests raw crash text, parses it, and returns a structured recommendation
        for which source file to modify and which offset to target.

        Args:
            crash_report: Raw crash log text from logcat or tombstone.
        """
        parsed = parse_crash(crash_report)
        if not parsed:
            crashes = extract_crashes(crash_report)
            if not crashes:
                return "No crash detected. Cannot suggest a patch target."
            parsed = crashes[0]
        suggestion = suggest_patch(parsed)
        if not suggestion:
            return "Crash has no backtrace. Cannot determine patch target."
        return (
            f"Fault library: {suggestion['fault_library']}\n"
            f"Fault PC: {suggestion['fault_pc']}\n"
            f"Frame: {suggestion['fault_frame']}\n"
            f"=== SUGGESTED ACTION ===\n"
            f"{suggestion['suggestion']}"
        )

    @mcp.tool()
    def pull_il2cpp(package: str = "com.dts.freefireth") -> str:
        """Locate and pull libil2cpp.so from a target package on the device.

        Args:
            package: Android package name to search for il2cpp in.
        """
        from src.tools_adb import shell, pull
        remote_paths = shell(
            f"su -c 'find /data/app/{package}* -name \"libil2cpp.so\" 2>/dev/null'"
        )
        if not remote_paths or "No such file" in remote_paths or "ERROR" in remote_paths:
            return f"libil2cpp.so not found for package '{package}'"

        remote = remote_paths.strip().splitlines()[0]
        local = str(Path(__file__).resolve().parent.parent / "libs" / "libil2cpp.so")
        try:
            result = pull(remote, local)
            return f"pulled: {remote} -> {local}\n{result}"
        except Exception as e:
            return f"PULL ERROR: {e}"

