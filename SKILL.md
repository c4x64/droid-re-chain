---
name: droid-re-chain
description: Use ONLY for Android reverse engineering tasks involving NDK compilation, ADB device control, il2cpp runtime analysis, Frida hooking, crash-log-driven patch iteration, or APK manipulation on arm64 Android emulators. Do NOT use for general Android development.
---

# droid-re-chain MCP Server

Headless AI-driven Android reverse engineering automation pipeline — **182 tools across 17 categories**.

## When to use

Use when the task involves any of:

- **NDK compilation**: Building `libmod.so` from `src/main.cpp` using the arm64 NDK toolchain
- **ADB device management**: Pushing/pulling files, executing shell commands, managing packages
- **Il2cpp runtime analysis**: Scanning method pointers, analyzing Unity/il2cpp binaries
- **Crash-driven iteration**: Parsing logcat/tombstone crashes, extracting fault offsets, suggesting patches
- **Memory analysis**: Inspecting process maps, scanning patterns, pointer chasing
- **Hook generation**: Dobby stubs, vtable swizzle, trampoline verification
- **Frida instrumentation**: Attach, spawn, stalker trace, memory read/write, Java hooks
- **APK manipulation**: Decompile, recompile, sign, install, detect protections, SSL pinning
- **Ghidra integration**: Headless analysis, decompilation, symbol export, xrefs, version tracking, FunctionID
- **Self-improvement**: Skill learning, MCP tool auto-generation, validation, registration, and upstream contribution

## 17 Tool Categories (182 tools)

### 1. ADB & Emulator (16 tools)
`adb_connect`, `adb_disconnect`, `adb_device_info`, `adb_devices`,
`adb_list_packages`, `adb_install`, `adb_uninstall`, `adb_start_app`,
`adb_stop_app`, `adb_restart_app`, `adb_clear_app_data`, `adb_screencap`,
`adb_input_tap`, `adb_input_swipe`, `adb_input_text`, `adb_reboot`

### 2. NDK & Compilation (16 tools)
`ndk_build_clean`, `ndk_build_module`, `ndk_build_debug`, `ndk_build_release`,
`ndk_build_ccache`, `cmake_generate_config`, `cmake_compile_target`,
`verify_elf_header`, `verify_elf_symbols`, `strip_symbols`,
`parse_compiler_errors`, `patch_makefile`, `check_include_paths`,
`set_compiler_flags`, `get_ndk_version`, `audit_link_dependencies`

### 3. Il2cpp Parsing (15 tools)
`il2cpp_list_assemblies`, `il2cpp_find_class`, `il2cpp_find_method`,
`il2cpp_dump_class_methods`, `il2cpp_get_method_pointer`,
`il2cpp_string_new`, `il2cpp_array_new`, `il2cpp_object_new`,
`il2cpp_invoke_method`, `il2cpp_field_get_value`, `il2cpp_field_set_value`,
`il2cpp_get_nested_types`, `il2cpp_parse_metadata_regex`,
`il2cpp_profiler_export`, `il2cpp_struct_size`

### 4. Hooking & Patching (15 tools)
`hook_generate_template`, `hook_arm64_inline`, `hook_arm64_plt`,
`hook_arm64_got`, `hook_inject_shared_library`, `hook_dlopen_intercept`,
`hook_restore_original`, `hook_list_active`, `hook_export_patch_plan`,
`hook_generate_nop_sled`, `hook_ret_sled`, `hook_trampoline_gen`,
`hook_il2cpp_method`, `hook_check_permissions`, `hook_set_debuggable`

### 5. Runtime Trapping (15 tools)
`trap_start_daemon`, `trap_stop_daemon`, `trap_get_crashes`,
`trap_set_filter`, `trap_analyze_crash`, `trap_suggest_patch`,
`trap_clear_logcat`, `trap_dump_logcat`, `trap_watch_signal`,
`trap_tombstone_export`, `trap_continuous_monitor`,
`trap_exception_hook`, `trap_set_breakpoint`, `trap_unwind_stack`,
`trap_check_seccomp`

### 6. Memory Analysis (15 tools)
`mem_read_region`, `mem_write_region`, `mem_scan_pattern`,
`mem_dump_process_maps`, `mem_get_base_address`, `mem_protect_region`,
`mem_alloc`, `mem_free`, `mem_hash_region`, `mem_dump_to_file`,
`mem_compare_regions`, `mem_find_library_base`, `mem_list_libraries`,
`mem_export_proc_maps`, `mem_check_rwx`

### 7. Frida Integration (15 tools)
`frida_check_installed`, `frida_start_server`, `frida_list_processes`,
`frida_attach`, `frida_eval_script`, `frida_trace_method`,
`frida_dump_memory`, `frida_write_memory`, `frida_spawn`, `frida_detach`,
`frida_stalker_trace`, `frida_offset_to_absolute`,
`frida_find_module_address`, `frida_enumerate_classes`,
`frida_hook_instance_method`

### 8. APK Manipulation (15 tools)
`apk_pull_from_device`, `apk_extract`, `apk_extract_native_libs`,
`apk_decompile_smali`, `apk_recompile`, `apk_sign`, `apk_install_patched`,
`patch_manifest_debuggable`, `detect_apk_protection`,
`apk_verify_signature`, `apk_get_version`, `diff_apks`,
`search_java_source`, `detect_ssl_pinning`

### 9. Static Analysis (7 tools)
`static_disassemble_offset`, `static_find_string_xrefs`, `static_detect_obfuscation`,
`static_checksec`, `static_find_crypto_constants`, `static_extract_urls`, `static_call_graph`

### 10. Offset Database (6 tools)
`db_save_offset`, `db_load_offsets`, `db_remap_offsets`, `db_export_json`, `db_import_json`, `db_diff_versions`

### 11. Session & Replay (4 tools)
`session_save`, `session_restore`, `session_replay`, `session_export`

### 12. Anti-Tamper Bypass (5 tools)
`bypass_root_detect`, `bypass_emulator_detect`, `bypass_debugger_detect`,
`bypass_integrity_check`, `spoof_device_fingerprint`

### 13. IDA Integration (3 tools)
`ida_import_symbols`, `ida_sync_offsets`, `ida_run_script`

### 14. Ghidra Integration (8 tools)
`ghidra_analyze`, `ghidra_export_symbols`, `ghidra_decompile_function`,
`ghidra_run_script`, `ghidra_find_xrefs`, `ghidra_import_offsets`,
`ghidra_diff_binaries`, `ghidra_detect_library_functions`

### 15. Self-Improvement (10 tools)
`skill_save`, `skill_load`, `skill_list`, `skill_apply`, `skill_promote`,
`tool_generate`, `tool_validate`, `tool_register`,
`session_learn`, `contribute_skill`

### 16. Network Analysis (4 tools)
`net_intercept_https`, `net_dump_traffic`, `net_find_endpoints`, `net_decode_protobuf`

### 17. Server Utility (2 tools)
`health_check`, `mcp_update`

## Files

- `src/main.cpp` — hook implementation (EDIT THIS)
- `include/il2cpp.h` — **READ ONLY**, do not modify
- `include/logging.h` — thread-safe logging macros, BUILD_HASH, null guards
- `Android.mk` / `Application.mk` — NDK build files
- `scripts/build_ndk.py` — advanced builder with ccache/LTO/sanitizers/ELF verify

## Important constraints

- Every source file must stay under 1,000 lines
- All ADB commands use `subprocess.run` with arg lists (never `shell=True`)
- `include/il2cpp.h` is READ ONLY — do not edit
- NDK toolchain read from `$ANDROID_NDK_HOME`, falls back to common install paths
- The project auto-detects macOS/Linux/Windows host OS for cross-platform compatibility