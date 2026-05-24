# API Reference

## Tools (120 total)

### ADB & Emulator (`tools_adb.py` — 16 tools)
- `adb_connect`, `adb_disconnect`, `adb_device_info`, `adb_devices`
- `adb_list_packages`, `adb_install`, `adb_uninstall`, `adb_start_app`
- `adb_stop_app`, `adb_restart_app`, `adb_clear_app_data`, `adb_screencap`
- `adb_input_tap`, `adb_input_swipe`, `adb_input_text`, `adb_reboot`

### NDK & Compilation (`tools_ndk.py` — 16 tools)
- `ndk_build_module`, `ndk_build_debug`, `ndk_build_release`, `ndk_build_ccache`
- `ndk_build_clean`, `cmake_generate_config`, `cmake_compile_target`
- `verify_elf_header`, `verify_elf_symbols`, `strip_symbols`
- `parse_compiler_errors`, `patch_makefile`, `check_include_paths`
- `set_compiler_flags`, `get_ndk_version`, `audit_link_dependencies`

### il2cpp & Metadata (`tools_il2cpp.py` — 15 tools)
- `il2cpp_list_assemblies`, `il2cpp_find_class`, `il2cpp_find_method`
- `il2cpp_dump_class_methods`, `il2cpp_get_method_pointer`
- `il2cpp_string_new`, `il2cpp_array_new`, `il2cpp_object_new`
- `il2cpp_invoke_method`, `il2cpp_field_get_value`, `il2cpp_field_set_value`
- `il2cpp_get_nested_types`, `il2cpp_parse_metadata_regex`
- `il2cpp_profiler_export`, `il2cpp_struct_size`

### Hooking & Patching (`tools_hook.py` — 15 tools)
- `hook_generate_template`, `hook_arm64_inline`, `hook_arm64_plt`
- `hook_arm64_got`, `hook_inject_shared_library`, `hook_dlopen_intercept`
- `hook_restore_original`, `hook_list_active`, `hook_export_patch_plan`
- `hook_generate_nop_sled`, `hook_ret_sled`, `hook_trampoline_gen`
- `hook_il2cpp_method`, `hook_check_permissions`, `hook_set_debuggable`

### Crash Trapping (`tools_trap.py` — 15 tools)
- `trap_start_daemon`, `trap_stop_daemon`, `trap_get_crashes`
- `trap_set_filter`, `trap_analyze_crash`, `trap_suggest_patch`
- `trap_clear_logcat`, `trap_dump_logcat`, `trap_watch_signal`
- `trap_tombstone_export`, `trap_continuous_monitor`
- `trap_exception_hook`, `trap_set_breakpoint`, `trap_unwind_stack`
- `trap_check_seccomp`

### Memory & Process (`tools_mem.py` — 15 tools)
- `mem_read_region`, `mem_write_region`, `mem_scan_pattern`
- `mem_dump_process_maps`, `mem_get_base_address`, `mem_protect_region`
- `mem_alloc`, `mem_free`, `mem_hash_region`
- `mem_dump_to_file`, `mem_compare_regions`, `mem_find_library_base`
- `mem_list_libraries`, `mem_export_proc_maps`, `mem_check_rwx`

### Frida Integration (`tools_frida.py` — 15 tools)
- `frida_check_installed`, `frida_start_server`, `frida_list_processes`
- `frida_attach`, `frida_eval_script`, `frida_trace_method`
- `frida_dump_memory`, `frida_write_memory`, `frida_spawn`
- `frida_detach`, `frida_stalker_trace`, `frida_offset_to_absolute`
- `frida_find_module_address`, `frida_enumerate_classes`
- `frida_hook_instance_method`

### APK Handling (`tools_apk.py` — 15 tools)
- `apk_pull_from_device`, `apk_extract`, `apk_extract_native_libs`
- `apk_decompile_smali`, `apk_recompile`, `apk_sign`
- `apk_install_patched`, `patch_manifest_debuggable`
- `detect_apk_protection`, `apk_verify_signature`
- `apk_get_version`, `diff_apks`, `search_java_source`
- `detect_ssl_pinning`

### Server (`server.py` — 1 tool)
- `health_check`

---

## Core Infrastructure (`shared.py`)

| Class / Function | Purpose |
|---|---|
| `CrashContext` | Structured crash report dataclass |
| `CrashTrapDaemon` | Background thread reading `adb logcat -b crash` |
| `_adb_run()` | ADB command runner with retries |
| `_adb_shell()` | Convenience wrapper for `adb shell` |
| `_check_ndk_toolchain()` | Verifies NDK clang is reachable |
| `_parse_ndk_errors()` | Structured NDK build output parser |

## Key Constants

| Constant | Source |
|---|---|
| `ADB_BINARY` | `adb` or `adb.exe` (auto-detected) |
| `NDK_CLANG` | `$ANDROID_NDK_HOME` arm64 clang |
| `NDK_STRIP` | `llvm-strip` from NDK toolchain |
| `NDK_TOOLCHAIN` | LLVM prebuilt path for host OS |
| `PROJECT_ROOT` | Repository root path |
| `LIBS_DIR` | `libs/` output directory |
| `HOST_OS` | `darwin`, `linux`, or `windows` |