from mcp.server.fastmcp import FastMCP

from src.tools_adb import register as register_adb
from src.tools_ndk import register as register_ndk
from src.tools_il2cpp import register as register_il2cpp

mcp = FastMCP(
    "droid-re-chain",
    description="Headless AI-driven Android reverse engineering automation pipeline.",
)

register_adb(mcp)
register_ndk(mcp)
register_il2cpp(mcp)

def main():
    mcp.run()

if __name__ == "__main__":
    main()