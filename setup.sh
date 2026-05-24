#!/usr/bin/env bash
set -euo pipefail

echo "=== droid-re-chain Setup (Unix) ==="

# 1. Python deps
pip install -r requirements.txt

# 2. Verify ADB
if ! command -v adb &>/dev/null; then
    echo "WARNING: adb not on PATH. Install Android platform-tools."
    echo "  macOS: brew install android-platform-tools"
    echo "  Linux: apt install adb  or  pacman -S android-tools"
fi

# 3. Verify NDK
if [ -z "${ANDROID_NDK_HOME:-}" ]; then
    echo "WARNING: ANDROID_NDK_HOME not set."
    echo "  Set it to your NDK r25+ path, e.g.:"
    echo "    export ANDROID_NDK_HOME=\$HOME/Android/Sdk/ndk/25.2.9519653"
fi

# 4. Create directories
mkdir -p libs logs patches frida_scripts apk_work

# 5. Verify all imports
echo "Verifying module imports..."
python3 -c "from src.server import mcp; print(f'OK: {len(mcp._tools)} tools registered')"

echo "=== Setup complete ==="
echo "Run: python3 -m src.server"