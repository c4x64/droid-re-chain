# API Reference

Auto-generated from 122 registered tools.
Host: darwin

## Tools

### ADB & Emulator (16 tools)
- `adb_clear_data` — src/tools_adb.py
- `adb_connect` — src/tools_adb.py
- `adb_current_app` — src/tools_adb.py
- `adb_device_info` — src/tools_adb.py
- `adb_devices` — src/tools_adb.py
- `adb_disconnect` — src/tools_adb.py
- `adb_file_chmod` — src/tools_adb.py
- `adb_file_pull` — src/tools_adb.py
- `adb_file_push` — src/tools_adb.py
- `adb_file_remove` — src/tools_adb.py
- `adb_force_stop` — src/tools_adb.py
- `adb_grant_permissions` — src/tools_adb.py
- `adb_install_apk` — src/tools_adb.py
- `adb_list_packages` — src/tools_adb.py
- `adb_mkdir` — src/tools_adb.py
- `adb_uninstall_package` — src/tools_adb.py

### APK Handling (13 tools)
- `apk_decompile_smali` — src/tools_apk.py
- `apk_extract` — src/tools_apk.py
- `apk_extract_native_libs` — src/tools_apk.py
- `apk_get_version` — src/tools_apk.py
- `apk_install_patched` — src/tools_apk.py
- `apk_pull_from_device` — src/tools_apk.py
- `apk_recompile` — src/tools_apk.py
- `apk_sign` — src/tools_apk.py
- `apk_verify_signature` — src/tools_apk.py
- `detect_apk_protection` — src/tools_apk.py
- `detect_ssl_pinning` — src/tools_apk.py
- `diff_apks` — src/tools_apk.py
- `search_java_source` — src/tools_apk.py

### Crash Trapping (15 tools)
- `trap_capture_tombstone` — src/tools_trap.py
- `trap_clear_buffers` — src/tools_trap.py
- `trap_detect_anticheat_log` — src/tools_trap.py
- `trap_dump_native_heap` — src/tools_trap.py
- `trap_extract_pc_register` — src/tools_trap.py
- `trap_get_thread_list` — src/tools_trap.py
- `trap_isolate_fault_address` — src/tools_trap.py
- `trap_log_custom_payload` — src/tools_trap.py
- `trap_map_fault_to_rva` — src/tools_trap.py
- `trap_monitor_anr` — src/tools_trap.py
- `trap_parse_stack_trace` — src/tools_trap.py
- `trap_scan_crash_signals` — src/tools_trap.py
- `trap_set_filter` — src/tools_trap.py
- `trap_start_stream` — src/tools_trap.py
- `trap_stop_stream` — src/tools_trap.py

### Frida Integration (15 tools)
- `frida_attach` — src/tools_frida.py
- `frida_check_installed` — src/tools_frida.py
- `frida_detach` — src/tools_frida.py
- `frida_dump_memory` — src/tools_frida.py
- `frida_enumerate_classes` — src/tools_frida.py
- `frida_eval_script` — src/tools_frida.py
- `frida_find_module_address` — src/tools_frida.py
- `frida_hook_instance_method` — src/tools_frida.py
- `frida_list_processes` — src/tools_frida.py
- `frida_offset_to_absolute` — src/tools_frida.py
- `frida_spawn` — src/tools_frida.py
- `frida_stalker_trace` — src/tools_frida.py
- `frida_start_server` — src/tools_frida.py
- `frida_trace_method` — src/tools_frida.py
- `frida_write_memory` — src/tools_frida.py

### Hooking & Patching (15 tools)
- `hook_add_conditional_gate` — src/tools_hook.py
- `hook_calculate_absolute_address` — src/tools_hook.py
- `hook_check_calling_convention` — src/tools_hook.py
- `hook_create_function_ptr_cast` — src/tools_hook.py
- `hook_generate_dlopen_wrapper` — src/tools_hook.py
- `hook_generate_dobby_stub` — src/tools_hook.py
- `hook_generate_multi_target` — src/tools_hook.py
- `hook_generate_patch_payload` — src/tools_hook.py
- `hook_generate_vtable_noop_patch` — src/tools_hook.py
- `hook_generate_vtable_swizzle` — src/tools_hook.py
- `hook_inject_xposed_bridge` — src/tools_hook.py
- `hook_inject_zygisk_template` — src/tools_hook.py
- `hook_obfuscate_string` — src/tools_hook.py
- `hook_verify_trampoline_size` — src/tools_hook.py
- `hook_write_patch_map` — src/tools_hook.py

### Memory & Process (15 tools)
- `mem_alloc_sandbox_page` — src/tools_mem.py
- `mem_audit_integrity_loops` — src/tools_mem.py
- `mem_check_protection` — src/tools_mem.py
- `mem_detect_hook_overwrites` — src/tools_mem.py
- `mem_dump_segment` — src/tools_mem.py
- `mem_find_base_address` — src/tools_mem.py
- `mem_free_sandbox_page` — src/tools_mem.py
- `mem_get_process_maps` — src/tools_mem.py
- `mem_get_region_size` — src/tools_mem.py
- `mem_locate_pointer_chains` — src/tools_mem.py
- `mem_monitor_value_change` — src/tools_mem.py
- `mem_read_bytes` — src/tools_mem.py
- `mem_scan_pattern` — src/tools_mem.py
- `mem_verify_checksum` — src/tools_mem.py
- `mem_write_bytes` — src/tools_mem.py

### NDK & Compilation (17 tools)
- `audit_link_dependencies` — src/tools_ndk.py
- `check_include_paths` — src/tools_ndk.py
- `cmake_compile_target` — src/tools_ndk.py
- `cmake_generate_config` — src/tools_ndk.py
- `get_ndk_version` — src/tools_ndk.py
- `ndk_build_ccache` — src/tools_ndk.py
- `ndk_build_clean` — src/tools_ndk.py
- `ndk_build_debug` — src/tools_ndk.py
- `ndk_build_module` — src/tools_ndk.py
- `ndk_build_release` — src/tools_ndk.py
- `parse_compiler_errors` — src/tools_ndk.py
- `patch_makefile` — src/tools_ndk.py
- `patch_manifest_debuggable` — src/tools_ndk.py
- `set_compiler_flags` — src/tools_ndk.py
- `strip_symbols` — src/tools_ndk.py
- `verify_elf_header` — src/tools_ndk.py
- `verify_elf_symbols` — src/tools_ndk.py

### Server Utility (1 tools)
- `health_check` — src/server.py

### il2cpp & Metadata (15 tools)
- `il2cpp_calculate_struct_padding` — src/tools_il2cpp.py
- `il2cpp_diff_metadata` — src/tools_il2cpp.py
- `il2cpp_export_type_definitions` — src/tools_il2cpp.py
- `il2cpp_extract_string_literals` — src/tools_il2cpp.py
- `il2cpp_find_class` — src/tools_il2cpp.py
- `il2cpp_find_generic_instances` — src/tools_il2cpp.py
- `il2cpp_generate_mock_header` — src/tools_il2cpp.py
- `il2cpp_get_fields` — src/tools_il2cpp.py
- `il2cpp_get_method_params` — src/tools_il2cpp.py
- `il2cpp_get_method_rva` — src/tools_il2cpp.py
- `il2cpp_get_nested_classes` — src/tools_il2cpp.py
- `il2cpp_load_json` — src/tools_il2cpp.py
- `il2cpp_run_dumper` — src/tools_il2cpp.py
- `il2cpp_search_methods` — src/tools_il2cpp.py
- `il2cpp_validate_method_signature` — src/tools_il2cpp.py
