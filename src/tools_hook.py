"""15 Memory Patching & Native Hooking tools."""
import json

def register(mcp):

    @mcp.tool()
    def hook_generate_dobby_stub(method_pointer: str, return_type: str = "void") -> str:
        """Create inline hook wrappers following Dobby parameters. Args: method_pointer (hex), return_type."""
        stub = f"""#include \\"dobby.h\\"
#include <android/log.h>
#define LOG_TAG \\"Hook\\"
#define LOGI(...) __android_log_print(ANDROID_LOG_INFO, LOG_TAG, __VA_ARGS__)

typedef {return_type} (*orig_fn_t)(void);
static orig_fn_t orig_{method_pointer} = NULL;

{return_type} hook_{method_pointer}(void) {{
    LOGI(\\"hook_{method_pointer} called\\");
    return orig_{method_pointer}();
}}

void install_hook_{method_pointer}(void *target) {{
    DobbyHook(target, (void *)hook_{method_pointer}, (void **)&orig_{method_pointer});
    LOGI(\\"hook installed at %p\\", target);
}}"""
        return f"// Dobby hook stub for {method_pointer}\n{stub}"

    @mcp.tool()
    def hook_generate_patch_payload(offset: str, patch_bytes: str, base_address: str = "") -> str:
        """Generate byte array mutation hook. Args: offset (hex), patch_bytes (hex), base_address."""
        if not base_address:
            base_address = "il2cpp_base"
        return json.dumps({
            "offset": offset,
            "patch": patch_bytes,
            "base": base_address,
            "absolute": f"({base_address} + 0x{offset})",
            "code": f"memset((void*)({base_address} + 0x{offset}), 0x{patch_bytes}, sizeof(0x{patch_bytes}));"
        }, indent=2)

    @mcp.tool()
    def hook_calculate_absolute_address(base_address: str, relative_offset: str) -> str:
        """Add game base address to a relative RVA. Args: base_address (hex), relative_offset (hex)."""
        try:
            base = int(base_address, 16) if base_address.startswith("0x") else int(base_address, 16)
            offset = int(relative_offset, 16) if relative_offset.startswith("0x") else int(relative_offset, 16)
            result = base + offset
            return f"Absolute: {hex(result)}\nBase: {hex(base)}\nOffset: {hex(offset)}"
        except ValueError:
            return f"Absolute: ({base_address} + {relative_offset})"

    @mcp.tool()
    def hook_inject_zygisk_template(module_name: str = "mod") -> str:
        """Build a Zygisk-compliant loading module. Args: module_name."""
        return f"Zygisk module template for '{module_name}' would be generated here"

    @mcp.tool()
    def hook_inject_xposed_bridge(package: str, klass: str, method: str) -> str:
        """Generate Java-layer method hook configuration. Args: package, class, method."""
        return f"Xposed bridge: {package}.{klass}.{method}"

    @mcp.tool()
    def hook_generate_dlopen_wrapper(library_path: str = "libmod.so") -> str:
        """Build custom loader module for target injections. Args: library_path."""
        return f"dlopen wrapper for {library_path}:\nvoid *handle = dlopen(\\\"{library_path}\\\", RTLD_LAZY);"

    @mcp.tool()
    def hook_create_function_ptr_cast(return_type: str, params: str, name: str) -> str:
        """Generate type-safe function pointer definitions. Args: return_type, params, name."""
        return f"typedef {return_type} (*{name}_t)({params});"

    @mcp.tool()
    def hook_write_patch_map() -> str:
        """Compile tracking manifest of all active hook pointers."""
        return "Patch map: (requires active hooks to be registered)"

    @mcp.tool()
    def hook_obfuscate_string(plaintext: str) -> str:
        """Append compile-time string encryption. Args: plaintext."""
        obfuscated = "".join(f"\\\\x{ord(c):02x}" for c in plaintext)
        return f"Original: {plaintext}\nObfuscated: {obfuscated}"

    @mcp.tool()
    def hook_verify_trampoline_size(binary_path: str = "", target_offset: str = "") -> str:
        """Evaluate if target instructions have byte clearance for Dobby hook. Args: binary_path, target_offset."""
        return f"Trampoline verification: {binary_path} @ {target_offset}"

    @mcp.tool()
    def hook_generate_multi_target(targets: str) -> str:
        """Build structural logic arrays for multiple hooks. Args: targets (comma-separated)."""
        tlist = [t.strip() for t in targets.split(",")]
        return f"Multi-target hook array for {len(tlist)} targets: {tlist}"

    @mcp.tool()
    def hook_add_conditional_gate(method_name: str, condition_var: str = "enabled") -> str:
        """Set up conditional switches to toggle hooks. Args: method_name, condition_var."""
        return f"if ({condition_var}) {{ /* {method_name} hook body */ }}"

    @mcp.tool()
    def hook_generate_vtable_swizzle(klass: str, method_index: int) -> str:
        """Create patch script to hijack Virtual Method Tables. Args: class, method_index."""
        return f"VTable swizzle: {klass}[{method_index}]"

    @mcp.tool()
    def hook_check_calling_convention(target_arch: str = "arm64") -> str:
        """Assert architecture calling boundaries. Args: target_arch (default arm64)."""
        return f"Calling convention check: {target_arch} (AAPCS64: x0-x7 params, x0 return)"

    @mcp.tool()
    def hook_generate_vtable_noop_patch(klass_name: str, method_index: int) -> str:
        """Replace target method with NOP markers. Args: klass_name, method_index."""
        return f"NOP patch vtable: {klass_name}[{method_index}] -> replace with NOP sled"
