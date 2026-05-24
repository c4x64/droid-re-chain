# droid-re-chain — Agent Instructions

## What this is

An MCP server exposing 90 tools across 6 categories for headless Android RE automation (ADB, NDK, il2cpp, hooking, crash trapping, memory analysis). The NDK module `src/main.cpp` + `include/il2cpp.h` compiles to `libs/libmod.so` (arm64).

## Directory layout

```
src/server.py          — MCP entrypoint, registers all 6 tool modules
src/shared.py          — CrashTrapDaemon, _adb_run, NDK paths, CrashContext
src/tools_adb.py       — 15 ADB/emulator management tools
src/tools_ndk.py       — 15 NDK/compilation/CMake tools
src/tools_il2cpp.py    — 15 symbol/metadata parsing tools
src/tools_hook.py      — 15 memory patching/hook generation tools
src/tools_trap.py      — 15 runtime/logcat crash trap tools
src/tools_mem.py       — 15 process/memory analysis tools
src/main.cpp           — NDK hook module (edit this)
include/il2cpp.h       — READ ONLY. Do not edit. il2cpp API wrappers.
Android.mk             — legacy NDK build file
SKILL.md               — opencode skill definition
config/opencode.json   — MCP server registration for opencode
```

## Key commands

```
python3 -m src.server         # start MCP server (stdio mode)
python3 src/server.py         # alternative entry
python3 -c "from src.tools_adb import register"  # verify module import
```

## 1K line rule

Every source file MUST stay under 1,000 lines. If a module approaches 900 lines, split it.

## Tool registration pattern

Each `tools_*.py` exports a single `register(mcp)` function that adds all its `@mcp.tool()` decorators. The server imports and calls each register function.

## Build

The NDK toolchain path is read from `$ANDROID_NDK_HOME`, defaults to `/opt/homebrew/share/android-commandlinetools/ndk/25.2.9519653`. Set this env var for portability.

## Crash analysis chain

`analyze_crash_report()` -> JSON dict -> `suggest_patch_strategy()` -> structured action plan. The `CrashTrapDaemon` in `shared.py` runs a background thread reading `adb logcat -b crash`.

## Important constraints

- Do not edit `include/il2cpp.h` — it is read only
- Do not exceed 1K lines per file
- All ADB commands use `subprocess.run` with arg lists (never `shell=True`)
- Tool modules use `tools_*.py` naming pattern
