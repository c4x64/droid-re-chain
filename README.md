<p align="center">
  <img src="https://img.shields.io/badge/tools-122-blue?style=flat-square">
  <img src="https://img.shields.io/badge/tests-36-passing-green?style=flat-square">
  <img src="https://img.shields.io/badge/python-3.10+-orange?style=flat-square">
  <img src="https://img.shields.io/badge/platform-macOS%20|%20Linux%20|%20Windows-lightgrey?style=flat-square">
  <img src="https://img.shields.io/badge/license-MIT-green?style=flat-square">
</p>

# droid-re-chain

Headless AI-driven Android reverse engineering automation pipeline.

An MCP server exposing **122 tools** across **8 categories** for automated static/dynamic analysis of Android arm64 Unity/il2cpp applications. Runs with any MCP-compatible agent: **Cursor**, **Claude Code**, **opencode**, **VS Code** (Continue/Roo Cline), or any custom MCP host.

## One-Liner Install

```bash
# macOS / Linux
curl -fsSL https://raw.githubusercontent.com/c4x64/droid-re-chain/main/install.sh | bash

# With custom NDK path
curl -fsSL https://raw.githubusercontent.com/c4x64/droid-re-chain/main/install.sh | bash -s -- --ndk /opt/ndk

# Windows (PowerShell)
powershell -Command "iwr -Uri https://raw.githubusercontent.com/c4x64/droid-re-chain/main/install.bat -OutFile install.bat; .\install.bat"

# Run from anywhere
droidre                    # stdio mode (for MCP hosts)
droidre --sse              # SSE mode

# Or from the project dir
cd ~/droid-re-chain && python3 -m src.server
```
 
## Quick Start
 
```bash
git clone https://github.com/c4x64/droid-re-chain.git
cd droid-re-chain
pip install -r requirements.txt
droidre                        # stdio mode (for MCP hosts)
droidre --sse                  # SSE mode (for browser/dev tools)
```

For NDK builds, set `ANDROID_NDK_HOME` to your NDK r25+ path.

## Architecture

```
src/server.py              — MCP entrypoint (--sse/--stdio flags)
src/shared.py              — CrashTrapDaemon, _adb_run, NDK paths, cross-platform OS detection
src/tools_adb.py           — 16 ADB/emulator management tools
src/tools_ndk.py           — 16 NDK/compilation/CMake/ELF verification tools
src/tools_il2cpp.py        — 15 symbol/metadata/Unity runtime tools
src/tools_hook.py          — 15 memory patching/trampoline generation tools
src/tools_trap.py          — 15 logcat crash trap/tombstone analysis tools
src/tools_mem.py           — 15 process/memory/maps/pattern scan tools
src/tools_frida.py         — 15 Frida attach/spawn/stalker/hook tools
src/tools_apk.py           — 15 APK decompile/recompile/sign/patch tools
include/il2cpp.h           — il2cpp API wrapper (READ ONLY)
include/logging.h          — Thread-safe logging, BUILD_HASH, null guards
src/main.cpp               — NDK hook module (constructor guard, install_hook)
scripts/build_ndk.py       — ccache/LTO/sanitizer/ELF verify builder
```

## Tool Categories

| Category | Tools | Key Capabilities |
|----------|-------|-----------------|
| **ADB** (`adb_*`) | 16 | connect, install, screencap, input, reboot, package lifecycle |
| **NDK** (`ndk_*`, `verify_*`, etc.) | 17 | clang/LTO/ccache build, CMake, ELF verify, symbol audit, strip |
| **il2cpp** (`il2cpp_*`) | 15 | assembly dump, class/method search, invoke, field read/write, profiler |
| **Hook** (`hook_*`) | 15 | inline/PLT/GOT templates, dlopen intercept, trampoline gen, il2cpp method hook |
| **Trap** (`trap_*`) | 15 | CrashTrapDaemon, logcat stream, signal filter, tombstone export, seccomp audit |
| **Memory** (`mem_*`) | 15 | maps dump, pattern scan, RWX check, region compare, hash, alloc/free |
| **Frida** (`frida_*`) | 15 | attach/spawn/detach, stalker trace, memory read/write, Java hook, module find |
| **APK** (`apk_*`) | 15 | pull, extract, apktool decompile/recompile, sign, SSL pinning scan, protection detect |
| **Static** (`static_*`) | 7 | capstone disassembly, string xrefs, obfuscation heuristics, checksec, crypto constants, URL extraction, call graph |
| **Database** (`db_*`) | 6 | persist/load/remap offsets by binary hash, import/export JSON, diff versions |
| **Session** (`session_*`) | 4 | snapshot/restore/replay session state, export shareable archives |
| **Bypass** (`bypass_*`, `spoof_*`) | 5 | root/emulator/debugger/integrity check bypass, device fingerprint spoofing |
| **IDA** (`ida_*`) | 3 | import IDA symbols, sync offsets back to IDA, execute IDAPython headless |
| **Network** (`net_*`) | 4 | mitmproxy setup, traffic dump, endpoint discovery, protobuf decode |
| **Server** (`health_*`) | 1 | health_check — all-subsystems status report |

**Total: 151 tools**

## Multi-Client Setup

droid-re-chain works with **20+ MCP-compatible clients**. Run the auto-installer:

```bash
bash scripts/setup_mcp.sh
```

It detects installed clients and writes configs for all of them:

| # | Client | Scope | Config Path |
|---|--------|-------|-------------|
| 1 | **Cursor** | Project | `.cursor/mcp.json` |
| 2 | **Windsurf** | Global | `~/.codeium/windsurf/mcp_config.json` |
| 3 | **Antigravity** | Project | `mcp_config.json` |
| 4 | **PearAI** | Project | `.pearai/mcp.json` |
| 5 | **Claude Desktop** | Global | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| 6 | **ChatGPT Desktop** | Global | Settings → MCP Servers |
| 7 | **LibreChat** | Project | `librechat.yaml` |
| 8 | **Jan** | Global | `~/jan/plugins/droid-re-chain.json` |
| 9 | **Goose CLI** | Global | `~/.goose/config.yaml` |
| 10 | **Claude Code** | Project | `.claude/settings.json` |
| 11 | **Aider** | Project | `.aider.conf.yml` |
| 12 | **AutoGen Studio** | Project | `autogenstudio/workspace.json` |
| 13 | **CrewAI** | Project | `crew.yaml` |
| 14 | **LangGraph** | Project | `langgraph.json` |
| 15 | **Roo Code** | Project | `.roo/mcp.json` |
| 16 | **Continue** | Project | `.continue/mcpServers/droid-re-chain.json` |
| 17 | **VS Code (1.102+)** | Workspace | `.vscode/mcp.json` |
| 18 | **Composio** | Cloud | Dashboard → Add Custom MCP |
| 19 | **LlamaIndex** | Runtime | Python `McpToolSpec` |
| 20 | **Harvey AI** | Enterprise | Admin dashboard |

See [`MCP_CLIENTS.md`](MCP_CLIENTS.md) for per-client details.

### opencode

Already configured in `config/opencode.json`. Symlink:

```bash
ln -sf $PWD/config/opencode.json $PWD/opencode.json
```

### CLI / Any MCP Host

```bash
droidre                                   # stdio (default, from anywhere)
droidre --sse --port 8080                 # SSE mode
bash mcp-entrypoint.sh                    # portable launcher
```

## Prerequisites

- **Python 3.10+**
- **Android NDK r25+** — set `ANDROID_NDK_HOME` for compilation tools
- **ADB** (platform-tools) — `brew install android-platform-tools` / `apt install adb`
- **Android emulator or device** with ADB debugging enabled (root optional; some tools need su)

### Optional

- **Frida** — `pip install frida-tools` for `frida_*` tools
- **apktool** — for `apk_decompile_smali` / `apk_recompile`
- **apksigner** — for `apk_sign` (comes with Android SDK build-tools)
- **ccache** — `brew install ccache` / `apt install ccache` (speeds up NDK rebuilds)

## Typical Workflow

```
1. Pull APK from device (apk_pull_from_device)
2. Decompile to smali   (apk_decompile_smali)
3. Find il2cpp offsets   (il2cpp_find_class → il2cpp_find_method → il2cpp_get_method_pointer)
4. Generate hook        (hook_il2cpp_method / hook_arm64_inline)
5. Compile libmod.so    (ndk_build_module)
6. Verify ELF           (verify_elf_header → verify_elf_symbols)
7. Push to device       (adb push via adb_file_*)
8. Frida attach         (frida_attach → frida_eval_script)
9. Monitor crashes      (trap_start_daemon → trap_get_crashes → trap_analyze_crash)
10. Patch & repeat      (trap_suggest_patch → hook_arm64_inline → rebuild)
```

## Cross-Platform

Auto-detects macOS/Linux/Windows for:
- ADB binary name (`adb` / `adb.exe`)
- NDK host tag (`darwin-x86_64`, `darwin-aarch64`, `linux-x86_64`, `windows-x86_64`)
- NDK fallback paths (Homebrew, `~/Android/Sdk`, `~/android-ndk`)

## Development

```bash
make install       # pip install everything
make build-release # NDK compile via scripts/build_ndk.py
make test          # 36 tests, all pass
make lint          # ruff check src/
make docs          # regenerate docs/api.md
```

## Testing

```bash
python3 -m pytest tests/ -v
```

36 tests covering OS detection, NDK path resolution, crash parser (empty/signal/full backtrace), ADB error handling, error limit truncation, daemon lifecycle.

## Files

| File | Purpose |
|------|---------|
| `src/server.py` | MCP entrypoint with `--sse`/`--port` flags |
| `src/shared.py` | CrashTrapDaemon, ADB/NDK wrappers, cross-platform detection |
| `src/tools_*.py` | 8 module files, 122 tools total |
| `include/logging.h` | Thread-safe logging macros, BUILD_HASH, null guards |
| `include/il2cpp.h` | il2cpp runtime API wrapper (**READ ONLY**) |
| `src/main.cpp` | NDK hook module with constructor guard + `install_hook()` |
| `scripts/build_ndk.py` | Advanced NDK builder (ccache, LTO, sanitizers, ELF verify) |
| `scripts/generate_docs.py` | Auto-generates `docs/api.md` from registered tools |
| `scripts/setup_mcp.sh` | One-shot MCP config installer for Cursor/Claude Code |
| `mcp-entrypoint.sh` | Portable launcher for any MCP host |
| `config/opencode.json` | opencode MCP server registration |
| `.cursor/mcp.json` | Cursor project-level MCP config |
| `.claude/settings.json` | Claude Code project-level MCP config |

## License

MIT