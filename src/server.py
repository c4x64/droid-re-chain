"""droid-re-chain MCP Server — modular registry.
Imports and registers all 16 tool modules with FastMCP.
Total: 172 tools across 16 categories: ADB, NDK, il2cpp, hook, trap, mem,
frida, apk, static, database, session, bypass, ida, net, dump, and ghidra.

Usage:
  python3 -m src.server              # stdio mode (default, for MCP hosts)
  python3 -m src.server --sse        # SSE mode (for browser/dev tools)
  python3 -m src.server --sse --port 8080  # custom port
"""
import os
import sys
import json
import argparse
from mcp.server.fastmcp import FastMCP
from src.shared import LIBS_DIR, LOGS_DIR, PROJECT_ROOT, HOST_OS, NDK_CLANG
from src.shared import _adb_run, _adb_shell, ADB_BINARY
from src.tools_adb import register as register_adb
from src.tools_ndk import register as register_ndk
from src.tools_il2cpp import register as register_il2cpp
from src.tools_hook import register as register_hook
from src.tools_trap import register as register_trap
from src.tools_mem import register as register_mem
from src.tools_frida import register as register_frida
from src.tools_apk import register as register_apk
from src.tools_static import register as register_static
from src.tools_database import register as register_database
from src.tools_session import register as register_session
from src.tools_bypass import register as register_bypass
from src.tools_ida import register as register_ida
from src.tools_net import register as register_net
from src.tools_dump import register as register_dump
from src.tools_ghidra import register as register_ghidra
from src.tools_update import register as register_update

mcp = FastMCP("droid-re-chain")

register_adb(mcp)
register_ndk(mcp)
register_il2cpp(mcp)
register_hook(mcp)
register_trap(mcp)
register_mem(mcp)
register_frida(mcp)
register_apk(mcp)
register_static(mcp)
register_database(mcp)
register_session(mcp)
register_bypass(mcp)
register_ida(mcp)
register_net(mcp)
register_dump(mcp)
register_ghidra(mcp)
register_update(mcp)

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