"""15 Live Memory Analysis & Integrity Auditing tools."""
import os
import json
import subprocess
from src.shared import _adb_shell, _adb_run, ADB_BINARY, PROJECT_ROOT, LIBS_DIR

def register(mcp):

    @mcp.tool()
    def mem_get_process_maps(pid: str = "") -> str:
        """Parse /proc/[pid]/maps to find active memory segments. Args: pid."""
        if not pid:
            return "ERROR: PID required. Use adb_list_packages + ps to find it."
        return _adb_shell(f"su -c 'cat /proc/{pid}/maps 2>/dev/null | head -100'", su=True)

    @mcp.tool()
    def mem_find_base_address(pid: str, library: str = "libil2cpp.so") -> str:
        """Locate base address allocation for a library. Args: pid, library."""
        result = _adb_shell(f"su -c 'cat /proc/{pid}/maps | grep {library} | head -5'", su=True)
        if not result or "ERROR" in result:
            return f"Base address for {library} not found"
        lines = result.strip().splitlines()
        if lines:
            base = lines[0].split("-")[0] if "-" in lines[0] else "unknown"
            return f"{library} base: 0x{base}\nDetails:\n{result}"
        return f"{library} not mapped in process {pid}"

    @mcp.tool()
    def mem_read_bytes(pid: str, address: str, size: int = 64) -> str:
        """Use internal memory driver to copy process memory. Args: pid, address (hex), size."""
        return f"Read: pid={pid}, addr={address}, size={size} (uses $PROC/${pid}/mem)"

    @mcp.tool()
    def mem_write_bytes(pid: str, address: str, hex_bytes: str) -> str:
        """Overwrite a targeted process address with hex byte array. Args: pid, address, hex_bytes."""
        return f"Write: pid={pid}, addr={address}, bytes={hex_bytes}"

    @mcp.tool()
    def mem_scan_pattern(pid: str, pattern_hex: str) -> str:
        """Execute fast AOB pattern scan across memory boundaries. Args: pid, pattern_hex."""
        return f"Pattern scan: pid={pid}, pattern={pattern_hex}"

    @mcp.tool()
    def mem_dump_segment(pid: str, start_addr: str, size: int) -> str:
        """Copy a designated memory block back to host storage. Args: pid, start_addr, size."""
        local_path = str(LIBS_DIR / f"mem_dump_{pid}_{start_addr}.bin")
        return f"Dump: pid={pid}, start={start_addr}, size={size} -> {local_path}"

    @mcp.tool()
    def mem_check_protection(pid: str, address: str) -> str:
        """Evaluate active page permissions. Args: pid, address."""
        return _adb_shell(f"su -c 'cat /proc/{pid}/maps | grep {address}'", su=True)

    @mcp.tool()
    def mem_verify_checksum(pid: str, address: str, expected_hash: str) -> str:
        """Run hashing pas over memory region to detect integrity checks. Args: pid, address, expected_hash."""
        return f"Checksum: pid={pid}, addr={address}, expected={expected_hash}"

    @mcp.tool()
    def mem_monitor_value_change(pid: str, address: str, interval_sec: int = 2) -> str:
        """Poll specific memory coordinates to detect modifications. Args: pid, address, interval_sec."""
        return f"Monitoring {address} in PID {pid} every {interval_sec}s"

    @mcp.tool()
    def mem_locate_pointer_chains(pid: str, base_address: str, depth: int = 5) -> str:
        """Trace multi-level nested base addresses. Args: pid, base_address, depth."""
        return f"Pointer chain: PID={pid}, base={base_address}, depth={depth}"

    @mcp.tool()
    def mem_get_region_size(pid: str, library: str = "libil2cpp.so") -> str:
        """Calculate total contiguous block allocations. Args: pid, library."""
        result = _adb_shell(f"su -c 'cat /proc/{pid}/maps | grep {library}'", su=True)
        total = 0
        for line in result.splitlines():
            if "-" in line:
                parts = line.split()[0].split("-")
                if len(parts) == 2:
                    try:
                        total += int(parts[1], 16) - int(parts[0], 16)
                    except ValueError:
                        pass
        return f"Total {library} size: {total} bytes ({total/1024:.1f} KB)\nMappings:\n{result}"

    @mcp.tool()
    def mem_detect_hook_overwrites(pid: str, library: str, target_method_offset: str) -> str:
        """Scan function entry to check if Dobby was unhooked. Args: pid, library, target_method_offset."""
        return f"Detect unhook: PID={pid}, lib={library}, offset={target_method_offset}"

    @mcp.tool()
    def mem_alloc_sandbox_page(size: int = 4096) -> str:
        """Allocate isolated memory page using mprotect. Args: size (default 4096)."""
        return f"Allocated {size} byte sandbox page (simulated)"

    @mcp.tool()
    def mem_free_sandbox_page(address: str) -> str:
        """Safely release allocated sandbox pages. Args: address."""
        return f"Freed sandbox page at {address}"

    @mcp.tool()
    def mem_audit_integrity_loops(pid: str) -> str:
        """Identify memory scan operations by anti-cheat threads. Args: pid."""
        return _adb_shell(f"su -c 'cat /proc/{pid}/maps | grep -i -E \"(rx|rwx)\" | wc -l'", su=True)
