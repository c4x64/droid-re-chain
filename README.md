# droid-re-chain

Headless AI-driven Android reverse engineering automation pipeline.

An MCP server exposing **90 tools** across **6 categories** for automated static/dynamic analysis of Android arm64 Unity/il2cpp applications.

## Architecture

```
src/server.py          — MCP entrypoint (registers all 6 modules)
src/shared.py          — CrashTrapDaemon, _adb_run, NDK paths
src/tools_adb.py       — 15 ADB/emulator management tools
src/tools_ndk.py       — 15 NDK/compilation/CMake tools
src/tools_il2cpp.py    — 15 symbol/metadata parsing tools
src/tools_hook.py      — 15 memory patching/hook generation tools
src/tools_trap.py      — 15 runtime/logcat crash trap tools
src/tools_mem.py       — 15 process/memory analysis tools
include/il2cpp.h       — il2cpp API wrapper (READ ONLY)
src/main.cpp           — NDK hook module
```

## Tool Categories

| Category | Count | Purpose |
|----------|-------|---------|
| ADB (`adb_*`) | 15 | Device control, push/pull, install, permissions |
| NDK (`ndk_*`, `cmake_*`, `verify_*`) | 15 | Compilation, toolchain, ELF verification |
| Il2cpp (`il2cpp_*`) | 15 | Symbol parsing, metadata, method RVA resolution |
| Hook (`hook_*`) | 15 | Dobby stubs, patch generation, vtable swizzle |
| Trap (`trap_*`) | 15 | Logcat streaming, crash detection, ANR monitoring |
| Memory (`mem_*`) | 15 | /proc/pid/maps, pattern scan, pointer chains |

## Quick Start

```bash
pip install -r requirements.txt
python3 src/server.py          # start MCP server (stdio mode)
```

For NDK builds, set `ANDROID_NDK_HOME` to your NDK r25+ installation.

## Prerequisites

- Python 3.10+
- Android NDK r25+ (for compilation)
- ADB (platform-tools)
- Android emulator or device with root access

## License

MIT