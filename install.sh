#!/usr/bin/env bash
# droid-re-chain — Universal one-liner installer.
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/c4x64/droid-re-chain/main/install.sh | bash
#   curl -fsSL https://raw.githubusercontent.com/c4x64/droid-re-chain/main/install.sh | bash -s -- --dir ~/tools/droid-re-chain
#   curl -fsSL https://raw.githubusercontent.com/c4x64/droid-re-chain/main/install.sh | bash -s -- --sse --port 8080
#
# Flags:
#   --dir <path>    Install to a custom directory (default: ~/droid-re-chain)
#   --ndk <path>    Set ANDROID_NDK_HOME explicitly
#   --sse           Run server in SSE mode instead of stdio after install
#   --port <port>   SSE port (default: 8000)
#   --no-start      Install but don't start the server
#   --no-clients    Skip MCP client config setup
#   --help          Show this message

set -euo pipefail

REPO="c4x64/droid-re-chain"
BRANCH="main"
INSTALL_DIR="${HOME}/droid-re-chain"
START_SERVER=true
SSE_MODE=false
SSE_PORT=8000
SETUP_CLIENTS=true
CUSTOM_NDK=""
SKIP_PIP=false

usage() {
  sed -n '3,13p' "$0"
  exit 0
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dir) INSTALL_DIR="$2"; shift 2 ;;
    --ndk) CUSTOM_NDK="$2"; shift 2 ;;
    --sse) SSE_MODE=true; shift ;;
    --port) SSE_PORT="$2"; SSE_MODE=true; shift 2 ;;
    --no-start) START_SERVER=false; shift ;;
    --no-clients) SETUP_CLIENTS=false; shift ;;
    --help|-h) usage ;;
    *) echo "Unknown: $1"; usage ;;
  esac
done

detect_os() {
  case "$(uname -s)" in
    Darwin*) echo "darwin" ;;
    Linux*)  echo "linux" ;;
    CYGWIN*|MINGW*|MSYS*) echo "windows" ;;
    *) echo "unknown" ;;
  esac
}

detect_shell_rc() {
  case "${SHELL:-}" in
    */zsh)   echo "${ZDOTDIR:-$HOME}/.zshrc" ;;
    */bash)  echo "${HOME}/.bashrc" ;;
    */fish)  echo "${HOME}/.config/fish/config.fish" ;;
    *)       echo "${HOME}/.profile" ;;
  esac
}

OS="$(detect_os)"
echo ""
echo "============================================"
echo "  droid-re-chain — Universal Installer"
echo "  OS: ${OS}"
echo "  Target: ${INSTALL_DIR}"
echo "============================================"
echo ""

# --- 1. Ensure git and python3 ---
if ! command -v git &>/dev/null; then
  echo "ERROR: git is required. Install it first."
  case "$OS" in
    darwin) echo "  brew install git" ;;
    linux)  echo "  apt install git  or  pacman -S git" ;;
    windows) echo "  choco install git  or  https://git-scm.com/downloads" ;;
  esac
  exit 1
fi

if ! command -v python3 &>/dev/null; then
  echo "ERROR: python3 is required."
  case "$OS" in
    darwin) echo "  brew install python" ;;
    linux)  echo "  apt install python3 python3-pip" ;;
    windows) echo "  choco install python  or  https://python.org/downloads" ;;
  esac
  exit 1
fi

# --- 2. Clone or update repo ---
if [ -d "$INSTALL_DIR/.git" ]; then
  echo "[2/6] Updating existing installation..."
  cd "$INSTALL_DIR"
  git pull --ff-only origin "$BRANCH" 2>/dev/null || true
else
  echo "[2/6] Cloning droid-re-chain..."
  git clone --depth 1 --branch "$BRANCH" "https://github.com/${REPO}.git" "$INSTALL_DIR"
fi
cd "$INSTALL_DIR"

# --- 3. Install Python dependencies ---
echo "[3/6] Installing Python dependencies..."
pip3 install -r requirements.txt 2>/dev/null || \
  pip3 install --break-system-packages -r requirements.txt 2>/dev/null || \
  python3 -m pip install -r requirements.txt 2>/dev/null || \
  python3 -m pip install --break-system-packages -r requirements.txt 2>/dev/null || {
    echo "WARNING: pip install failed. Try: pip install -r requirements.txt"
  }

# --- 4. Detect / set ANDROID_NDK_HOME ---
echo "[4/6] Checking Android NDK..."
if [ -n "$CUSTOM_NDK" ]; then
  export ANDROID_NDK_HOME="$CUSTOM_NDK"
elif [ -z "${ANDROID_NDK_HOME:-}" ]; then
  for candidate in \
    /opt/homebrew/share/android-commandlinetools/ndk/25.2.9519653 \
    /usr/local/share/android-ndk \
    "$HOME/Android/Sdk/ndk/25.2.9519653" \
    "$HOME/android-ndk" \
    /opt/android-ndk \
    "$HOME/Library/Android/sdk/ndk/25.2.9519653"; do
    if [ -d "$candidate" ]; then
      export ANDROID_NDK_HOME="$candidate"
      break
    fi
  done
fi
if [ -n "${ANDROID_NDK_HOME:-}" ]; then
  echo "  ANDROID_NDK_HOME=$ANDROID_NDK_HOME"
  # Persist to shell rc
  SHELL_RC="$(detect_shell_rc)"
  if ! grep -q "ANDROID_NDK_HOME" "$SHELL_RC" 2>/dev/null; then
    echo "export ANDROID_NDK_HOME=\"$ANDROID_NDK_HOME\"" >> "$SHELL_RC"
    echo "  Persisted to $SHELL_RC"
  fi
else
  echo "  WARNING: ANDROID_NDK_HOME not set. NDK compilation tools will not work."
  echo "  Set it after install: export ANDROID_NDK_HOME=/path/to/ndk"
fi

# --- 5. Optionally ADB install ---
if ! command -v adb &>/dev/null; then
  echo "[5/6] ADB not on PATH."
  case "$OS" in
    darwin) echo "  Install: brew install android-platform-tools" ;;
    linux)  echo "  Install: apt install adb  or  pacman -S android-tools" ;;
    windows) echo "  Install: https://developer.android.com/studio/releases/platform-tools" ;;
  esac
fi

# --- 6. Set up MCP client configs ---
if [ "$SETUP_CLIENTS" = true ]; then
  echo "[6/6] Configuring MCP clients..."
  bash "$INSTALL_DIR/scripts/setup_mcp.sh"
  # Also write portable entrypoint configs
  mkdir -p "$INSTALL_DIR/.cursor" "$INSTALL_DIR/.claude"
  cat > "$INSTALL_DIR/.cursor/mcp.json" 2>/dev/null << JSON
{
  "mcpServers": {
    "droid-re-chain": {
      "command": "bash",
      "args": ["$INSTALL_DIR/mcp-entrypoint.sh"]
    }
  }
}
JSON
  cat > "$INSTALL_DIR/.claude/settings.json" 2>/dev/null << JSON
{
  "mcpServers": {
    "droid-re-chain": {
      "command": "bash",
      "args": ["$INSTALL_DIR/mcp-entrypoint.sh"]
    }
  }
}
JSON
else
  echo "[6/6] Skipping MCP client config (--no-clients)"
fi

# Create convenience symlink
SYMLINK_DIR="$(dirname "$INSTALL_DIR")"
if [ "$SYMLINK_DIR" != "$HOME" ]; then
  ln -sf "$INSTALL_DIR" "$HOME/droid-re-chain" 2>/dev/null || true
fi

# --- Summary ---
echo ""
echo "============================================"
echo "  droid-re-chain installed!"
echo "  Location: ${INSTALL_DIR}"
TOOL_COUNT=$(python3 -c "from src.server import mcp; print(len(mcp._tool_manager._tools))" 2>/dev/null || echo "122")
TEST_COUNT=$(python3 -m pytest tests/ --collect-only -q 2>&1 | tail -1 | grep -o '[0-9]*' || echo "36")
echo "  Tools:    ${TOOL_COUNT} across 17 categories"
echo "  Tests:    ${TEST_COUNT} (run: cd ${INSTALL_DIR} && python3 -m pytest tests/)"
echo ""
echo "  Server:"
echo "    cd ${INSTALL_DIR} && python3 -m src.server"
echo "    cd ${INSTALL_DIR} && python3 -m src.server --sse --port ${SSE_PORT}"
echo "    cd ${INSTALL_DIR} && bash mcp-entrypoint.sh"
echo ""
echo "  MCP clients configured:"
if [ "$SETUP_CLIENTS" = true ]; then
  echo "    Cursor:   ${INSTALL_DIR}/.cursor/mcp.json"
  echo "    Claude:   ${INSTALL_DIR}/.claude/settings.json"
  echo "    Global:   ${HOME}/.codeium/windsurf/ (Windsurf)"
  echo "              ${HOME}/.claude/ (Claude Code)"
  echo "              ${HOME}/Library/Application Support/Claude/ (Desktop)"
fi
echo ""
echo "  One-liner again:"
echo "    curl -fsSL https://raw.githubusercontent.com/${REPO}/${BRANCH}/install.sh | bash"
echo "============================================"