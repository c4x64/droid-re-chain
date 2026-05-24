"""Example: Use Frida tools to enumerate classes and hook a target."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.tools_frida import register
from mcp.server.fastmcp import FastMCP

if __name__ == "__main__":
    mcp = FastMCP("frida-example")
    register(mcp)

    print("=== Frida Example: Enumerate & Hook ===")
    print()
    print("1. Ensure frida-server is running on device:")
    print("   adb push frida-server /data/local/tmp/")
    print("   adb shell chmod 755 /data/local/tmp/frida-server")
    print("   adb shell /data/local/tmp/frida-server &")
    print()
    print("2. Find a target process:")
    print("   python3 -c \"from src.tools_frida import *; ...\"")
    print()
    print("3. Generate hook for an instance method:")
    script = """\
Java.perform(function() {
    var cls = Java.use('com.example.target.MainActivity');
    cls.onCreate.implementation = function(bundle) {
        console.log('onCreate hooked!');
        this.onCreate(bundle);
    };
});"""
    print(f"Example hook script:\n{script}")
    print()
    print("Available Frida tools:")
    print("  frida_check_installed, frida_list_processes, frida_attach")
    print("  frida_eval_script, frida_trace_method, frida_dump_memory")
    print("  frida_write_memory, frida_spawn, frida_detach")
    print("  frida_stalker_trace, frida_offset_to_absolute")
    print("  frida_find_module_address, frida_enumerate_classes")
    print("  frida_hook_instance_method")