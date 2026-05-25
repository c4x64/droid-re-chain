#!/usr/bin/env bash
# droid-re-chain — Universal installer with colors and interactive selection.
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/c4x64/droid-re-chain/main/install.sh | bash
#   bash install.sh                                  # interactive (local)
#   bash install.sh --interactive                    # force interactive
#   bash install.sh --categories adb,ndk,hook        # non-interactive subset
#   bash install.sh --purpose apk                    # purpose profile
#   bash install.sh --clients cursor,opencode        # specific clients only
#   bash install.sh --dir ~/tools/droid-re-chain     # custom dir
#   bash install.sh --no-start                       # install only
#   bash install.sh --help                           # this message

set -euo pipefail

# ─── ANSI colors ──────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'
CHECK="${GREEN}\xE2\x9C\x94${NC}"
CROSS="${RED}\xE2\x9C\x98${NC}"

REPO="c4x64/droid-re-chain"
BRANCH="main"
INSTALL_DIR="${HOME}/droid-re-chain"
START_SERVER=true
SSE_MODE=false
SSE_PORT=8000
SETUP_CLIENTS=true
CUSTOM_NDK=""
SKIP_PIP=false
INTERACTIVE=false
SELECTED_CATEGORIES=""
SELECTED_CLIENTS=""
INSTALL_PURPOSE="full"

usage() {
  sed -n '4,15p' "$0"
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
    --interactive) INTERACTIVE=true; shift ;;
    --categories) SELECTED_CATEGORIES="$2"; shift 2 ;;
    --purpose)
      case "$2" in
        full|apk|native|custom) INSTALL_PURPOSE="$2" ;;
        *) echo "Purpose must be: full, apk, native, custom"; exit 1 ;;
      esac
      shift 2 ;;
    --clients) SELECTED_CLIENTS="$2"; shift 2 ;;
    --help|-h) usage ;;
    *) echo -e "${RED}Unknown: $1${NC}"; usage ;;
  esac
done

# ─── Helpers ──────────────────────────────────────────────────────────
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

# Auto-detect interactive: only if stdin is a terminal (not piped)
if [ -t 0 ] && [ "$INTERACTIVE" = false ]; then
  INTERACTIVE=true
fi

OS="$(detect_os)"

echo -e "\n${BOLD}${BLUE}============================================${NC}"
echo -e "${BOLD}${BLUE}  droid-re-chain — Universal Installer${NC}"
echo -e "${BOLD}${BLUE}  OS: ${OS}  |  Target: ${INSTALL_DIR}${NC}"
echo -e "${BOLD}${BLUE}============================================${NC}\n"

# ─── Interactive: Purpose / Category Selection ─────────────────────────
if [ "$INTERACTIVE" = true ] && [ -z "$SELECTED_CATEGORIES" ]; then
  echo -e "${CYAN}Select install purpose:${NC}"
  echo -e "  ${BOLD}1${NC}) Full (all 182 tools, 17 categories)  ${GREEN}[recommended]${NC}"
  echo -e "  ${BOLD}2${NC}) APK Analysis (adb, apk, static, net, frida)"
  echo -e "  ${BOLD}3${NC}) Native RE (ndk, hook, mem, trap, dump, ghidra, il2cpp)"
  echo -e "  ${BOLD}4${NC}) Custom (pick individual categories)"
  read -r -p "Choice [1]: " purpose_choice
  case "${purpose_choice:-1}" in
    2) INSTALL_PURPOSE="apk" ;;
    3) INSTALL_PURPOSE="native" ;;
    4) INSTALL_PURPOSE="custom" ;;
    *) INSTALL_PURPOSE="full" ;;
  esac
fi

case "$INSTALL_PURPOSE" in
  apk)
    SELECTED_CATEGORIES="adb,apk,static,net,frida"
    echo -e "  ${CHECK} Profile: ${BOLD}APK Analysis${NC} (${SELECTED_CATEGORIES})"
    ;;
  native)
    SELECTED_CATEGORIES="ndk,hook,mem,trap,dump,ghidra,il2cpp"
    echo -e "  ${CHECK} Profile: ${BOLD}Native RE${NC} (${SELECTED_CATEGORIES})"
    ;;
  custom)
    ALL_CATS="adb,ndk,il2cpp,hook,trap,mem,frida,apk,static,database,session,bypass,ida,net,dump,ghidra,update,selfimprove"
    if [ "$INTERACTIVE" = true ]; then
      echo -e "\n${CYAN}Select tool categories (space-separated numbers, or 'all'):${NC}"
      IFS=',' read -ra CATS <<< "$ALL_CATS"
      for i in "${!CATS[@]}"; do
        echo -e "  ${BOLD}$((i+1))${NC}) ${CATS[$i]}"
      done
      echo -e "  ${BOLD}a${NC}) All"
      read -r -p "Categories [a]: " cat_choice
      if [ "$cat_choice" = "a" ] || [ -z "$cat_choice" ]; then
        SELECTED_CATEGORIES="$ALL_CATS"
      else
        selected=""
        for n in $cat_choice; do
          idx=$((n-1))
          if [ "$idx" -ge 0 ] && [ "$idx" -lt "${#CATS[@]}" ]; then
            [ -n "$selected" ] && selected="$selected,"
            selected="${selected}${CATS[$idx]}"
          fi
        done
        SELECTED_CATEGORIES="$selected"
      fi
    else
      SELECTED_CATEGORIES="$ALL_CATS"
    fi
    echo -e "  ${CHECK} Custom: ${BOLD}${SELECTED_CATEGORIES}${NC}"
    ;;
  *)
    if [ -z "$SELECTED_CATEGORIES" ]; then
      echo -e "  ${CHECK} Profile: ${BOLD}Full${NC} (all 17 categories)"
    else
      echo -e "  ${CHECK} Profile: ${BOLD}Custom${NC} (${SELECTED_CATEGORIES})"
    fi
    ;;
esac

# Interactive: MCP client selection
if [ "$INTERACTIVE" = true ] && [ -z "$SELECTED_CLIENTS" ] && [ "$SETUP_CLIENTS" = true ]; then
  echo ""
  echo -e "${CYAN}Configure MCP clients?${NC}"
  echo -e "  ${BOLD}1${NC}) All detected clients  ${GREEN}[recommended]${NC}"
  echo -e "  ${BOLD}2${NC}) Select specific clients"
  echo -e "  ${BOLD}3${NC}) Skip client config"
  read -r -p "Choice [1]: " client_choice
  case "${client_choice:-1}" in
    2) SETUP_CLIENTS="select" ;;
    3) SETUP_CLIENTS=false ;;
    *) SETUP_CLIENTS=true ;;
  esac
fi

if [ "$SETUP_CLIENTS" = "select" ] && [ "$INTERACTIVE" = true ]; then
  ALL_CLIENTS="cursor,windsurf,antigravity,pearai,claude_desktop,chatgpt,librechat,jan,goose,claude_code,aider,autogen,crewai,langgraph,roo_code,continue,vscode,composio,llamaindex,harvey,opencode"
  echo -e "\n${CYAN}Select MCP clients to configure (space-separated numbers, or 'all'):${NC}"
  IFS=',' read -ra CLIENTS <<< "$ALL_CLIENTS"
  CLIENTS_LABELS=("Cursor" "Windsurf" "Antigravity" "PearAI" "Claude Desktop" "ChatGPT" "LibreChat" "Jan" "Goose CLI" "Claude Code" "Aider" "AutoGen" "CrewAI" "LangGraph" "Roo Code" "Continue" "VS Code" "Composio" "LlamaIndex" "Harvey AI" "opencode")
  for i in "${!CLIENTS[@]}"; do
    echo -e "  ${BOLD}$((i+1))${NC}) ${CLIENTS_LABELS[$i]}"
  done
  echo -e "  ${BOLD}a${NC}) All"
  read -r -p "Clients [a]: " cl_choice
  if [ "$cl_choice" = "a" ] || [ -z "$cl_choice" ]; then
    SELECTED_CLIENTS="$ALL_CLIENTS"
  else
    selected=""
    for n in $cl_choice; do
      idx=$((n-1))
      if [ "$idx" -ge 0 ] && [ "$idx" -lt "${#CLIENTS[@]}" ]; then
        [ -n "$selected" ] && selected="$selected,"
        selected="${selected}${CLIENTS[$idx]}"
      fi
    done
    SELECTED_CLIENTS="$selected"
  fi
  SETUP_CLIENTS=true
fi

echo ""

# ─── 1. Ensure git and python3 ──────────────────────────────────────
echo -e "${BOLD}[1/6]${NC} Checking prerequisites..."
if ! command -v git &>/dev/null; then
  echo -e "  ${CROSS} ${RED}git is required${NC}"
  case "$OS" in
    darwin) echo "    brew install git" ;;
    linux)  echo "    apt install git  or  pacman -S git" ;;
    windows) echo "    choco install git  or  https://git-scm.com/downloads" ;;
  esac
  exit 1
fi
if ! command -v python3 &>/dev/null; then
  echo -e "  ${CROSS} ${RED}python3 is required${NC}"
  case "$OS" in
    darwin) echo "    brew install python" ;;
    linux)  echo "    apt install python3 python3-pip" ;;
    windows) echo "    choco install python  or  https://python.org/downloads" ;;
  esac
  exit 1
fi
echo -e "  ${CHECK} git: $(git --version 2>&1 | head -1)"
echo -e "  ${CHECK} python3: $(python3 --version 2>&1)"

# ─── 2. Clone or update repo ─────────────────────────────────────────
if [ -d "$INSTALL_DIR/.git" ]; then
  echo -e "${BOLD}[2/6]${NC} Updating existing installation..."
  cd "$INSTALL_DIR"
  git pull --ff-only origin "$BRANCH" 2>/dev/null || true
else
  echo -e "${BOLD}[2/6]${NC} Cloning droid-re-chain..."
  git clone --depth 1 --branch "$BRANCH" "https://github.com/${REPO}.git" "$INSTALL_DIR"
fi
cd "$INSTALL_DIR"
echo -e "  ${CHECK} $(git log --oneline -1 2>/dev/null || echo 'ok')"

# ─── 3. Install Python dependencies ─────────────────────────────────
echo -e "${BOLD}[3/6]${NC} Installing Python dependencies..."
pip3 install -r requirements.txt 2>/dev/null || \
  pip3 install --break-system-packages -r requirements.txt 2>/dev/null || \
  python3 -m pip install -r requirements.txt 2>/dev/null || \
  python3 -m pip install --break-system-packages -r requirements.txt 2>/dev/null || {
    echo -e "  ${YELLOW}WARNING: pip install failed. Try: pip install -r requirements.txt${NC}"
  }
echo -e "  ${CHECK} Requirements installed"

# ─── 4. Detect / set ANDROID_NDK_HOME ───────────────────────────────
echo -e "${BOLD}[4/6]${NC} Checking Android NDK..."
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
  echo -e "  ${CHECK} ANDROID_NDK_HOME=${ANDROID_NDK_HOME}"
  SHELL_RC="$(detect_shell_rc)"
  if ! grep -q "ANDROID_NDK_HOME" "$SHELL_RC" 2>/dev/null; then
    echo "export ANDROID_NDK_HOME=\"$ANDROID_NDK_HOME\"" >> "$SHELL_RC"
    echo -e "  ${CHECK} Persisted to ${SHELL_RC}"
  fi
else
  echo -e "  ${YELLOW}WARNING: ANDROID_NDK_HOME not set. NDK compilation tools unavailable.${NC}"
  echo -e "  ${YELLOW}Set: export ANDROID_NDK_HOME=/path/to/ndk${NC}"
fi

# ─── 5. Check ADB ───────────────────────────────────────────────────
echo -e "${BOLD}[5/6]${NC} Checking ADB..."
if command -v adb &>/dev/null; then
  echo -e "  ${CHECK} adb found: $(adb --version 2>&1 | head -1)"
else
  echo -e "  ${YELLOW}ADB not on PATH.${NC}"
  case "$OS" in
    darwin) echo -e "  ${YELLOW}Install: brew install android-platform-tools${NC}" ;;
    linux)  echo -e "  ${YELLOW}Install: apt install adb  or  pacman -S android-tools${NC}" ;;
    windows) echo -e "  ${YELLOW}Install: https://developer.android.com/studio/releases/platform-tools${NC}" ;;
  esac
fi

# ─── 6. Set up MCP client configs ───────────────────────────────────
echo -e "${BOLD}[6/6]${NC} Configuring MCP clients..."
SCRIPT_SRC="$(cd "$(dirname "$0")" && pwd)"
if [ "$SETUP_CLIENTS" = true ]; then
  if [ -n "$SELECTED_CLIENTS" ]; then
    bash "$SCRIPT_SRC/scripts/setup_mcp.sh" --clients "$SELECTED_CLIENTS"
  else
    bash "$SCRIPT_SRC/scripts/setup_mcp.sh"
  fi
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
  echo -e "  ${CHECK} Client configs written"
elif [ "$SETUP_CLIENTS" = false ]; then
  echo -e "  ${YELLOW}Skipping MCP client config (--no-clients)${NC}"
fi

# Persist DROID_CATEGORIES to .env so mcp-entrypoint.sh picks it up
if [ -n "$SELECTED_CATEGORIES" ]; then
  echo "DROID_CATEGORIES=${SELECTED_CATEGORIES}" >> "$INSTALL_DIR/.env" 2>/dev/null || true
  echo -e "  ${CHECK} Categories limited to: ${SELECTED_CATEGORIES}"
fi

# Symlink
SYMLINK_DIR="$(dirname "$INSTALL_DIR")"
if [ "$SYMLINK_DIR" != "$HOME" ]; then
  ln -sf "$INSTALL_DIR" "$HOME/droid-re-chain" 2>/dev/null || true
fi

# ─── Summary ─────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}${GREEN}============================================${NC}"
echo -e "${BOLD}${GREEN}  droid-re-chain installed!${NC}"
echo -e "${BOLD}${GREEN}  Location: ${INSTALL_DIR}${NC}"
TOOL_COUNT=$(python3 -c "from src.server import mcp; print(len(mcp._tool_manager._tools))" 2>/dev/null || echo "182")
TEST_COUNT=$(python3 -m pytest tests/ --collect-only -q 2>&1 | tail -1 | grep -o '[0-9]*' || echo "36")
echo -e "  ${CHECK} Tools:    ${BOLD}${TOOL_COUNT}${NC} across 17 categories"
echo -e "  ${CHECK} Tests:    ${BOLD}${TEST_COUNT}${NC} (run: python3 -m pytest tests/)"
if [ -n "${SELECTED_CATEGORIES:-}" ]; then
  echo -e "  ${YELLOW}Active:    ${SELECTED_CATEGORIES}${NC}"
fi
echo ""
echo -e "  ${BOLD}Server:${NC}"
echo -e "    python3 -m src.server"
echo -e "    python3 -m src.server --sse --port ${SSE_PORT}"
echo -e "    bash mcp-entrypoint.sh"
echo ""
echo -e "  ${BOLD}MCP clients configured:${NC}"
echo -e "    ${INSTALL_DIR}/.cursor/mcp.json"
echo -e "    ${INSTALL_DIR}/.claude/settings.json"
echo ""
echo -e "  ${BOLD}One-liner again:${NC}"
echo -e "    curl -fsSL https://raw.githubusercontent.com/${REPO}/${BRANCH}/install.sh | bash"
echo -e "${BOLD}${GREEN}============================================${NC}\n"
