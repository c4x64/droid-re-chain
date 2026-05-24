---
name: droid-re-chain
description: Use ONLY for Android reverse engineering tasks involving NDK compilation, ADB device control, il2cpp runtime analysis, or automated crash-log-driven patch iteration on arm64 Android emulators. Do NOT use for general Android development.
---

# droid-re-chain MCP Server

Headless AI-driven Android reverse engineering automation pipeline — 90 tools across 6 categories.

## When to use

Use when the task involves any of:

- **NDK compilation**: Building `libmod.so` from `src/main.cpp` using the arm64 NDK toolchain
- **ADB device management**: Pushing/pulling files, executing shell commands, restarting packages
- **Il2cpp runtime analysis**: Scanning method pointers, analyzing Unity/il2cpp binaries
- **Crash-driven iteration**: Parsing logcat/tombstone crashes, extracting fault offsets, suggesting patch targets
- **Memory analysis**: Inspecting process maps, scanning patterns, pointer chasing
- **Hook generation**: Dobby stubs, vtable swizzle, trampoline verification

## 6 Tool Categories (90 tools)

### 1. ADB & Emulator (15 tools) — `adb_*`
`adb_connect`, `adb_disconnect`, `adb_device_info`, `adb_devices`,
`adb_list_packages`, `adb_current_app`, `adb_force_stop`, `adb_clear_data`,
`adb_install_apk`, `adb_uninstall_package`, `adb_grant_permissions`,
`adb_file_push`, `adb_file_pull`, `adb_file_chmod`, `adb_file_remove`, `adb_mkdir`

### 2. NDK & Compilation (15 tools) — `ndk_*`, `cmake_*`, `verify_*`, `strip_*`
`ndk_build_clean`, `ndk_build_module`, `ndk_build_debug`, `ndk_build_release`,
`cmake_generate_config`, `cmake_compile_target`, `verify_elf_header`,
`strip_symbols`, `parse_compiler_errors`, `patch_makefile`,
`check_include_paths`, `set_compiler_flags`, `get_ndk_version`,
`audit_link_dependencies`, `generate_standalone_toolchain`

### 3. Il2cpp Parsing (15 tools) — `il2cpp_*`
`il2cpp_run_dumper`, `il2cpp_load_json`, `il2cpp_find_class`,
`il2cpp_get_method_rva`, `il2cpp_get_fields`, `il2cpp_get_method_params`,
`il2cpp_search_methods`, `il2cpp_generate_mock_header`,
`il2cpp_extract_string_literals`, `il2cpp_diff_metadata`,
`il2cpp_get_nested_classes`, `il2cpp_validate_method_signature`,
`il2cpp_export_type_definitions`, `il2cpp_find_generic_instances`,
`il2cpp_calculate_struct_padding`

### 4. Hooking & Patching (15 tools) — `hook_*`
`hook_generate_dobby_stub`, `hook_generate_patch_payload`,
`hook_calculate_absolute_address`, `hook_inject_zygisk_template`,
`hook_inject_xposed_bridge`, `hook_generate_dlopen_wrapper`,
`hook_create_function_ptr_cast`, `hook_write_patch_map`,
`hook_obfuscate_string`, `hook_verify_trampoline_size`,
`hook_generate_multi_target`, `hook_add_conditional_gate`,
`hook_generate_vtable_swizzle`, `hook_check_calling_convention`,
`hook_generate_vtable_noop_patch`

### 5. Runtime Trapping (15 tools) — `trap_*`
`trap_clear_buffers`, `trap_start_stream`, `trap_stop_stream`,
`trap_set_filter`, `trap_scan_crash_signals`, `trap_extract_pc_register`,
`trap_parse_stack_trace`, `trap_isolate_fault_address`,
`trap_map_fault_to_rva`, `trap_dump_native_heap`, `trap_monitor_anr`,
`trap_capture_tombstone`, `trap_log_custom_payload`, `trap_get_thread_list`,
`trap_detect_anticheat_log`

### 6. Memory Analysis (15 tools) — `mem_*`
`mem_get_process_maps`, `mem_find_base_address`, `mem_read_bytes`,
`mem_write_bytes`, `mem_scan_pattern`, `mem_dump_segment`,
`mem_check_protection`, `mem_verify_checksum`, `mem_monitor_value_change`,
`mem_locate_pointer_chains`, `mem_get_region_size`,
`mem_detect_hook_overwrites`, `mem_alloc_sandbox_page`,
`mem_free_sandbox_page`, `mem_audit_integrity_loops`

## Workflow

1. **Pull** il2cpp from target → analyze exported symbols with `il2cpp_*` tools
2. **Write** hooks in `src/main.cpp` using `include/il2cpp.h` utilities
3. **Build** with `ndk_build_module` → parse JSON errors → fix
4. **Verify** with `verify_elf_header` → confirm ARM64
5. **Deploy** with `adb_file_push` + `adb_start_activity` → push `.so` + restart
6. **Trap** with `trap_start_stream` + `trap_scan_crash_signals` → extract offsets
7. **Analyze** with `trap_parse_stack_trace` → `hook_generate_patch_payload` → **patch** → repeat

## Files

- `src/main.cpp` — hook implementation (EDIT THIS)
- `include/il2cpp.h` — **READ ONLY**, do not modify
- `Android.mk` / `Application.mk` — NDK build files