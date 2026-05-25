"""7 Static Analysis tools — disassembly, strings, obfuscation detection, checksec."""
import os
import re
import json
import struct
from pathlib import Path
from src.shared import LIBS_DIR, PROJECT_ROOT

def _supports_capstone():
    try:
        import capstone
        return True
    except ImportError:
        return False

def _read_elf_header(path: str) -> dict:
    result = {"path": path, "nx": False, "pie": False, "relro": False, "canary": False, "arch": ""}
    if not os.path.isfile(path):
        result["error"] = "file not found"
        return result
    try:
        with open(path, "rb") as f:
            header = f.read(64)
        if header[:4] != b"\x7fELF":
            result["error"] = "not an ELF"
            return result
        result["arch"] = "AArch64" if header[4] == 2 and (header[18] | header[19] << 8) == 183 else "ARM32" if header[4] == 1 and (header[18] | header[19] << 8) == 40 else "x86_64" if header[4] == 2 and (header[18] | header[19] << 8) == 62 else "unknown"
        result["nx"] = True
        try:
            import subprocess
            r = subprocess.run(["readelf", "-l", path], capture_output=True, text=True, timeout=15)
            for line in r.stdout.splitlines():
                if "GNU_STACK" in line and "E" in line:
                    result["nx"] = False
                if "GNU_RELRO" in line:
                    result["relro"] = True
                if "DYNAMIC" in line:
                    result["pie"] = True
            r2 = subprocess.run(["readelf", "-s", path], capture_output=True, text=True, timeout=15)
            if "__stack_chk_fail" in r2.stdout or "__intel_security_cookie" in r2.stdout:
                result["canary"] = True
        except Exception:
            pass
    except Exception as e:
        result["error"] = str(e)
    return result

def register(mcp):

    @mcp.tool()
    def static_disassemble_offset(binary_path: str, offset: str, count: int = 16) -> str:
        """Disassemble ARM64 at a given file offset using Capstone. Args: binary_path, offset (hex), count (instructions)."""
        if not _supports_capstone():
            return "Capstone not installed. Run: pip install capstone"
        from capstone import Cs, CS_ARCH_AARCH64, CS_MODE_ARM
        offset_int = int(offset, 16) if offset.startswith("0x") else int(offset, 16)
        try:
            with open(binary_path, "rb") as f:
                f.seek(offset_int)
                code = f.read(count * 4 + 16)
        except Exception as e:
            return f"ERROR reading binary: {e}"
        md = Cs(CS_ARCH_AARCH64, CS_MODE_ARM)
        md.detail = False
        lines = []
        for i, (addr, size, mnemonic, op_str) in enumerate(md.disasm_lite(code, offset_int)):
            if i >= count:
                break
            lines.append(f"0x{addr:x}:  {mnemonic:10s} {op_str}")
        return "\n".join(lines) if lines else "no instructions at offset"

    @mcp.tool()
    def static_find_string_xrefs(binary_path: str, search: str) -> str:
        """Scan binary for a string and find nearby code references. Args: binary_path, search string."""
        if not os.path.isfile(binary_path):
            return f"ERROR: file not found: {binary_path}"
        try:
            with open(binary_path, "rb") as f:
                data = f.read()
        except Exception as e:
            return f"ERROR: {e}"
        targets = []
        pos = 0
        while True:
            pos = data.find(search.encode(), pos)
            if pos == -1:
                break
            start = max(0, pos - 64)
            end = min(len(data), pos + len(search) + 64)
            context = data[start:end]
            prefix = "..." if start > 0 else ""
            suffix = "..." if end < len(data) else ""
            targets.append({"offset": hex(pos), "context": prefix + context.hex()[:96] + suffix})
            pos += 1
        return json.dumps({"string": search, "occurrences": len(targets),
                           "results": targets[:20], "binary": binary_path}, indent=2)

    @mcp.tool()
    def static_detect_obfuscation(binary_path: str) -> str:
        """Heuristic check for obfuscation: OLLVM, symbol stripping, section anomalies. Args: binary_path."""
        if not os.path.isfile(binary_path):
            return f"ERROR: file not found: {binary_path}"
        flags = []
        try:
            import subprocess
            r = subprocess.run(["readelf", "-S", binary_path], capture_output=True, text=True, timeout=15)
            sections = r.stdout
            if ".text" not in sections:
                flags.append("missing .text section (stripped or packed)")
            if ".bss" not in sections and ".data" not in sections:
                flags.append("missing standard data sections")
            r2 = subprocess.run(["nm", "-D", binary_path], capture_output=True, text=True, timeout=15)
            symbols = r2.stdout.strip().splitlines()
            if len(symbols) == 0:
                flags.append("all symbols stripped")
            elif len(symbols) < 5:
                flags.append(f"minimal symbols ({len(symbols)})")
            if not flags:
                flags.append("no obvious obfuscation detected")
        except FileNotFoundError:
            flags.append("readelf/nm not available")
        except Exception as e:
            flags.append(f"error: {e}")
        return json.dumps({"binary": binary_path, "flags": flags, "obfuscated": len(flags) > 1}, indent=2)

    @mcp.tool()
    def static_checksec(binary_path: str) -> str:
        """Security check: NX, PIE, RELRO, stack canary. Args: binary_path (default: libs/libmod.so)."""
        path = binary_path
        if not path:
            for c in [LIBS_DIR / "libmod_stripped.so", LIBS_DIR / "libmod.so"]:
                if c.exists():
                    path = str(c)
                    break
        if not path or not os.path.isfile(path):
            return "ERROR: no binary specified or found in libs/"
        result = _read_elf_header(path)
        if result.get("error"):
            return f"ERROR: {result['error']}"
        return json.dumps({k: result[k] for k in ["arch", "nx", "pie", "relro", "canary"]}, indent=2)

    @mcp.tool()
    def static_find_crypto_constants(binary_path: str) -> str:
        """Scan binary for known crypto constant tables (AES, RC4, MD5, etc.). Args: binary_path."""
        if not os.path.isfile(binary_path):
            return f"ERROR: file not found: {binary_path}"
        try:
            with open(binary_path, "rb") as f:
                data = f.read()
        except Exception as e:
            return f"ERROR: {e}"
        SIGNATURES = {
            "AES_SBOX": (b"\x63\x7c\x77\x7b\xf2\x6b\x6f\xc5", "AES substitution box"),
            "AES_RSBOX": (b"\x52\x09\x6a\xd5\x30\x36\xa5\x38", "AES reverse S-box"),
            "RC4_KEY": (b"\x00\x01\x02\x03\x04\x05\x06\x07", "RC4 identity key schedule"),
            "MD5_INIT": (b"\x01\x23\x45\x67\x89\xab\xcd\xef", "MD5 initial constants"),
            "SHA256_INIT": (b"\x6a\x09\xe6\x67\xbb\x67\xae\x85", "SHA-256 initial hash"),
            "BASE64_TABLE": (b"\x41\x42\x43\x44\x45\x46\x47\x48", "Base64 alphabet start"),
        }
        found = []
        for name, (sig, desc) in SIGNATURES.items():
            pos = data.find(sig)
            if pos != -1:
                found.append({"name": name, "description": desc, "offset": hex(pos)})
        return json.dumps({"binary": binary_path, "found": found, "count": len(found)}, indent=2)

    @mcp.tool()
    def static_extract_urls(binary_path: str) -> str:
        """Extract hardcoded URLs and API endpoints from binary. Args: binary_path."""
        if not os.path.isfile(binary_path):
            return f"ERROR: file not found: {binary_path}"
        try:
            with open(binary_path, "rb") as f:
                data = f.read()
        except Exception as e:
            return f"ERROR: {e}"
        strings = []
        current = b""
        for byte in data:
            if 32 <= byte < 127:
                current += bytes([byte])
            else:
                if len(current) >= 6:
                    strings.append(current.decode("ascii", errors="replace"))
                current = b""
        url_pattern = re.compile(r'https?://[^\s"\'<>]+')
        ip_pattern = re.compile(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d+\b')
        urls = []
        for s in strings:
            for m in url_pattern.finditer(s):
                urls.append({"type": "url", "value": m.group(), "length": len(m.group())})
            for m in ip_pattern.finditer(s):
                urls.append({"type": "ip:port", "value": m.group(), "length": len(m.group())})
        return json.dumps({"binary": binary_path, "endpoints": urls[:30], "count": len(urls)}, indent=2)

    @mcp.tool()
    def static_call_graph(binary_path: str, entry_offset: str) -> str:
        """Build a local call graph from an offset using BL instructions. Args: binary_path, entry_offset (hex)."""
        if not os.path.isfile(binary_path):
            return f"ERROR: file not found: {binary_path}"
        entry = int(entry_offset, 16) if entry_offset.startswith("0x") else int(entry_offset, 16)
        try:
            with open(binary_path, "rb") as f:
                data = f.read()
        except Exception as e:
            return f"ERROR: {e}"
        calls = []
        visited = set()
        stack = [entry]
        while stack and len(calls) < 200:
            addr = stack.pop()
            if addr in visited:
                continue
            visited.add(addr)
            chunk = data[addr:addr + 256]
            for i in range(0, len(chunk) - 4, 4):
                instr = struct.unpack("<I", chunk[i:i + 4])[0]
                if (instr & 0xFC000000) == 0x14000000:
                    imm = instr & 0x03FFFFFF
                    if instr & 0x02000000:
                        imm |= ~0x03FFFFFF
                    target = addr + i + (imm << 2)
                    if target < len(data):
                        calls.append({"from": hex(addr + i), "to": hex(target)})
                        if target not in visited:
                            stack.append(target)
        return json.dumps({"entry": hex(entry), "nodes_visited": len(visited),
                           "edges": calls[:100], "total_calls_found": len(calls)}, indent=2)