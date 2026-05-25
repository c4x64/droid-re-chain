"""Runtime library dumping, ELF repair, symbol recovery, and post-dump tools."""
import os
import re
import json
import struct
import subprocess
from pathlib import Path
from src.shared import ADB_BINARY, _adb_shell, LIBS_DIR, PROJECT_ROOT

DUMP_DIR = PROJECT_ROOT / "dumps"
DUMP_DIR.mkdir(exist_ok=True)

def _read_elf_word(data: bytes, offset: int) -> int:
    return struct.unpack_from("<I", data, offset)[0]

def _read_elf_half(data: bytes, offset: int) -> int:
    return struct.unpack_from("<H", data, offset)[0]

def _read_elf_ehdr(data: bytes) -> dict:
    if len(data) < 64 or data[:4] != b"\x7fELF":
        return {"valid": False}
    return {
        "valid": True, "ei_class": data[4], "ei_data": data[5],
        "e_type": _read_elf_half(data, 16), "e_machine": _read_elf_half(data, 18),
        "e_version": _read_elf_word(data, 20), "e_entry": struct.unpack_from("<Q", data, 24)[0],
        "e_phoff": struct.unpack_from("<Q", data, 32)[0],
        "e_shoff": struct.unpack_from("<Q", data, 40)[0],
        "e_flags": _read_elf_word(data, 48),
        "e_ehsize": _read_elf_half(data, 52),
        "e_phentsize": _read_elf_half(data, 54), "e_phnum": _read_elf_half(data, 56),
        "e_shentsize": _read_elf_half(data, 58), "e_shnum": _read_elf_half(data, 60),
        "e_shstrndx": _read_elf_half(data, 62),
    }

def register(mcp):

    @mcp.tool()
    def dump_lib_from_memory(pid: str, lib_name: str = "libil2cpp.so") -> str:
        """Dump a loaded .so from process memory via Frida. Args: pid, lib_name."""
        script = f"""'use strict';
var mod = Process.getModuleByName('{lib_name}');
if (!mod) {{
    console.log('ERROR: module {lib_name} not found in process');
    [[exit]]
}}
var size = mod.size;
var base = mod.base;
var bytes = Memory.readByteArray(base, size);
var filename = '/data/local/tmp/{lib_name}.dumped';
var f = new File(filename, 'wb');
f.write(bytes);
f.flush();
f.close();
console.log('OK: ' + filename + '|size=' + size + '|base=' + base);
"""
        pull = f"Run the Frida script, then pull the dump:\n  frida -U -p {pid} -l script.js\n  {ADB_BINARY} pull /data/local/tmp/{lib_name}.dumped {DUMP_DIR}/"
        return pull

    @mcp.tool()
    def dump_all_libs(pid: str) -> str:
        """Dump every loaded native library from a process at once. Args: pid."""
        script = """'use strict';
var mods = Process.enumerateModules();
var dumpDir = '/data/local/tmp/dump_all/';
Java.perform(function() {
    var File = Java.use('java.io.File');
    var dir = File.$new(dumpDir);
    dir.mkdirs();
});
for (var i = 0; i < mods.length; i++) {
    var mod = mods[i];
    if (mod.path.indexOf('.so') < 0) continue;
    try {
        var bytes = Memory.readByteArray(mod.base, mod.size);
        var filename = dumpDir + mod.name.replace(/[\\\\/:*?\"<>|]/g, '_');
        var f = new File(filename, 'wb');
        f.write(bytes);
        f.flush();
        f.close();
        console.log('DUMPED: ' + mod.name + ' [' + mod.base + '] ' + mod.size + ' bytes');
    } catch (e) {
        console.log('FAIL: ' + mod.name + ' - ' + e);
    }
}
console.log('DONE: dumps in ' + dumpDir);
"""
        return f"Run: frida -U -p {pid} -l script.js\nThen: {ADB_BINARY} pull /data/local/tmp/dump_all/ {DUMP_DIR}/"

    @mcp.tool()
    def dump_at_entrypoint(package: str, lib_to_dump: str = "libil2cpp.so") -> str:
        """Hook dlopen and dump the library at load time, before self-modification. Args: package, lib_to_dump."""
        script = f"""'use strict';
var dlopenPtr = Module.findExportByName('libdl.so', 'android_dlopen_ext') ||
                Module.findExportByName(null, 'dlopen');
var targetLib = '{lib_to_dump}';
var dumped = false;
Interceptor.attach(dlopenPtr, {{
    onEnter: function(args) {{
        var path = args[0].readCString();
        if (path && path.indexOf(targetLib) >= 0 && !dumped) {{
            console.log('[entrypoint] ' + targetLib + ' loading from: ' + path);
        }}
    }},
    onLeave: function(retval) {{
        if (retval.toInt32() > 0 && !dumped) {{
            var mod = Process.findModuleByName(targetLib);
            if (mod) {{
                var bytes = Memory.readByteArray(mod.base, mod.size);
                var filename = '/data/local/tmp/{lib_to_dump}.entrypoint_dump';
                var f = new File(filename, 'wb');
                f.write(bytes);
                f.flush();
                f.close();
                dumped = true;
                console.log('ENTRYPOINT_DUMP: ' + filename + ' | size=' + mod.size);
            }}
        }}
    }}
}});
console.log('[entrypoint] Watching dlopen for ' + targetLib);
"""
        return f"Run: frida -U -f {package} -l script.js --no-pause\nThen pull: {ADB_BINARY} pull /data/local/tmp/{lib_to_dump}.entrypoint_dump {DUMP_DIR}/"

    @mcp.tool()
    def dump_after_unpack(package: str, lib_to_dump: str = "libil2cpp.so",
                          signal_function: str = "il2cpp_init") -> str:
        """Wait for a known unpack signal function, then dump. Args: package, lib_to_dump, signal_function."""
        script = f"""'use strict';
var targetLib = '{lib_to_dump}';
var signalFn = '{signal_function}';
var dumped = false;
var mod = Process.findModuleByName(targetLib);
if (!mod) {{
    console.log('Waiting for ' + targetLib + ' to load...');
    var dlopenPtr = Module.findExportByName(null, 'dlopen');
    Interceptor.attach(dlopenPtr, {{
        onLeave: function(retval) {{
            if (retval.toInt32() > 0) {{
                mod = Process.findModuleByName(targetLib);
            }}
        }}
    }});
}}
function doDump() {{
    if (dumped) return;
    mod = Process.findModuleByName(targetLib);
    if (!mod) {{ console.log('ERROR: ' + targetLib + ' not found'); return; }}
    var bytes = Memory.readByteArray(mod.base, mod.size);
    var filename = '/data/local/tmp/{lib_to_dump}.unpacked';
    var f = new File(filename, 'wb');
    f.write(bytes);
    f.flush();
    f.close();
    dumped = true;
    console.log('UNPACK_DUMP: ' + filename + ' | size=' + mod.size + ' | base=' + mod.base);
}}
var exports = null;
try {{
    var allMods = Process.enumerateModules();
    for (var i = 0; i < allMods.length; i++) {{
        if (allMods[i].name.indexOf(targetLib) >= 0) {{
            try {{
                exports = Module.enumerateExports(targetLib);
            }} catch(e) {{}}
            break;
        }}
    }}
}} catch(e) {{}}
if (exports) {{
    for (var j = 0; j < exports.length; j++) {{
        if (exports[j].name.indexOf(signalFn) >= 0) {{
            Interceptor.attach(exports[j].address, {{
                onEnter: function(args) {{
                    console.log('[unpack_signal] ' + signalFn + ' called — dumping');
                    doDump();
                }}
            }});
            break;
        }}
    }}
}}
if (!dumped) {{
    setTimeout(doDump, 5000);
}}
console.log('[unpack] Dump will trigger on ' + signalFn + ' call');
"""
        return f"Run: frida -U -f {package} -l script.js --no-pause\nThen pull: {ADB_BINARY} pull /data/local/tmp/{lib_to_dump}.unpacked {DUMP_DIR}/"

    @mcp.tool()
    def fix_elf_header(binary_path: str) -> str:
        """Repair a corrupted ELF header using program headers still valid in memory.
        Args: binary_path."""
        if not os.path.isfile(binary_path):
            return f"ERROR: file not found: {binary_path}"
        try:
            with open(binary_path, "rb") as f:
                data = bytearray(f.read())
        except Exception as e:
            return f"ERROR: {e}"
        ehdr = _read_elf_ehdr(data)
        if not ehdr["valid"]:
            return "ERROR: not a valid ELF (missing magic)"
        repairs = []
        if ehdr["e_phoff"] == 0 or ehdr["e_phoff"] > len(data):
            for off in range(0x40, min(0x1000, len(data)), 8):
                if data[off:off+4] == b"\x01\x00\x00\x00":
                    cand = struct.unpack_from("<Q", data, off - 8)[0]
                    if 0x40 < cand < len(data):
                        struct.pack_into("<Q", data, 32, cand)
                        repairs.append(f"e_phoff: 0 -> 0x{cand:x}")
                        break
        if ehdr["e_shoff"] == 0 or ehdr["e_shoff"] > len(data):
            repairs.append("e_shoff: 0 (section headers stripped — use reconstruct_section_headers)")
        if ehdr["e_phnum"] == 0:
            repairs.append("e_phnum: 0 (corrupted)")
        if ehdr["e_shnum"] == 0:
            repairs.append("e_shnum: 0 (section headers stripped)")
        if ehdr["e_ehsize"] < 64:
            struct.pack_into("<H", data, 52, 64)
            repairs.append("e_ehsize: corrected to 64")
        out_path = str(Path(binary_path).with_suffix(".fixed.elf"))
        with open(out_path, "wb") as f:
            f.write(data)
        return json.dumps({"input": binary_path, "output": out_path,
                           "repairs": repairs, "repair_count": len(repairs),
                           "elf_class": "64-bit" if ehdr["ei_class"] == 2 else "32-bit",
                           "arch": {0x28: "ARM", 0xB7: "AArch64", 0x3E: "x86-64"}.get(ehdr["e_machine"], "unknown")}, indent=2)

    @mcp.tool()
    def fix_so_imports(binary_path: str, reference_binary: str = "") -> str:
        """Rebuild the import table from memory when .dynsym is zeroed on disk.
        Args: binary_path, reference_binary (optional, provides known imports)."""
        if not os.path.isfile(binary_path):
            return f"ERROR: file not found: {binary_path}"
        try:
            with open(binary_path, "rb") as f:
                data = bytearray(f.read())
        except Exception as e:
            return f"ERROR: {e}"
        imports_found = []
        if reference_binary and os.path.isfile(reference_binary):
            try:
                r = subprocess.run(["readelf", "--dyn-syms", reference_binary],
                                   capture_output=True, text=True, timeout=15)
                for line in r.stdout.splitlines():
                    if "FUNC" in line and "GLOBAL" in line:
                        parts = line.split()
                        if len(parts) >= 8:
                            imports_found.append({"name": parts[-1], "type": "FUNC"})
            except Exception:
                pass
        try:
            r = subprocess.run(["readelf", "-d", binary_path], capture_output=True, text=True, timeout=15)
            for line in r.stdout.splitlines():
                if "NEEDED" in line:
                    lib = line.split("[")[-1].split("]")[0] if "[" in line else ""
                    if lib:
                        imports_found.append({"name": f"[NEEDED] {lib}", "type": "NEEDED"})
        except Exception:
            pass
        count = len(imports_found)
        return json.dumps({"binary": binary_path, "reference": reference_binary or "none",
                           "imports_rebuilt": count, "imports": imports_found[:30],
                           "note": "Use this output to reconstruct .dynsym entries manually" if count == 0 else ""}, indent=2)

    @mcp.tool()
    def reconstruct_section_headers(binary_path: str) -> str:
        """Rebuild section headers from program headers (PT_LOAD segments). Args: binary_path."""
        if not os.path.isfile(binary_path):
            return f"ERROR: file not found: {binary_path}"
        try:
            with open(binary_path, "rb") as f:
                data = f.read()
        except Exception as e:
            return f"ERROR: {e}"
        ehdr = _read_elf_ehdr(data)
        if not ehdr["valid"]:
            return "ERROR: not a valid ELF"
        if ehdr["e_phoff"] == 0 or ehdr["e_phnum"] == 0:
            return "ERROR: program headers missing — cannot reconstruct sections"
        segments = []
        is_64 = ehdr["ei_class"] == 2
        phdr_entry_size = 56 if is_64 else 32
        phdr_start = ehdr["e_phoff"]
        for i in range(ehdr["e_phnum"]):
            off = phdr_start + i * phdr_entry_size
            if off + phdr_entry_size > len(data):
                break
            if is_64:
                p_type = _read_elf_word(data, off)
                p_offset = struct.unpack_from("<Q", data, off + 8)[0]
                p_filesz = struct.unpack_from("<Q", data, off + 32)[0]
                p_flags = _read_elf_word(data, off + 4)
            else:
                p_type = _read_elf_word(data, off)
                p_offset = struct.unpack_from("<I", data, off + 4)[0]
                p_filesz = struct.unpack_from("<I", data, off + 16)[0]
                p_flags = _read_elf_word(data, off + 24)
            if p_type == 1:
                seg_type = "LOAD"
            elif p_type == 4:
                seg_type = "NOTE"
            elif p_type == 0x6474e550:
                seg_type = "GNU_EH_FRAME"
            elif p_type == 0x6474e551:
                seg_type = "GNU_STACK"
            elif p_type == 0x6474e552:
                seg_type = "GNU_RELRO"
            elif p_type == 2:
                seg_type = "DYNAMIC"
            else:
                seg_type = f"PT_0x{p_type:x}"
            segments.append({"index": i, "type": seg_type, "offset": hex(p_offset),
                             "filesz": hex(p_filesz), "flags": hex(p_flags)})
        sections = []
        for seg in segments:
            if seg["type"] == "LOAD":
                sections.append({"name": f".segment_{seg['index']}", "type": "PROGBITS",
                                 "offset": seg["offset"], "size": seg["filesz"],
                                 "flags": seg["flags"]})
        return json.dumps({"binary": binary_path, "segments_found": len(segments),
                           "segments": segments,
                           "suggested_sections": sections}, indent=2)

    @mcp.tool()
    def validate_dumped_elf(binary_path: str) -> str:
        """Verify a dumped binary is loadable: magic, entry point within file, program headers valid.
        Args: binary_path."""
        if not os.path.isfile(binary_path):
            return f"ERROR: file not found: {binary_path}"
        results = {"path": binary_path, "valid": False, "checks": []}
        try:
            with open(binary_path, "rb") as f:
                data = f.read()
        except Exception as e:
            results["checks"].append({"check": "read", "status": f"FAIL: {e}"})
            return json.dumps(results, indent=2)
        if data[:4] == b"\x7fELF":
            results["checks"].append({"check": "magic", "status": "PASS"})
        else:
            results["checks"].append({"check": "magic", "status": f"FAIL: got {data[:4].hex()}"})
            return json.dumps(results, indent=2)
        ehdr = _read_elf_ehdr(data)
        if ehdr["e_entry"] and ehdr["e_entry"] < len(data):
            results["checks"].append({"check": "entry_point", "status": "PASS",
                                      "detail": f"0x{ehdr['e_entry']:x}"})
        else:
            results["checks"].append({"check": "entry_point", "status": f"FAIL: 0x{ehdr['e_entry']:x} outside file"})
        if ehdr["e_phoff"] and ehdr["e_phnum"] and ehdr["e_phoff"] + ehdr["e_phnum"] * ehdr["e_phentsize"] <= len(data):
            results["checks"].append({"check": "program_headers", "status": "PASS",
                                      "detail": f"{ehdr['e_phnum']} headers @ 0x{ehdr['e_phoff']:x}"})
        else:
            results["checks"].append({"check": "program_headers", "status": "FAIL"})
        if ehdr["e_shoff"] and ehdr["e_shnum"]:
            results["checks"].append({"check": "section_headers", "status": "INFO",
                                      "detail": f"{ehdr['e_shnum']} headers @ 0x{ehdr['e_shoff']:x} (may be stripped)"})
        else:
            results["checks"].append({"check": "section_headers", "status": "INFO", "detail": "section headers stripped"})
        try:
            import subprocess
            r = subprocess.run(["readelf", "-l", binary_path], capture_output=True, text=True, timeout=15)
            if r.returncode == 0:
                results["checks"].append({"check": "readelf_parse", "status": "PASS"})
                results["checks"].append({"check": "architecture",
                                          "status": next((l.split(":")[1].strip() for l in r.stdout.splitlines() if "Machine:" in l), "unknown")})
        except Exception:
            pass
        results["valid"] = all(c["status"] == "PASS" for c in results["checks"] if c["status"].startswith("FAIL"))
        results["total_checks"] = len(results["checks"])
        return json.dumps(results, indent=2)

    @mcp.tool()
    def recover_symbols_from_memory(binary_path: str) -> str:
        """Scan a dumped library for surviving symbol hash tables when .dynsym is wiped.
        Args: binary_path."""
        if not os.path.isfile(binary_path):
            return f"ERROR: file not found: {binary_path}"
        try:
            with open(binary_path, "rb") as f:
                data = f.read()
        except Exception as e:
            return f"ERROR: {e}"
        symbols = []
        for off in range(0, len(data) - 32, 4):
            if data[off:off+2] == b"\x01\x00":
                name_ptr = struct.unpack_from("<Q" if len(data) > 0xFFFFFFFF else "<I", data, off + 8)[0]
                if 0 < name_ptr < len(data):
                    end = data.find(b"\x00", name_ptr)
                    if end > name_ptr:
                        name = data[name_ptr:end].decode("ascii", errors="replace")
                        if name and len(name) > 1 and name[0].isalpha():
                            symbols.append({"offset": hex(off), "name": name, "type": "candidate"})
        if len(symbols) > 200:
            symbols = symbols[:200]
        return json.dumps({"binary": binary_path, "total_candidates": len(symbols),
                           "symbols": symbols[:50],
                           "note": "These are heuristic candidates — cross-check with match_dumped_to_original"}, indent=2)

    @mcp.tool()
    def match_dumped_to_original(disk_path: str, dumped_path: str) -> str:
        """Diff the on-disk version against the memory-dumped version to identify packer modifications.
        Args: disk_path, dumped_path."""
        if not os.path.isfile(disk_path) or not os.path.isfile(dumped_path):
            return "ERROR: one or both files not found"
        try:
            with open(disk_path, "rb") as f:
                disk = f.read()
            with open(dumped_path, "rb") as f:
                dumped = f.read()
        except Exception as e:
            return f"ERROR: {e}"
        import hashlib
        disk_hash = hashlib.sha256(disk).hexdigest()[:16]
        dumped_hash = hashlib.sha256(dumped).hexdigest()[:16]
        if disk_hash == dumped_hash:
            return json.dumps({"identical": True, "disk_hash": disk_hash, "dumped_hash": dumped_hash}, indent=2)
        diffs = []
        min_len = min(len(disk), len(dumped))
        for i in range(0, min_len, 64):
            if disk[i:i+64] != dumped[i:i+64]:
                if not diffs or i - diffs[-1]["offset"] > 4096:
                    disk_bytes = disk[i:i+32].hex()
                    dump_bytes = dumped[i:i+32].hex()
                    diffs.append({"offset": hex(i), "disk": disk_bytes, "dumped": dump_bytes})
        size_diff = len(dumped) - len(disk)
        return json.dumps({"identical": False, "disk_hash": disk_hash, "dumped_hash": dumped_hash,
                           "disk_size": len(disk), "dumped_size": len(dumped), "size_diff": size_diff,
                           "diff_count": len(diffs), "differences": diffs[:20],
                           "note": "Differences indicate packer modifications" if diffs else "No structural differences"}, indent=2)