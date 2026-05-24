#!/usr/bin/env bash
# Portable launcher for droid-re-chain MCP server.
# Resolves project root regardless of where the script lives,
# so Cursor/Claude Code can invoke it from any working directory.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

# Inherit ANDROID_NDK_HOME from environment, or try common paths
if [ -z "${ANDROID_NDK_HOME:-}" ]; then
  for candidate in \
    /opt/homebrew/share/android-commandlinetools/ndk/25.2.9519653 \
    /usr/local/share/android-ndk \
    "$HOME/Android/Sdk/ndk/25.2.9519653" \
    "$HOME/android-ndk"; do
    if [ -d "$candidate" ]; then
      export ANDROID_NDK_HOME="$candidate"
      break
    fi
  done
fi

exec python3 -m src.server "$@"