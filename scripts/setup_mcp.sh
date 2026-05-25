#!/usr/bin/env bash
# Setup droid-re-chain for use with 20+ MCP-compatible clients.
# Detects installed clients and writes/merges configs.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

echo "=== droid-re-chain — MCP Client Auto-Setup ==="
echo "Project: $PROJECT_ROOT"
echo ""

install_count=0
detected_count=0

# Helper: merge droid-re-chain entry into a JSON mcpServers file
merge_json() {
  local file="$1"
  local project_root="$2"
  mkdir -p "$(dirname "$file")"
  if [ -f "$file" ]; then
    python3 -c "
import json
with open('$file') as f: cfg = json.load(f)
servers = cfg.setdefault('mcpServers', {})
servers['droid-re-chain'] = {
    'command': 'bash',
    'args': ['$project_root/mcp-entrypoint.sh'],
    'env': {'ANDROID_NDK_HOME': '${ANDROID_NDK_HOME:-}',
            'GHIDRA_HOME': '${GHIDRA_HOME:-}'}
}
with open('$file', 'w') as f: json.dump(cfg, f, indent=2)
print('  merged')
" 2>/dev/null && return 0 || return 1
  else
    python3 -c "
import json
cfg = {
    'mcpServers': {
        'droid-re-chain': {
            'command': 'bash',
            'args': ['$project_root/mcp-entrypoint.sh'],
        'env': {'ANDROID_NDK_HOME': '${ANDROID_NDK_HOME:-}',
                'GHIDRA_HOME': '${GHIDRA_HOME:-}'}
    }
}
with open('$file', 'w') as f: json.dump(cfg, f, indent=2)
print('  created')
" 2>/dev/null && return 0 || return 1
  fi
}

# --- 1. Cursor ---
echo "[1/20] Cursor..."
CURSOR_FILE="$PROJECT_ROOT/.cursor/mcp.json"
merge_json "$CURSOR_FILE" "$PROJECT_ROOT" && install_count=$((install_count+1))

# --- 2. Windsurf ---
echo "[2/20] Windsurf..."
WINDSURF_FILE="$HOME/.codeium/windsurf/mcp_config.json"
merge_json "$WINDSURF_FILE" "$PROJECT_ROOT" && install_count=$((install_count+1))

# --- 3. Antigravity ---
echo "[3/20] Antigravity..."
AG_FILE="$PROJECT_ROOT/mcp_config.json"
python3 -c "
import json
cfg = {
    'mcpConfig': {
        'servers': [{
            'name': 'droid-re-chain',
            'transport': 'stdio',
            'command': ['bash', '$PROJECT_ROOT/mcp-entrypoint.sh']
        }]
    }
}
with open('$AG_FILE', 'w') as f: json.dump(cfg, f, indent=2)
print('  created')
" && install_count=$((install_count+1))

# --- 4. PearAI ---
echo "[4/20] PearAI..."
PEARAI_FILE="$PROJECT_ROOT/.pearai/mcp.json"
mkdir -p "$(dirname "$PEARAI_FILE")"
merge_json "$PEARAI_FILE" "$PROJECT_ROOT" && install_count=$((install_count+1))

# --- 5. Claude Desktop ---
echo "[5/20] Claude Desktop..."
if [ "$(uname)" = "Darwin" ]; then
  CLAUDE_FILE="$HOME/Library/Application Support/Claude/claude_desktop_config.json"
elif [ "$(uname)" = "Linux" ]; then
  CLAUDE_FILE="$HOME/.config/Claude/claude_desktop_config.json"
else
  CLAUDE_FILE="$APPDATA/Claude/claude_desktop_config.json"
fi
if merge_json "$CLAUDE_FILE" "$PROJECT_ROOT"; then
  install_count=$((install_count+1))
else
  echo "  (Claude Desktop may not be installed)"
fi

# --- 6. ChatGPT Desktop ---
echo "[6/20] ChatGPT Desktop..."
echo "  Manual: Add via ChatGPT Settings > MCP Servers"
echo "  Config file would go at: $HOME/Library/Application Support/OpenAI/chatgpt/mcp.json" 2>/dev/null || true
CHATGPT_FILE="$HOME/Library/Application Support/OpenAI/chatgpt/mcp.json"
if merge_json "$CHATGPT_FILE" "$PROJECT_ROOT" 2>/dev/null; then
  install_count=$((install_count+1))
fi

# --- 7. LibreChat ---
echo "[7/20] LibreChat..."
LCHAT_FILE="$PROJECT_ROOT/librechat.yaml"
cat > "$LCHAT_FILE" 2>/dev/null << YAML
mcp:
  servers:
    droid-re-chain:
      type: stdio
      command: bash
      args:
        - $PROJECT_ROOT/mcp-entrypoint.sh
YAML
echo "  created"

# --- 8. Jan ---
echo "[8/20] Jan..."
JAN_DIR="$HOME/jan/plugins"
mkdir -p "$JAN_DIR"
JAN_FILE="$JAN_DIR/droid-re-chain.json"
merge_json "$JAN_FILE" "$PROJECT_ROOT" && install_count=$((install_count+1))

# --- 9. Goose CLI ---
echo "[9/20] Goose CLI..."
GOOSE_DIR="$HOME/.goose"
mkdir -p "$GOOSE_DIR"
GOOSE_FILE="$GOOSE_DIR/config.yaml"
cat > "$GOOSE_FILE" 2>/dev/null << YAML
name: droid-re-chain
version: 0.3.0
type: stdio
command: bash
args:
  - $PROJECT_ROOT/mcp-entrypoint.sh
env:
  ANDROID_NDK_HOME: ${ANDROID_NDK_HOME:-}
  GHIDRA_HOME: ${GHIDRA_HOME:-}
YAML
echo "  created"

# --- 10. Claude Code ---
echo "[10/20] Claude Code..."
CLAUDE_CODE_FILE="$PROJECT_ROOT/.claude/settings.json"
merge_json "$CLAUDE_CODE_FILE" "$PROJECT_ROOT" && install_count=$((install_count+1))

# --- 11. Aider ---
echo "[11/20] Aider..."
AIDER_FILE="$PROJECT_ROOT/.aider.conf.yml"
cat >> "$AIDER_FILE" 2>/dev/null << YAML

# droid-re-chain MCP server
mcp-servers:
  droid-re-chain:
    command: bash
    args:
      - $PROJECT_ROOT/mcp-entrypoint.sh
YAML
echo "  appended to $AIDER_FILE"

# --- 12. AutoGen Studio ---
echo "[12/20] AutoGen Studio..."
AUTOGEN_DIR="$PROJECT_ROOT/autogenstudio"
mkdir -p "$AUTOGEN_DIR"
AUTOGEN_FILE="$AUTOGEN_DIR/workspace.json"
python3 -c "
import json
cfg = {
    'version': '0.1.0',
    'components': {
        'droid-re-chain': {
            'type': 'mcp',
            'config': {
                'command': 'bash',
                'args': ['$PROJECT_ROOT/mcp-entrypoint.sh'],
                'transport': 'stdio'
            }
        }
    }
}
with open('$AUTOGEN_FILE', 'w') as f: json.dump(cfg, f, indent=2)
print('  created')
" && install_count=$((install_count+1))

# --- 13. CrewAI ---
echo "[13/20] CrewAI..."
CREW_FILE="$PROJECT_ROOT/crew.yaml"
cat >> "$CREW_FILE" 2>/dev/null << YAML

# droid-re-chain MCP
mcp_servers:
  - name: droid-re-chain
    type: stdio
    command: bash
    args:
      - $PROJECT_ROOT/mcp-entrypoint.sh
YAML
echo "  appended to $CREW_FILE"

# --- 14. LangGraph ---
echo "[14/20] LangGraph..."
LGRAPH_FILE="$PROJECT_ROOT/langgraph.json"
python3 -c "
import json
cfg = {
    'node': {
        'mcpServers': {
            'droid-re-chain': {
                'command': 'bash',
                'args': ['$PROJECT_ROOT/mcp-entrypoint.sh']
            }
        }
    }
}
with open('$LGRAPH_FILE', 'w') as f: json.dump(cfg, f, indent=2)
print('  created')
" && install_count=$((install_count+1))

# --- 15. Roo Code ---
echo "[15/20] Roo Code..."
ROO_FILE="$PROJECT_ROOT/.roo/mcp.json"
mkdir -p "$(dirname "$ROO_FILE")"
python3 -c "
import json
cfg = {
    'mcpServers': {
        'droid-re-chain': {
            'command': 'bash',
            'args': ['$PROJECT_ROOT/mcp-entrypoint.sh'],
            'alwaysAllow': ['health_check'],
            'disabled': False
        }
    }
}
with open('$ROO_FILE', 'w') as f: json.dump(cfg, f, indent=2)
print('  created')
" && install_count=$((install_count+1))

# --- 16. Continue ---
echo "[16/20] Continue..."
CONTINUE_DIR="$PROJECT_ROOT/.continue/mcpServers"
mkdir -p "$CONTINUE_DIR"
CONTINUE_FILE="$CONTINUE_DIR/droid-re-chain.json"
python3 -c "
import json
cfg = {
    'mcpServers': {
        'droid-re-chain': {
            'command': 'bash',
            'args': ['$PROJECT_ROOT/mcp-entrypoint.sh']
        }
    }
}
with open('$CONTINUE_FILE', 'w') as f: json.dump(cfg, f, indent=2)
print('  created')
" && install_count=$((install_count+1))

# --- 17. VS Code Native ---
echo "[17/20] VS Code Native MCP..."
VSCODE_FILE="$PROJECT_ROOT/.vscode/mcp.json"
mkdir -p "$(dirname "$VSCODE_FILE")"
merge_json "$VSCODE_FILE" "$PROJECT_ROOT" && install_count=$((install_count+1))

# --- 18. Composio ---
echo "[18/20] Composio..."
echo "  Manual: Add via Composio Dashboard > Add Tool > Custom MCP"
echo "  Or CLI: composio add-tool droid-re-chain bash $PROJECT_ROOT/mcp-entrypoint.sh"

# --- 19. LlamaIndex ---
echo "[19/20] LlamaIndex..."
echo "  Python integration:"
echo '    from llama_index.core.tools import McpToolSpec'
echo "    mcp_spec = McpToolSpec(command='bash', args=['$PROJECT_ROOT/mcp-entrypoint.sh'])"

# --- 20. Harvey AI ---
echo "[20/20] Harvey AI..."
echo "  Enterprise: Provide config to your platform team:"
echo "    {\"mcpServers\":{\"droid-re-chain\":{\"command\":\"bash\",\"args\":[\"$PROJECT_ROOT/mcp-entrypoint.sh\"]}}}"

echo ""
echo "=== Done ==="
echo "Config files written/updated: $install_count"
echo ""
echo "Restart your MCP host(s) to activate droid-re-chain."
echo "Test: python3 -m src.server"
echo "Docs: cat MCP_CLIENTS.md"