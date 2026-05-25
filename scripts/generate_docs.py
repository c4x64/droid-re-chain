#!/usr/bin/env python3
"""Auto-generate docs/api.md from registered MCP tools."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.server import mcp
from src.shared import HOST_OS

MODULES = {
    "adb": ("ADB & Emulator", "src/tools_adb.py"),
    "ndk": ("NDK & Compilation", "src/tools_ndk.py"),
    "cmake": ("NDK & Compilation", "src/tools_ndk.py"),
    "verify": ("NDK & Compilation", "src/tools_ndk.py"),
    "strip": ("NDK & Compilation", "src/tools_ndk.py"),
    "parse": ("NDK & Compilation", "src/tools_ndk.py"),
    "patch": ("NDK & Compilation", "src/tools_ndk.py"),
    "check": ("NDK & Compilation", "src/tools_ndk.py"),
    "get": ("NDK & Compilation", "src/tools_ndk.py"),
    "set": ("NDK & Compilation", "src/tools_ndk.py"),
    "audit": ("NDK & Compilation", "src/tools_ndk.py"),
    "il2cpp": ("il2cpp & Metadata", "src/tools_il2cpp.py"),
    "hook": ("Hooking & Patching", "src/tools_hook.py"),
    "trap": ("Crash Trapping", "src/tools_trap.py"),
    "mem": ("Memory & Process", "src/tools_mem.py"),
    "frida": ("Frida Integration", "src/tools_frida.py"),
    "apk": ("APK Handling", "src/tools_apk.py"),
    "diff": ("APK Handling", "src/tools_apk.py"),
    "search": ("APK Handling", "src/tools_apk.py"),
    "detect": ("APK Handling", "src/tools_apk.py"),
    "static": ("Static Analysis", "src/tools_static.py"),
    "db": ("Offset Database", "src/tools_database.py"),
    "session": ("Session & Replay", "src/tools_session.py"),
    "bypass": ("Anti-Tamper Bypass", "src/tools_bypass.py"),
    "spoof": ("Anti-Tamper Bypass", "src/tools_bypass.py"),
    "ida": ("IDA Integration", "src/tools_ida.py"),
    "net": ("Network Analysis", "src/tools_net.py"),
    "ghidra": ("Ghidra Integration", "src/tools_ghidra.py"),
    "mcp": ("Server Utility", "src/tools_update.py"),
    "health": ("Server Utility", "src/server.py"),
}

tools_by_module: dict[str, list[str]] = {}
for name in sorted(mcp._tool_manager._tools):
    prefix = name.split("_")[0]
    cat, src = MODULES.get(prefix, ("Other", "?"))
    tools_by_module.setdefault(cat, []).append((name, src))

lines = ["# API Reference", "", f"Auto-generated from {len(mcp._tool_manager._tools)} registered tools.", f"Host: {HOST_OS}", "", "## Tools", ""]
for cat in sorted(tools_by_module):
    tools = tools_by_module[cat]
    lines.append(f"### {cat} ({len(tools)} tools)")
    for name, src in sorted(tools, key=lambda x: x[0]):
        lines.append(f"- `{name}` — {src}")
    lines.append("")

api_path = Path(__file__).resolve().parent.parent / "docs" / "api.md"
api_path.write_text("\n".join(lines))
print(f"Generated {api_path} — {len(mcp._tool_manager._tools)} tools")