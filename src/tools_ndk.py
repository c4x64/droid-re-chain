"""15 Compilation & Toolchain Control tools."""
import os
import subprocess
import json
from pathlib import Path
from src.shared import (
    _check_ndk_toolchain, _parse_ndk_errors,
    NDK_CLANG, NDK_STRIP, NDK_SYSROOT, NDK_CMAKE_TOOLCHAIN,
    NDK_TOOLCHAIN, NDK_BASE,
    PROJECT_ROOT, LIBS_DIR, SRC_DIR, INCLUDE_DIR,
)

def register(mcp):

    @mcp.tool()
    def ndk_build_clean() -> str:
        """Erase old libs/ output structures. Returns count of deleted files."""
        count = 0
        for f in LIBS_DIR.glob("*"):
            try:
                f.unlink()
                count += 1
            except OSError:
                pass
        obj = PROJECT_ROOT / "obj"
        if obj.exists():
            for f in obj.rglob("*"):
                try:
                    f.unlink()
                    count += 1
                except OSError:
                    pass
            try:
                obj.rmdir()
            except OSError:
                pass
        return f"cleaned {count} artifact(s)"

    @mcp.tool()
    def ndk_build_module(source: str = "main.cpp", output: str = "libmod.so") -> str:
        """Compile an NDK shared library using the arm64 toolchain. Returns JSON with errors/warnings.
        Args: source (in src/), output (in libs/)."""
        tc = _check_ndk_toolchain()
        if tc:
            return tc
        src_path = SRC_DIR / source
        if not src_path.exists():
            return f"ERROR: source not found at {src_path}"
        out_path = LIBS_DIR / output
        cmd = [
            NDK_CLANG, "-target", "aarch64-linux-android21",
            "--sysroot", NDK_SYSROOT, "-I", str(INCLUDE_DIR),
            "-fPIC", "-shared", "-O2", "-fvisibility=hidden",
            "-Wall", "-Wextra", "-o", str(out_path), str(src_path),
            "-llog", "-ldl", "-Wl,--gc-sections", "-Wl,--hash-style=sysv",
        ]
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        except subprocess.TimeoutExpired:
            return json.dumps({"status": "timeout", "detail": "compilation exceeded 120s"})
        except FileNotFoundError:
            return json.dumps({"status": "fatal", "detail": f"compiler not found: {NDK_CLANG}"})
        except Exception as e:
            return json.dumps({"status": "error", "detail": str(e)})
        if r.returncode != 0:
            diag = json.loads(_parse_ndk_errors(r.stderr, r.stdout))
            diag["compiler_exit_code"] = r.returncode
            return json.dumps(diag, indent=2)
        size = out_path.stat().st_size
        stripped_path = LIBS_DIR / output.replace(".so", "_stripped.so")
        s = subprocess.run([NDK_STRIP, "-o", str(stripped_path), str(out_path)], capture_output=True, text=True, timeout=30)
        strip_info = f", stripped: {stripped_path.stat().st_size} bytes" if s.returncode == 0 else f", strip skipped: {s.stderr.strip()}"
        diag = json.loads(_parse_ndk_errors(r.stderr, r.stdout))
        diag.update({"status": "success", "output": str(out_path), "size_bytes": size, "strip": strip_info})
        return json.dumps(diag, indent=2)

    @mcp.tool()
    def ndk_build_debug(source: str = "main.cpp", output: str = "libmod_debug.so") -> str:
        """Compile with full debugging flags (-g -O0).
        Args: source (in src/), output (in libs/)."""
        tc = _check_ndk_toolchain()
        if tc:
            return tc
        src_path = SRC_DIR / source
        if not src_path.exists():
            return f"ERROR: source not found at {src_path}"
        out_path = LIBS_DIR / output
        cmd = [
            NDK_CLANG, "-target", "aarch64-linux-android21",
            "--sysroot", NDK_SYSROOT, "-I", str(INCLUDE_DIR),
            "-fPIC", "-shared", "-g", "-O0", "-fvisibility=hidden",
            "-Wall", "-Wextra", "-o", str(out_path), str(src_path),
            "-llog", "-ldl",
        ]
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        except subprocess.TimeoutExpired:
            return "TIMEOUT: debug compilation exceeded 120s"
        except Exception as e:
            return f"ERROR: {e}"
        if r.returncode != 0:
            return f"BUILD FAILED (exit {r.returncode}):\n{r.stderr.strip()}"
        return f"debug build: {out_path} ({out_path.stat().st_size} bytes)"

    @mcp.tool()
    def ndk_build_release(source: str = "main.cpp", output: str = "libmod.so") -> str:
        """Build optimized release payload with stripped symbol trees.
        Args: source (in src/), output (in libs/)."""
        result = ndk_build_module(source=source, output=output)
        return f"release: {result}"

    @mcp.tool()
    def cmake_generate_config(build_dir: str = "build/cmake") -> str:
        """Create a cross-compilation workspace via CMakeLists.txt.
        Args: build_dir path."""
        build_path = Path(build_dir)
        if not build_path.is_absolute():
            build_path = PROJECT_ROOT / build_path
        build_path.mkdir(parents=True, exist_ok=True)
        if not os.path.isfile(NDK_CMAKE_TOOLCHAIN):
            return f"ERROR: NDK CMake toolchain not found at {NDK_CMAKE_TOOLCHAIN}"
        cmake_lists = PROJECT_ROOT / "CMakeLists.txt"
        if not cmake_lists.exists():
            cmake_lists.write_text(
                "cmake_minimum_required(VERSION 3.18)\n"
                "project(droid-re-chain C CXX)\n"
                "set(CMAKE_CXX_STANDARD 17)\n"
                "add_library(mod SHARED src/main.cpp)\n"
                "target_include_directories(mod PRIVATE include)\n"
                "target_link_libraries(mod log dl)\n"
            )
            return f"created CMakeLists.txt at {cmake_lists}. Re-run to configure."
        cmd = ["cmake", "-DCMAKE_TOOLCHAIN_FILE=" + NDK_CMAKE_TOOLCHAIN,
               "-DANDROID_ABI=arm64-v8a", "-DANDROID_PLATFORM=android-21",
               "-DCMAKE_BUILD_TYPE=Release", "-S", str(PROJECT_ROOT), "-B", str(build_path)]
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        except Exception as e:
            return f"ERROR: {e}"
        if r.returncode != 0:
            return f"CMAKE CONFIG FAILED (exit {r.returncode}):\n{r.stderr.strip()[:2000]}"
        return f"cmake configured: {build_path}\n{r.stdout.strip()[:1000]}"

    @mcp.tool()
    def cmake_compile_target(build_dir: str = "build/cmake", target: str = "mod") -> str:
        """Drive a targeted CMake compilation cycle for arm64-v8a.
        Args: build_dir, target name (default mod)."""
        build_path = Path(build_dir)
        if not build_path.is_absolute():
            build_path = PROJECT_ROOT / build_path
        if not (build_path / "CMakeCache.txt").exists():
            return f"ERROR: build not configured at {build_path}. Run cmake_generate_config first."
        cmd = ["cmake", "--build", str(build_path), "--target", target]
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        except Exception as e:
            return f"ERROR: {e}"
        parsed = json.loads(_parse_ndk_errors(r.stderr, r.stdout))
        parsed["command"] = " ".join(cmd)
        if r.returncode == 0:
            lib_output = LIBS_DIR / "libmod.so"
            if lib_output.exists():
                parsed["output_size"] = lib_output.stat().st_size
            parsed["status"] = "success"
        else:
            parsed["status"] = "failed"
            parsed["compiler_exit_code"] = r.returncode
        return json.dumps(parsed, indent=2)

    @mcp.tool()
    def verify_elf_header(binary_path: str = "") -> str:
        """Validate whether a compiled .so matches ARM64 machine architecture.
        Args: binary_path (default libs/libmod_stripped.so)."""
        if not binary_path:
            candidates = [LIBS_DIR / "libmod_stripped.so", LIBS_DIR / "libmod.so"]
            for c in candidates:
                if c.exists():
                    binary_path = str(c)
                    break
            if not binary_path:
                return "ERROR: no binary found in libs/. Build first."
        if not os.path.isfile(binary_path):
            return f"ERROR: file not found: {binary_path}"
        try:
            with open(binary_path, "rb") as f:
                header = f.read(64)
        except IOError as e:
            return f"ERROR: {e}"
        if len(header) < 16 or header[:4] != b"\x7fELF":
            return f"NOT AN ELF or too small: {binary_path}"
        cls = "64-bit" if header[4] == 2 else "32-bit" if header[4] == 1 else f"unknown ({header[4]})"
        endian = "little" if header[5] == 1 else "big" if header[5] == 2 else f"unknown ({header[5]})"
        machine = header[18] | (header[19] << 8)
        m = {0: "None", 3: "i386", 40: "ARM", 62: "x86-64", 183: "AArch64", 243: "RISC-V"}
        ms = m.get(machine, f"unknown ({hex(machine)})")
        arm64 = (machine == 183 and cls == "64-bit")
        return f"File: {binary_path} ({os.path.getsize(binary_path)} bytes)\nClass: {cls}\nEndian: {endian}\nMachine: {ms}\nARM64: {'YES' if arm64 else 'NO'}"

    @mcp.tool()
    def strip_symbols(binary_path: str = "") -> str:
        """Explicitly invoke llvm-strip to verify obfuscation alignment.
        Args: binary_path (default libs/libmod.so)."""
        if not binary_path:
            candidates = [LIBS_DIR / "libmod.so", LIBS_DIR / "libmod_stripped.so"]
            for c in candidates:
                if c.exists():
                    binary_path = str(c)
                    break
        if not binary_path or not os.path.isfile(binary_path):
            return "ERROR: binary not found"
        out = binary_path.replace(".so", "_stripped.so")
        s = subprocess.run([NDK_STRIP, "-o", out, binary_path], capture_output=True, text=True, timeout=30)
        if s.returncode == 0:
            return f"stripped: {binary_path} -> {out} ({os.path.getsize(out)} bytes)"
        return f"strip failed: {s.stderr.strip()}"

    @mcp.tool()
    def parse_compiler_errors(build_log: str) -> str:
        """Scan stdout logs to format compilation failures into clean JSON structure.
        Args: build_log raw text."""
        return _parse_ndk_errors(build_log, "")

    @mcp.tool()
    def patch_makefile(optimization_level: str = "-O2") -> str:
        """Dynamically adjust optimization fields inside active build scripts.
        Args: optimization_level (default -O2)."""
        android_mk = PROJECT_ROOT / "Android.mk"
        if not android_mk.exists():
            return "ERROR: Android.mk not found"
        content = android_mk.read_text()
        import re
        new_content = re.sub(r'-O[0-9]', optimization_level, content)
        if new_content != content:
            android_mk.write_text(new_content)
            return f"patched Android.mk: -O* -> {optimization_level}"
        return "no changes needed"

    @mcp.tool()
    def check_include_paths() -> str:
        """Resolve include paths to ensure dobby.h maps correctly."""
        inc = INCLUDE_DIR
        found = [str(f.relative_to(PROJECT_ROOT)) for f in inc.rglob("*") if f.suffix in (".h", ".hpp")]
        if not found:
            return f"No headers found in {inc}"
        return f"{len(found)} headers found:\n" + "\n".join(found)

    @mcp.tool()
    def set_compiler_flags(extra_flags: str = "-fPIE -fstack-protector-strong") -> str:
        """Programmatically inject security parameter mitigations into Android.mk.
        Args: extra_flags to add."""
        android_mk = PROJECT_ROOT / "Android.mk"
        if not android_mk.exists():
            return "ERROR: Android.mk not found"
        content = android_mk.read_text()
        if extra_flags in content:
            return f"flags already present: {extra_flags}"
        if "LOCAL_CFLAGS" in content:
            content = content.replace("LOCAL_CFLAGS :=", f"LOCAL_CFLAGS := {extra_flags} ")
        android_mk.write_text(content)
        return f"injected: {extra_flags}"

    @mcp.tool()
    def get_ndk_version() -> str:
        """Confirm local path alignment with the active Android NDK package."""
        if os.path.isdir(NDK_BASE):
            readme = os.path.join(NDK_BASE, "README.md")
            if os.path.isfile(readme):
                with open(readme) as f:
                    for line in f:
                        if "r25" in line.lower() or "NDK" in line:
                            return f"NDK: {NDK_BASE}\nInfo: {line.strip()[:100]}"
            return f"NDK found at: {NDK_BASE}\nClang: {NDK_CLANG}"
        return f"NDK not found at {NDK_BASE}"

    @mcp.tool()
    def ndk_build_ccache(source: str = "main.cpp", output: str = "libmod_cc.so") -> str:
        """Build with CCache acceleration. Args: source (in src/), output (in libs/)."""
        import shutil
        ccache_bin = shutil.which("ccache")
        if not ccache_bin:
            return "ccache not installed. Install it: brew install ccache / apt install ccache"
        tc = _check_ndk_toolchain()
        if tc: return tc
        src_path = SRC_DIR / source
        if not src_path.exists(): return f"ERROR: source not found at {src_path}"
        out_path = LIBS_DIR / output
        cmd = [ccache_bin, NDK_CLANG, "-target", "aarch64-linux-android21",
               "--sysroot", NDK_SYSROOT, "-I", str(INCLUDE_DIR),
               "-fPIC", "-shared", "-O2", "-fvisibility=hidden",
               "-flto=thin", "-Wall", "-Wextra",
               "-o", str(out_path), str(src_path), "-llog", "-ldl"]
        env = os.environ.copy()
        env["CCACHE_SLOPPINESS"] = "time_macros,pch_defines"
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=120, env=env)
        except subprocess.TimeoutExpired:
            return json.dumps({"status": "timeout"})
        if r.returncode != 0: return _parse_ndk_errors(r.stderr, r.stdout)
        return json.dumps({"status": "success", "output": str(out_path),
                           "size": out_path.stat().st_size, "ccache": True})

    @mcp.tool()
    def verify_elf_symbols(binary_path: str = "") -> str:
        """Run nm on built .so to count exported vs undefined symbols. Args: binary_path."""
        if not binary_path:
            for c in [LIBS_DIR / "libmod_stripped.so", LIBS_DIR / "libmod.so"]:
                if c.exists(): binary_path = str(c); break
        if not binary_path: return "ERROR: no binary found"
        try:
            r = subprocess.run(["nm", "-D", binary_path], capture_output=True, text=True, timeout=15)
            if r.returncode != 0:
                return f"nm failed: {r.stderr.strip()[:300]}"
            lines = r.stdout.strip().splitlines()
            total = len(lines)
            undefined = sum(1 for l in lines if " U " in l)
            defined = total - undefined
            exports = [l.strip() for l in lines if " T " in l][:20]
            return json.dumps({"total_symbols": total, "defined": defined,
                               "undefined": undefined,
                               "exported_functions": exports[:10],
                               "binary": binary_path}, indent=2)
        except FileNotFoundError:
            return "nm not found. Install binutils."

    @mcp.tool()
    def audit_link_dependencies() -> str:
        """Validate whether libmod.so correctly links against required libraries."""
        libmod = LIBS_DIR / "libmod.so"
        if not libmod.exists():
            return "ERROR: libmod.so not found. Build first."
        r = subprocess.run(["readelf", "-d", str(libmod)], capture_output=True, text=True, timeout=15)
        if r.returncode == 0:
            needed = [l for l in r.stdout.splitlines() if "NEEDED" in l]
            return f"Dynamic dependencies:\n" + "\n".join(needed) if needed else r.stdout.strip()[:1000]
        try:
            r2 = subprocess.run([NDK_TOOLCHAIN + "/bin/llvm-readelf", "-d", str(libmod)], capture_output=True, text=True, timeout=15)
            return r2.stdout.strip()[:1000] if r2.stdout.strip() else r2.stderr.strip()[:500]
        except Exception as e:
            return f"readelf not available: {e}"