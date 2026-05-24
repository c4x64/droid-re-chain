---
name: droid-re-chain
description: Use ONLY for Android reverse engineering tasks involving NDK compilation, ADB device control, il2cpp runtime analysis, or automated crash-log-driven patch iteration on arm64 Android emulators. Do NOT use for general Android development.
---

# droid-re-chain MCP Server

Headless AI-driven Android reverse engineering automation pipeline.

## When to use

Use when the task involves any of:

- **NDK compilation**: Building `libmod.so` from `src/main.cpp` using the arm64 NDK toolchain
- **ADB device management**: Pushing/pulling files, executing shell commands, restarting packages
- **Il2cpp runtime analysis**: Scanning method pointers, analyzing Unity/il2cpp binaries
- **Crash-driven iteration**: Parsing logcat/tombstone crashes, extracting fault offsets, suggesting patch targets

## Tools available

| Tool | Purpose |
|------|---------|
| `adb_connect` / `adb_disconnect` | Connect/disconnect to emulator loopback |
| `adb_devices` | List connected devices |
| `adb_shell_cmd` / `adb_push_binary` / `adb_pull_data` | Device control and payload deployment |
| `adb_install_apk` / `adb_start_activity` / `adb_force_stop` | App lifecycle management |
| `adb_restart_package` (combo) | Force-stop + relaunch a package |
| `ndk_build_module` / `ndk_build_clean` | NDK compilation pipeline |
| `cmake_generate_config` / `cmake_compile_target` | CMake build system |
| `verify_binary_architecture` | ELF header ARM64 verification |
| `logcat_clear_buffer` / `logcat_dump_stack_trace` | Logcat management |
| `logcat_spawn_crash_trap` | Background crash daemon (SIGSEGV/SIGILL/SIGABRT) |
| `analyze_crash_report` / `extract_il2cpp_offsets` | Crash parsing |
| `suggest_patch_strategy` | AI-driven patch suggestion |
| `build_deploy_loop` | Full auto cycle (build→push→restart→logcat→analyze→repeat) |
| `deploy_payload_with_restart` | Push + restart in one step |
| `device_info` / `project_status` | Environment introspection |

## Workflow

1. **Pull** il2cpp from target with `adb_pull_data` → analyze exported symbols
2. **Write** hooks in `src/main.cpp` using `include/il2cpp.h` utilities
3. **Build** with `ndk_build_module` → parse JSON errors → fix
4. **Verify** with `verify_binary_architecture` → confirm ARM64
5. **Deploy** with `deploy_payload_with_restart` → pushes `.so` + restarts target
6. **Trap** with `logcat_spawn_crash_trap(action="start")` + `action="fetch"` → extract offsets
7. **Analyze** with `analyze_crash_report` → `suggest_patch_strategy` → **patch** → repeat

## Files

- `src/main.cpp` — hook implementation (EDIT THIS)
- `include/il2cpp.h` — **READ ONLY**, do not modify
- `Android.mk` — legacy NDK build file