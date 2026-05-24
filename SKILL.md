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
| `adb_devices` | List connected devices |
| `adb_shell` / `adb_push_payload` | Device control and payload deployment |
| `adb_restart_package` | Force-stop + relaunch a package |
| `build_mod` / `ndk_compile_project` / `clean_build` | NDK compilation pipeline |
| `deploy_mod` | Build + push in one atomic step |
| `analyze_crash` / `extract_crash_offsets` / `suggest_patch_target` | Logcat crash analysis |
| `pull_il2cpp` | Extract il2cpp from target APK |

## Workflow

1. **Pull** il2cpp from target → analyze exported symbols
2. **Write** hooks in `src/main.cpp` using `include/il2cpp.h` utilities
3. **Build** with `build_mod` → fix compilation errors
4. **Deploy** with `deploy_mod` → pushes to `/data/local/tmp/libmod.so`
5. **Restart** target package with `adb_restart_package`
6. **Logcat** with `adb_logcat(filter="REChainMod:S")` → trap crashes
7. **Analyze** with `analyze_crash` → extract offset → **patch** → repeat

## Files

- `src/main.cpp` — hook implementation (edit this)
- `include/il2cpp.h` — **READ ONLY**, do not modify
- `Android.mk` — legacy NDK build file