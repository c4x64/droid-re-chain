#!/usr/bin/env python3
"""NDK build wrapper with ccache, LTO, sanitizers, and ELF verification."""
import os
import sys
import subprocess
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.shared import NDK_CLANG, NDK_CLANGXX, NDK_STRIP, LIBS_DIR, SRC_DIR, INCLUDE_DIR, _parse_ndk_errors

CCACHE = os.environ.get("CCACHE", "")
SANITIZE = os.environ.get("SANITIZE", "")  
LTO = os.environ.get("LTO", "1")
OPT_LEVEL = os.environ.get("OPT", "-O2")

def build_module(target: str = "libmod.so", source: str = "src/main.cpp",
                 extra_flags: list = None, strip: bool = True) -> dict:
    result = {"target": target, "source": source, "status": "failed", "errors": [], "warnings": [], "size": 0}
    clang = NDK_CLANG
    if not clang or not os.path.isfile(clang):
        result["errors"].append(f"NDK clang not found: {clang}. Set ANDROID_NDK_HOME")
        return result
    src_path = Path(SRC_DIR / source) if not os.path.isabs(source) else Path(source)
    if not src_path.exists():
        result["errors"].append(f"Source not found: {src_path}")
        return result
    out_path = LIBS_DIR / target
    cmd = []
    if CCACHE:
        ccache_bin = shutil.which(CCACHE) if not os.path.isabs(CCACHE) else CCACHE
        if ccache_bin:
            cmd.append(ccache_bin)
    cmd += [clang, "-shared", "-fPIC", OPT_LEVEL, "-Wall", "-Werror"]
    if LTO == "1":
        cmd += ["-flto=thin"]
    if SANITIZE:
        cmd += [f"-fsanitize={SANITIZE}", "-fno-sanitize-recover=all"]
    cmd += ["-I", str(INCLUDE_DIR), str(src_path), "-o", str(out_path)]
    cmd += ["-llog", "-ldl"]
    if extra_flags:
        cmd += extra_flags
    env = os.environ.copy()
    if CCACHE:
        env["CCACHE_SLOPPINESS"] = "time_macros,pch_defines"
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=60, env=env)
    except subprocess.TimeoutExpired:
        result["errors"].append("Build timed out after 60s")
        return result
    if r.returncode != 0:
        parsed = json.loads(_parse_ndk_errors(r.stderr, r.stdout))
        result.update(parsed)
        result["command"] = " ".join(str(c) for c in cmd)
        return result
    if strip and NDK_STRIP and os.path.isfile(NDK_STRIP):
        stripped = out_path.with_name(out_path.stem + "_stripped.so")
        subprocess.run([NDK_STRIP, "-o", str(stripped), str(out_path)], timeout=10)
        result["stripped_size"] = stripped.stat().st_size
    result["size"] = out_path.stat().st_size
    result["status"] = "success"
    result["command"] = " ".join(str(c) for c in cmd)
    return result

def verify_elf(so_path: str) -> dict:
    """Run readelf and nm on built .so for quality verification."""
    result = {"path": so_path, "valid": False, "arch": "", "entry": "", "symbols": 0, "undefined": 0, "warnings": []}
    if not os.path.isfile(so_path):
        result["warnings"].append(f"File not found: {so_path}")
        return result
    try:
        r = subprocess.run(["file", so_path], capture_output=True, text=True, timeout=10)
        result["file_type"] = r.stdout.strip()
    except Exception as e:
        result["warnings"].append(f"file command: {e}")
    try:
        r = subprocess.run(["readelf", "-h", so_path], capture_output=True, text=True, timeout=10)
        for line in r.stdout.splitlines():
            if "Machine:" in line:
                result["arch"] = line.split(":")[1].strip()
            if "Entry point" in line:
                result["entry"] = line.split(":")[1].strip()
        result["valid"] = bool(result["arch"])
    except Exception as e:
        result["warnings"].append(f"readelf: {e}")
    try:
        r = subprocess.run(["nm", "-D", so_path], capture_output=True, text=True, timeout=10)
        lines = r.stdout.strip().splitlines()
        result["symbols"] = len(lines)
        result["undefined"] = sum(1 for l in lines if " U " in l)
    except Exception as e:
        result["warnings"].append(f"nm: {e}")
    return result

if __name__ == "__main__":
    import shutil
    import json
    tgt = sys.argv[1] if len(sys.argv) > 1 else "libmod.so"
    src = sys.argv[2] if len(sys.argv) > 2 else "src/main.cpp"
    print(f"Building {tgt} from {src}...")
    r = build_module(tgt, src)
    print(json.dumps(r, indent=2))
    if r["status"] == "success" and r.get("stripped_size"):
        v = verify_elf(str(LIBS_DIR / target_name := tgt))
        print("\nELF Verify:", json.dumps(v, indent=2))