"""Example: Build NDK module, push to device, and patch a target offset."""
import sys
import time
import subprocess
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.shared import NDK_CLANG, NDK_STRIP, LIBS_DIR, _adb_run, _adb_shell, ADB_BINARY


def main():
    if not NDK_CLANG:
        print("Set ANDROID_NDK_HOME first")
        sys.exit(1)

    # 1. Build
    src_main = Path(__file__).resolve().parent.parent / "src" / "main.cpp"
    lib_out = LIBS_DIR / "libmod.so"
    lib_stripped = LIBS_DIR / "libmod_stripped.so"

    cmd = [NDK_CLANG, "-shared", "-fPIC", "-O2", "-Wall", "-Werror",
           "-I", str(src_main.parent.parent / "include"),
           str(src_main), "-o", str(lib_out), "-llog", "-ldl"]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if r.returncode != 0:
        print("Build failed:", r.stderr)
        return

    # 2. Strip
    subprocess.run([NDK_STRIP, "-o", str(lib_stripped), str(lib_out)], timeout=10)
    print(f"Built: {lib_stripped} ({lib_stripped.stat().st_size} bytes)")

    # 3. Push
    _adb_run([ADB_BINARY, "push", str(lib_stripped), "/data/local/tmp/libmod.so"])
    print("Pushed to device")

    # 4. Patch example (dry run)
    print("Offset 0x1234 ready for patching via hook tools")


if __name__ == "__main__":
    main()