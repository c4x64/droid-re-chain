"""droid-re-chain MCP Server — modular registry.
Imports and registers all 8 tool modules with FastMCP.
Total: 120 tools across ADB, NDK, il2cpp, hook, trap, mem, frida, and apk categories.
"""
import os
import json
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

mcp = FastMCP("droid-re-chain")

register_adb(mcp)
register_ndk(mcp)
register_il2cpp(mcp)
register_hook(mcp)
register_trap(mcp)
register_mem(mcp)
register_frida(mcp)
register_apk(mcp)

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
    mcp.run()

if __name__ == "__main__":
    main()