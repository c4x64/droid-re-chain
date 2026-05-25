"""15 Live Memory Analysis & Integrity Auditing tools."""
import json
from src.shared import _adb_shell, PROJECT_ROOT, LIBS_DIR, ADB_BINARY

def _validate_pid(pid: str) -> str | None:
    if not pid.isdigit():
        return f"ERROR: invalid PID '{pid}' — must be numeric"
    return None

def register(mcp):

    @mcp.tool()
    def mem_get_process_maps(pid: str = "") -> str:
        """Parse /proc/[pid]/maps to find active memory segments. Args: pid."""
        err = _validate_pid(pid)
        if err: return err
        return _adb_shell(f"cat /proc/{pid}/maps 2>/dev/null | head -100", su=True)

    @mcp.tool()
    def mem_find_base_address(pid: str, library: str = "libil2cpp.so") -> str:
        """Locate base address allocation for a library. Args: pid, library."""
        err = _validate_pid(pid)
        if err: return err
        result = _adb_shell(f"cat /proc/{pid}/maps | grep {library} | head -5", su=True)
        if not result or "ERROR" in result:
            return f"Base address for {library} not found"
        lines = result.strip().splitlines()
        if lines:
            base = lines[0].split("-")[0] if "-" in lines[0] else "unknown"
            return f"{library} base: 0x{base}\nDetails:\n{result}"
        return f"{library} not mapped in process {pid}"

    @mcp.tool()
    def mem_read_bytes(pid: str, address: str, size: int = 64) -> str:
        """Read process memory via /proc/pid/mem. Args: pid, address (hex), size."""
        err = _validate_pid(pid)
        if err: return err
        local_path = str(LIBS_DIR / f"mem_{pid}_{address}.bin")
        cmd = f"dd if=/proc/{pid}/mem bs=1 skip=$((0x{address})) count={size} 2>/dev/null | xxd"
        result = _adb_shell(cmd, su=True)
        return json.dumps({"pid": pid, "address": address, "size": size, "hexdump": result[:2000]}, indent=2)

    @mcp.tool()
    def mem_write_bytes(pid: str, address: str, hex_bytes: str) -> str:
        """Overwrite process memory at a given address. Args: pid, address (hex), hex_bytes."""
        err = _validate_pid(pid)
        if err: return err
        data = bytes.fromhex(hex_bytes.replace(" ", ""))
        escaped = data.hex()
        cmd = f"echo '{escaped}' | xxd -r -p 2>/dev/null | dd of=/proc/{pid}/mem bs=1 seek=$((0x{address})) count={len(data)} 2>/dev/null"
        result = _adb_shell(cmd, su=True)
        return json.dumps({"pid": pid, "address": address, "bytes_written": len(data), "result": result[:500]}, indent=2)

    @mcp.tool()
    def mem_scan_pattern(pid: str, pattern_hex: str) -> str:
        """Scan memory for a hex pattern across all rw-p segments. Args: pid, pattern_hex."""
        err = _validate_pid(pid)
        if err: return err
        pat = pattern_hex.replace(" ", "").upper()
        cmd = f"for map in $(grep 'rw-p' /proc/{pid}/maps | awk '{{print $1}}'); do start=$(echo $map | cut -d- -f1); end=$(echo $map | cut -d- -f2); dd if=/proc/{pid}/mem bs=4096 skip=$((0x$start/4096)) count=$(((0x$end-0x$start)/4096)) 2>/dev/null | xxd -p | grep -ob '{pat}' && echo FOUND:$map; done"
        result = _adb_shell(cmd, su=True)
        hits = [l for l in result.splitlines() if "FOUND:" in l]
        return json.dumps({"pid": pid, "pattern": pattern_hex, "matches": len(hits), "detail": result[:1500]}, indent=2)

    @mcp.tool()
    def mem_dump_segment(pid: str, start_addr: str, size: int) -> str:
        """Dump a memory segment to a file on host. Args: pid, start_addr (hex), size."""
        err = _validate_pid(pid)
        if err: return err
        local_path = str(LIBS_DIR / f"mem_dump_{pid}_{start_addr}.bin")
        device_path = f"/data/local/tmp/dump_{pid}_{start_addr}.bin"
        dump_cmd = f"dd if=/proc/{pid}/mem bs=4096 skip=$((0x{start_addr}/4096)) count={((size + 4095) // 4096)} 2>/dev/null > {device_path}"
        _adb_shell(dump_cmd, su=True)
        pull = f"{ADB_BINARY} pull {device_path} {local_path}".replace("adb", ADB_BINARY)
        return json.dumps({"pid": pid, "address": start_addr, "size": size, "device_path": device_path, "local_path": local_path, "pull_command": pull}, indent=2)

    @mcp.tool()
    def mem_check_protection(pid: str, address: str) -> str:
        """Evaluate active page permissions. Args: pid, address."""
        err = _validate_pid(pid)
        if err: return err
        return _adb_shell(f"cat /proc/{pid}/maps | grep {address}", su=True)

    @mcp.tool()
    def mem_verify_checksum(pid: str, address: str, expected_hash: str) -> str:
        """Verify SHA-256 hash of a memory region. Args: pid, address, expected_hash."""
        err = _validate_pid(pid)
        if err: return err
        cmd = f"dd if=/proc/{pid}/mem bs=4096 skip=$((0x{address}/4096)) count=4 2>/dev/null | sha256sum | cut -d' ' -f1"
        actual = _adb_shell(cmd, su=True).strip()
        match = actual == expected_hash.lower()
        return json.dumps({"pid": pid, "address": address, "expected": expected_hash, "actual": actual, "match": match}, indent=2)

    @mcp.tool()
    def mem_monitor_value_change(pid: str, address: str, interval_sec: int = 2) -> str:
        """Poll memory for changes over time via repeated reads. Args: pid, address, interval_sec."""
        err = _validate_pid(pid)
        if err: return err
        cmd = f"for i in 1 2 3; do echo -n '[$i] '; dd if=/proc/{pid}/mem bs=4 skip=$((0x{address}/4)) count=1 2>/dev/null | xxd -p; sleep {interval_sec}; done"
        result = _adb_shell(cmd, su=True)
        return json.dumps({"pid": pid, "address": address, "interval_sec": interval_sec, "snapshots": result[:1000]}, indent=2)

    @mcp.tool()
    def mem_locate_pointer_chains(pid: str, base_address: str, depth: int = 5) -> str:
        """Trace pointer chain by following memory references. Args: pid, base_address, depth."""
        err = _validate_pid(pid)
        if err: return err
        chain = [base_address]
        current = base_address
        for _ in range(depth):
            cmd = f"dd if=/proc/{pid}/mem bs=8 skip=$((0x{current}/8)) count=1 2>/dev/null | xxd -e -p"
            next_addr = _adb_shell(cmd, su=True).strip()
            if not next_addr or len(next_addr) < 8:
                break
            next_addr = next_addr.strip()[:16].lstrip("0") or "0"
            chain.append(f"0x{next_addr}")
            current = f"0x{next_addr}"
        return json.dumps({"pid": pid, "base": base_address, "depth": len(chain) - 1, "chain": chain}, indent=2)

    @mcp.tool()
    def mem_get_region_size(pid: str, library: str = "libil2cpp.so") -> str:
        """Calculate total contiguous block allocations. Args: pid, library."""
        err = _validate_pid(pid)
        if err: return err
        result = _adb_shell(f"cat /proc/{pid}/maps | grep {library}", su=True)
        total = 0
        for line in result.splitlines():
            if "-" in line:
                parts = line.split()[0].split("-")
                if len(parts) == 2:
                    try:
                        total += int(parts[1], 16) - int(parts[0], 16)
                    except ValueError:
                        pass
        return json.dumps({"pid": pid, "library": library, "total_bytes": total, "total_kb": round(total/1024, 1), "mappings": result[:1000]}, indent=2)

    @mcp.tool()
    def mem_detect_hook_overwrites(pid: str, library: str, target_method_offset: str) -> str:
        """Read function entry bytes and compare to expected signature. Args: pid, library, target_method_offset."""
        err = _validate_pid(pid)
        if err: return err
        base_cmd = f"grep {library} /proc/{pid}/maps | head -1 | cut -d- -f1"
        base_hex = _adb_shell(base_cmd, su=True).strip()
        if not base_hex or len(base_hex) < 8:
            return json.dumps({"error": f"library {library} not found in PID {pid}"}, indent=2)
        addr = int(base_hex, 16) + int(target_method_offset, 16)
        cmd = f"dd if=/proc/{pid}/mem bs=16 skip=$(({addr}/16)) count=1 2>/dev/null | xxd -p"
        bytes_at = _adb_shell(cmd, su=True).strip()
        return json.dumps({"pid": pid, "library": library, "offset": target_method_offset, "absolute": hex(addr), "current_bytes": bytes_at[:32]}, indent=2)

    @mcp.tool()
    def mem_alloc_sandbox_page(size: int = 4096) -> str:
        """Allocate a temporary file-backed sandbox page. Args: size (default 4096)."""
        import time
        path = f"/data/local/tmp/sandbox_{int(time.time())}.bin"
        cmd = f"dd if=/dev/zero bs=1 count={size} 2>/dev/null > {path} && chmod 600 {path}"
        result = _adb_shell(cmd, su=True)
        return json.dumps({"path": path, "size": size, "status": "allocated", "result": result[:200]}, indent=2)

    @mcp.tool()
    def mem_free_sandbox_page(path: str) -> str:
        """Release a previously allocated sandbox page. Args: path."""
        result = _adb_shell(f"rm -f {path}", su=True)
        return json.dumps({"path": path, "status": "freed", "result": result[:200]}, indent=2)

    @mcp.tool()
    def mem_audit_integrity_loops(pid: str) -> str:
        """Count executable/writable memory regions (potential anti-cheat scanning). Args: pid."""
        err = _validate_pid(pid)
        if err: return err
        rwx_count = _adb_shell(f'cat /proc/{pid}/maps | grep -c "rwx"', su=True).strip()
        rx_count = _adb_shell(f'cat /proc/{pid}/maps | grep -c "r-xp"', su=True).strip()
        total_maps = _adb_shell(f'cat /proc/{pid}/maps | wc -l', su=True).strip()
        return json.dumps({"pid": pid, "rwx_regions": rwx_count, "executable_regions": rx_count, "total_mappings": total_maps}, indent=2)
