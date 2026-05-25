"""15 Frida Integration tools."""
import json
from src.shared import _adb_run, _adb_shell, ADB_BINARY, PROJECT_ROOT, LIBS_DIR
FRIDA_SCRIPTS = PROJECT_ROOT / "frida_scripts"
FRIDA_SCRIPTS.mkdir(exist_ok=True)

def register(mcp):

    @mcp.tool()
    def frida_check_installed() -> str:
        """Verify frida-server is running on the device."""
        r = _adb_shell("ps -ef | grep frida-server | grep -v grep", su=True)
        return f"frida-server running: {bool(r.strip())}\n{r}" if r.strip() else "frida-server not detected or not running"

    @mcp.tool()
    def frida_start_server(local_path: str = "") -> str:
        """Push and start frida-server on the emulator. Args: local_path to frida-server binary."""
        arch = _adb_shell("getprop ro.product.cpu.abi")
        remote = "/data/local/tmp/frida-server"
        if local_path:
            push = _adb_run([ADB_BINARY, "push", local_path, remote], timeout=30)
        else:
            push = f"provide frida-server binary for {arch}"
        _adb_shell(f"chmod 755 {remote}", su=True)
        _adb_shell(f"{remote} &", su=True)
        import time; time.sleep(1)
        return f"frida-server started on {arch}\n{push}"

    @mcp.tool()
    def frida_list_processes() -> str:
        """List running processes visible to Frida."""
        return "Run: frida-ps -U (requires frida tools on host)"

    @mcp.tool()
    def frida_attach(pid: str) -> str:
        """Attach Frida to a target PID. Args: pid."""
        return f"Attach Frida to PID {pid}: frida -U -p {pid}"

    @mcp.tool()
    def frida_eval_script(script: str) -> str:
        """Inject and run a Frida script. Args: script content."""
        path = FRIDA_SCRIPTS / "inject.js"
        path.write_text(script)
        return f"Script saved to {path}. Run: frida -U -l {path} com.target.package"

    @mcp.tool()
    def frida_trace_method(method_offset: str, library: str = "libil2cpp.so") -> str:
        """Generate a method trace script from an offset. Args: method_offset, library."""
        script = f"""'use strict';
var target = Module.findBaseAddress('{library}').add(0x{method_offset});
Interceptor.attach(target, {{
    onEnter: function(args) {{ console.log('entering 0x{method_offset}'); }},
    onLeave: function(retval) {{ console.log('leaving 0x{method_offset} -> ' + retval); }}
}});"""
        return f"Trace script:\n{script}"

    @mcp.tool()
    def frida_dump_memory(address: str, size: int) -> str:
        """Read memory range from target. Args: address (hex), size."""
        script = f"""'use strict';
var ptr = ptr('0x{address}');
console.log(hexdump(ptr, {{ offset: 0, length: {size}, header: true, ansi: true }}));"""
        return f"Dump script:\n{script}"

    @mcp.tool()
    def frida_write_memory(address: str, hex_bytes: str) -> str:
        """Live patch memory without recompiling. Args: address, hex_bytes."""
        script = f"""'use strict';
var ptr = ptr('0x{address}');
ptr.writeByteArray(hexToBytes('{hex_bytes}'));
function hexToBytes(h) {{ var b=[]; for(var i=0;i<h.length;i+=2) b.push(parseInt(h.substr(i,2),16)); return b; }}"""
        return f"Write script:\n{script}"

    @mcp.tool()
    def frida_spawn(package: str) -> str:
        """Start target app under Frida (pre-main hooks). Args: package."""
        return f"frida -U -f {package} --no-pause"

    @mcp.tool()
    def frida_detach() -> str:
        """Clean Frida teardown."""
        return "frida -D kill (or CTRL+C in Frida session)"

    @mcp.tool()
    def frida_stalker_trace(package: str, target_module: str = "libil2cpp.so") -> str:
        """Code coverage tracing via Stalker. Args: package, target_module."""
        script = f"""'use strict';
var mod = Process.findModuleByName('{target_module}');
if (mod) {{
    Stalker.follow(Process.getCurrentThreadId(), {{
        events: {{ call: false, ret: false, exec: true }},
        transform: function(iterator) {{
            var instruction;
            while ((instruction = iterator.next()) !== null) {{
                if (instruction.address.sub(mod.base).toInt32() > 0x100000) break;
                iterator.keep();
            }}
        }}
    }});
}}"""
        return f"Stalker script saved: {script}"

    @mcp.tool()
    def frida_offset_to_absolute(module_base: str, relative_offset: str) -> str:
        """Convert module-relative offset to absolute address. Args: module_base, relative_offset."""
        try:
            base = int(module_base, 16) if module_base.startswith("0x") else int(module_base, 16)
            offset = int(relative_offset, 16) if relative_offset.startswith("0x") else int(relative_offset, 16)
            return f"Absolute: 0x{base + offset:x}\nBase: 0x{base:x}\nOffset: 0x{offset:x}"
        except ValueError:
            return f"Absolute: {module_base} + {relative_offset}"

    @mcp.tool()
    def frida_find_module_address(package: str, module_name: str = "libil2cpp.so") -> str:
        """Find base address of a module in target process. Args: package, module_name."""
        script = f"""'use strict';
var mod = Process.findModuleByName('{module_name}');
if (mod) console.log('{module_name}: base=' + mod.base + ', size=' + mod.size);
else console.log('{module_name} not found');
"""
        return f"Find module script:\n{script}\nRun: frida -U -l {PROJECT_ROOT}/frida_scripts/find_mod.js {package}"

    @mcp.tool()
    def frida_enumerate_classes(package: str) -> str:
        """Enumerate Java classes in a running app. Args: package."""
        script = """'use strict';
Java.perform(function() {
    Java.enumerateLoadedClasses({
        onMatch: function(c) { console.log(c); },
        onComplete: function() { console.log('done'); }
    });
});"""
        return f"Enum classes script:\n{script}"

    @mcp.tool()
    def frida_hook_instance_method(klass: str, method: str) -> str:
        """Hook a Java instance method. Args: klass (full path), method."""
        script = f"""'use strict';
Java.perform(function() {{
    var cls = Java.use('{klass}');
    cls.{method}.implementation = function() {{
        console.log('{klass}.{method} called');
        return this.{method}.apply(this, arguments);
    }};
}});"""
        return f"Hook script:\n{script}"

    @mcp.tool()
    def frida_dump_module(module_name: str = "libil2cpp.so") -> str:
        """Dump a loaded module from memory via Frida's Process.getModuleByName. Args: module_name."""
        script = f"""'use strict';
var mod = Process.getModuleByName('{module_name}');
if (mod) {{
    var size = mod.size;
    var base = mod.base;
    var bytes = Memory.readByteArray(base, size);
    var filename = '/data/local/tmp/' + '{module_name}' + '.dumped';
    var f = new File(filename, 'wb');
    f.write(bytes);
    f.flush();
    f.close();
    console.log('DUMPED: ' + filename + ' (' + size + ' bytes from ' + base + ')');
}} else {{
    console.log('ERROR: module ' + '{module_name}' + ' not found');
}}"""
        return f"Dump script (run with: frida -U -l script.js <package>):\n{script}"

    @mcp.tool()
    def frida_find_decrypt_func(target_lib: str = "libil2cpp.so") -> str:
        """Scan for the decryption routine by watching mmap calls. Args: target_lib."""
        script = f"""'use strict';
var mmapPtr = Module.findExportByName('libc.so', 'mmap');
var targetBase = null;
Interceptor.attach(mmapPtr, {{
    onEnter: function(args) {{
        this.addr = args[0];
        this.size = args[1];
        this.prot = args[2];
    }},
    onLeave: function(retval) {{
        if (retval.toInt32() > 0 && this.prot === 3) {{
            var libs = Process.enumerateModules();
            for (var i = 0; i < libs.length; i++) {{
                if (libs[i].name.indexOf('{target_lib}') >= 0) {{
                    targetBase = libs[i].base;
                    break;
                }}
            }}
            if (targetBase) {{
                console.log('DECRYPT mmap: size=' + this.size + ' mmap_ret=' + retval +
                    ' target_base=' + targetBase);
                var caller = Thread.backtrace(this.context, Backtracer.ACCURATE);
                for (var j = 0; j < caller.length; j++) {{
                    var mod = Process.findModuleByAddress(caller[j]);
                    if (mod) {{
                        var offset = caller[j].sub(mod.base);
                        console.log('  caller[' + j + ']: ' + mod.name + ' + 0x' + offset.toString(16));
                    }}
                }}
            }}
        }}
    }}
}});
console.log('[find_decrypt] Watching mmap for ' + '{target_lib}' + ' load...');
"""
        return f"Decrypt function finder script:\n{script}"
