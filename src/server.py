"""droid-re-chain MCP Server — modular registry.
Imports and registers tool modules with FastMCP.
Total: 182 tools across 17 categories: ADB, NDK, il2cpp, hook, trap, mem,
frida, apk, static, database, session, bypass, ida, net, dump, ghidra,
update, and self-improvement.

Usage:
  python3 -m src.server                         # all categories (stdio)
  python3 -m src.server --sse                   # SSE mode
  DROID_CATEGORIES=adb,ndk python3 -m src.server  # subset only

Supported DROID_CATEGORIES values (comma-separated):
  adb, ndk, il2cpp, hook, trap, mem, frida, apk, static,
  database, session, bypass, ida, net, dump, ghidra, update, selfimprove
"""
import os
import json
import argparse
from mcp.server.fastmcp import FastMCP
from src.shared import PROJECT_ROOT, HOST_OS, NDK_CLANG, LIBS_DIR
from src.shared import _adb_run, ADB_BINARY

_CATEGORIES = {
    "adb": "src.tools_adb",
    "ndk": "src.tools_ndk",
    "il2cpp": "src.tools_il2cpp",
    "hook": "src.tools_hook",
    "trap": "src.tools_trap",
    "mem": "src.tools_mem",
    "frida": "src.tools_frida",
    "apk": "src.tools_apk",
    "static": "src.tools_static",
    "database": "src.tools_database",
    "session": "src.tools_session",
    "bypass": "src.tools_bypass",
    "ida": "src.tools_ida",
    "net": "src.tools_net",
    "dump": "src.tools_dump",
    "ghidra": "src.tools_ghidra",
    "update": "src.tools_update",
    "selfimprove": "src.tools_selfimprove",
}

mcp = FastMCP("droid-re-chain")

def _load_categories():
    raw = os.environ.get("DROID_CATEGORIES", "")
    if not raw:
        return list(_CATEGORIES.keys())
    return [c.strip() for c in raw.split(",") if c.strip() in _CATEGORIES]

import importlib
for cat in _load_categories():
    mod = importlib.import_module(_CATEGORIES[cat])
    mod.register(mcp)

@mcp.tool()
def health_check() -> str:
    """Verify all subsystems are reachable and report status."""
    adb_check = _adb_run([ADB_BINARY, "devices"], timeout=10)
    adb_status = "ok" if "List of devices" in adb_check else "fail: " + adb_check[:100]
    ndk_found = bool(NDK_CLANG and os.path.isfile(NDK_CLANG))
    return json.dumps({"adb": adb_status, "ndk": "ok" if ndk_found else "missing: set ANDROID_NDK_HOME",
                        "project_root": str(PROJECT_ROOT), "libs_dir": str(LIBS_DIR),
                        "host_os": HOST_OS}, indent=2)

def main():
    parser = argparse.ArgumentParser(prog="droid-re-chain")
    parser.add_argument("--sse", action="store_true", help="Run in SSE mode instead of stdio")
    parser.add_argument("--port", type=int, default=8000, help="Port for SSE mode (default: 8000)")
    args = parser.parse_args()
    if args.sse:
        mcp.run(transport="sse", port=args.port)
    else:
        mcp.run(transport="stdio")

if __name__ == "__main__":
    main()