"""droid-re-chain MCP Server — modular registry.

Imports and registers all 6 tool modules with FastMCP.
Total: 90 tools across ADB, NDK, il2cpp, hook, trap, and mem categories.
"""
import time
import subprocess
import json
from mcp.server.fastmcp import FastMCP

from src.shared import LIBS_DIR, LOGS_DIR, _adb_run, _adb_shell, ADB_BINARY
from src.tools_adb import register as register_adb
from src.tools_ndk import register as register_ndk
from src.tools_il2cpp import register as register_il2cpp
from src.tools_hook import register as register_hook
from src.tools_trap import register as register_trap
from src.tools_mem import register as register_mem

mcp = FastMCP("droid-re-chain")

register_adb(mcp)
register_ndk(mcp)
register_il2cpp(mcp)
register_hook(mcp)
register_trap(mcp)
register_mem(mcp)

def main():
    mcp.run()

if __name__ == "__main__":
    main()
