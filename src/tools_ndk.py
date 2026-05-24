import subprocess
import os
import sys
from pathlib import Path

NDK_BASE = os.environ.get(
    "ANDROID_NDK_HOME",
    "/opt/homebrew/share/android-commandlinetools/ndk/25.2.9519653",
)
TOOLCHAIN = f"{NDK_BASE}/toolchains/llvm/prebuilt/darwin-x86_64"
CLANG = f"{TOOLCHAIN}/bin/aarch64-linux-android21-clang"
CLANGXX = f"{TOOLCHAIN}/bin/aarch64-linux-android21-clang++"
STRIP = f"{TOOLCHAIN}/bin/llvm-strip"
SYSROOT = f"{TOOLCHAIN}/sysroot"

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LIBS_DIR = PROJECT_ROOT / "libs"
SRC_DIR = PROJECT_ROOT / "src"
INCLUDE_DIR = PROJECT_ROOT / "include"


class NDKError(Exception):
    pass


def _check_toolchain() -> None:
    if not os.path.isfile(CLANG):
        raise NDKError(f"clang not found at {CLANG}. Is NDK installed?")


def compile_shared(
    source: str = "main.cpp",
    output: str = "libmod.so",
    extra_flags: list[str] | None = None,
) -> str:
    _check_toolchain()
    LIBS_DIR.mkdir(exist_ok=True)

    src_path = SRC_DIR / source
    if not src_path.exists():
        raise NDKError(f"source not found: {src_path}")

    out_path = LIBS_DIR / output
    cmd = [
        CLANG,
        "-target", "aarch64-linux-android21",
        "--sysroot", SYSROOT,
        "-I", str(INCLUDE_DIR),
        "-fPIC", "-shared",
        "-O2", "-fvisibility=hidden",
        "-Wall", "-Wextra",
        "-o", str(out_path),
        str(src_path),
        "-llog", "-ldl",
        "-Wl,--gc-sections",
        "-Wl,--hash-style=sysv",
    ]
    if extra_flags:
        cmd.extend(extra_flags)

    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    except subprocess.TimeoutExpired:
        raise NDKError("compilation timed out (120s)")
    except FileNotFoundError:
        raise NDKError(f"compiler not found: {CLANG}. Check ANDROID_NDK_HOME.")

    log = ""
    if r.returncode != 0:
        log += f"COMPILE ERROR (exit {r.returncode}):\n"
        log += r.stderr.strip()
        if r.stdout.strip():
            log += "\n" + r.stdout.strip()
        raise NDKError(log)

    log += f"compiled: {out_path} ({out_path.stat().st_size} bytes)\n"

    stripped = LIBS_DIR / output.replace(".so", "_stripped.so")
    s = subprocess.run(
        [STRIP, "-o", str(stripped), str(out_path)],
        capture_output=True, text=True, timeout=30,
    )
    if s.returncode == 0:
        log += f"stripped: {stripped} ({stripped.stat().st_size} bytes)"
    else:
        log += f"strip skipped: {s.stderr.strip()}"

    return log


def get_libmod_path(stripped: bool = True) -> Path:
    name = "libmod_stripped.so" if stripped else "libmod.so"
    p = LIBS_DIR / name
    if stripped and not p.exists():
        p = LIBS_DIR / "libmod.so"
    return p


def clean() -> str:
    count = 0
    for f in LIBS_DIR.glob("*"):
        f.unlink()
        count += 1
    return f"cleaned {count} artifact(s)"


def register(mcp):
    """Register all NDK build tools with the FastMCP server."""

    @mcp.tool()
    def ndk_compile_project(project_path: str = "") -> str:
        """Compile src/main.cpp into a shared library using the NDK arm64 toolchain.

        Parses compiler diagnostics and returns structured success/failure output.

        Args:
            project_path: Ignored; always compiles from the project root.
        """
        ndk_dir = os.environ.get("ANDROID_NDK_HOME", NDK_BASE)
        if not os.path.isdir(ndk_dir):
            return (f"ERROR: NDK not found at {ndk_dir}. "
                    "Set ANDROID_NDK_HOME or install NDK 25.")

        try:
            result = compile_shared()
            return result
        except NDKError as e:
            return f"BUILD FAILED:\n{e}"

    @mcp.tool()
    def build_mod() -> str:
        """Alias for ndk_compile_project. Builds libmod.so from src/main.cpp."""
        try:
            return compile_shared()
        except NDKError as e:
            return f"BUILD FAILED:\n{e}"

    @mcp.tool()
    def clean_build() -> str:
        """Remove all compiled artifacts from libs/."""
        return clean()

    @mcp.tool()
    def deploy_mod(remote_path: str = "/data/local/tmp/libmod.so") -> str:
        """Build libmod.so then push it to the device with executable permissions.

        Combines build + push into one atomic step.

        Args:
            remote_path: Destination path on the Android device.
        """
        try:
            compile_shared()
        except NDKError as e:
            return f"BUILD FAILED:\n{e}"

        libmod = get_libmod_path()
        if not libmod.exists():
            return f"ERROR: {libmod} not found after build"

        from src.tools_adb import push, chmod
        try:
            out = push(str(libmod), remote_path)
            perm = chmod(remote_path, "755", su=True)
            return f"built: {libmod.stat().st_size} bytes\npushed: {out}\npermissions: {perm}"
        except Exception as e:
            return f"DEPLOY ERROR: {e}"