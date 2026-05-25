#!/usr/bin/env bash
# Setup droid-re-chain for use with 20+ MCP-compatible clients.
# Detects installed clients and writes/merges configs.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

# Parse --clients flag for selective setup
SELECTED_CLIENTS=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --clients) SELECTED_CLIENTS="$2"; shift 2 ;;
    *) shift ;;
  esac
done

echo "=== droid-re-chain — MCP Client Auto-Setup ==="
echo "Project: $PROJECT_ROOT"
echo ""

# Helper: check if a client name is in SELECTED_CLIENTS (if set)
client_wanted() {
  [ -z "$SELECTED_CLIENTS" ] && return 0
  local name="$1"
  [[ ",$SELECTED_CLIENTS," == *",$name,"* ]] && return 0
  return 1
}

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
echo "[1/21] Cursor..."
if client_wanted "cursor"; then
  CURSOR_FILE="$PROJECT_ROOT/.cursor/mcp.json"
  merge_json "$CURSOR_FILE" "$PROJECT_ROOT" && install_count=$((install_count+1))
else
  echo "  skipped"
fi

# --- 2. Windsurf ---
echo "[2/21] Windsurf..."
if client_wanted "windsurf"; then
  WINDSURF_FILE="$HOME/.codeium/windsurf/mcp_config.json"
  merge_json "$WINDSURF_FILE" "$PROJECT_ROOT" && install_count=$((install_count+1))
else
  echo "  skipped"
fi

# --- 3. Antigravity ---
echo "[3/21] Antigravity..."
if client_wanted "antigravity"; then
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
else
  echo "  skipped"
fi

# --- 4. PearAI ---
echo "[4/21] PearAI..."
if client_wanted "pearai"; then
  PEARAI_FILE="$PROJECT_ROOT/.pearai/mcp.json"
  mkdir -p "$(dirname "$PEARAI_FILE")"
  merge_json "$PEARAI_FILE" "$PROJECT_ROOT" && install_count=$((install_count+1))
else
  echo "  skipped"
fi

# --- 5. Claude Desktop ---
echo "[5/21] Claude Desktop..."
if client_wanted "claude_desktop"; then
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
else
  echo "  skipped"
fi

# --- 6. ChatGPT Desktop ---
echo "[6/21] ChatGPT Desktop..."
if client_wanted "chatgpt"; then
  echo "  Manual: Add via ChatGPT Settings > MCP Servers"
  echo "  Config file would go at: $HOME/Library/Application Support/OpenAI/chatgpt/mcp.json" 2>/dev/null || true
  CHATGPT_FILE="$HOME/Library/Application Support/OpenAI/chatgpt/mcp.json"
  if merge_json "$CHATGPT_FILE" "$PROJECT_ROOT" 2>/dev/null; then
    install_count=$((install_count+1))
  fi
else
  echo "  skipped"
fi

# --- 7. LibreChat ---
echo "[7/21] LibreChat..."
if client_wanted "librechat"; then
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
else
  echo "  skipped"
fi

# --- 8. Jan ---
echo "[8/21] Jan..."
if client_wanted "jan"; then
  JAN_DIR="$HOME/jan/plugins"
  mkdir -p "$JAN_DIR"
  JAN_FILE="$JAN_DIR/droid-re-chain.json"
  merge_json "$JAN_FILE" "$PROJECT_ROOT" && install_count=$((install_count+1))
else
  echo "  skipped"
fi

# --- 9. Goose CLI ---
echo "[9/21] Goose CLI..."
if client_wanted "goose"; then
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
else
  echo "  skipped"
fi

# --- 10. Claude Code ---
echo "[10/21] Claude Code..."
if client_wanted "claude_code"; then
  CLAUDE_CODE_FILE="$PROJECT_ROOT/.claude/settings.json"
  merge_json "$CLAUDE_CODE_FILE" "$PROJECT_ROOT" && install_count=$((install_count+1))
else
  echo "  skipped"
fi

# --- 11. Aider ---
echo "[11/21] Aider..."
if client_wanted "aider"; then
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
else
  echo "  skipped"
fi

# --- 12. AutoGen Studio ---
echo "[12/21] AutoGen Studio..."
if client_wanted "autogen"; then
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
else
  echo "  skipped"
fi

# --- 13. CrewAI ---
echo "[13/21] CrewAI..."
if client_wanted "crewai"; then
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
else
  echo "  skipped"
fi

# --- 14. LangGraph ---
echo "[14/21] LangGraph..."
if client_wanted "langgraph"; then
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
else
  echo "  skipped"
fi

# --- 15. Roo Code ---
echo "[15/21] Roo Code..."
if client_wanted "roo_code"; then
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
else
  echo "  skipped"
fi

# --- 16. Continue ---
echo "[16/21] Continue..."
if client_wanted "continue"; then
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
else
  echo "  skipped"
fi

# --- 17. VS Code Native ---
echo "[17/21] VS Code Native MCP..."
if client_wanted "vscode"; then
  VSCODE_FILE="$PROJECT_ROOT/.vscode/mcp.json"
  mkdir -p "$(dirname "$VSCODE_FILE")"
  merge_json "$VSCODE_FILE" "$PROJECT_ROOT" && install_count=$((install_count+1))
else
  echo "  skipped"
fi

# --- 18. Composio ---
echo "[18/21] Composio..."
if client_wanted "composio"; then
  echo "  Manual: Add via Composio Dashboard > Add Tool > Custom MCP"
  echo "  Or CLI: composio add-tool droid-re-chain bash $PROJECT_ROOT/mcp-entrypoint.sh"
else
  echo "  skipped"
fi

# --- 19. LlamaIndex ---
echo "[19/21] LlamaIndex..."
if client_wanted "llamaindex"; then
  echo "  Python integration:"
  echo '    from llama_index.core.tools import McpToolSpec'
  echo "    mcp_spec = McpToolSpec(command='bash', args=['$PROJECT_ROOT/mcp-entrypoint.sh'])"
else
  echo "  skipped"
fi

# --- 20. Harvey AI ---
echo "[20/21] Harvey AI..."
if client_wanted "harvey"; then
  echo "  Enterprise: Provide config to your platform team:"
  echo "    {\"mcpServers\":{\"droid-re-chain\":{\"command\":\"bash\",\"args\":[\"$PROJECT_ROOT/mcp-entrypoint.sh\"]}}}"
else
  echo "  skipped"
fi

# --- 21. opencode ---
echo "[21/21] opencode..."
if client_wanted "opencode"; then
  OPCODE_FILE="$HOME/.config/opencode/opencode.jsonc"
  mkdir -p "$(dirname "$OPCODE_FILE")"
  python3 -c "
import json
# opencode uses 'mcp' key (not 'mcpServers') and JSONC
cfg = {}
if __import__('os').path.isfile('$OPCODE_FILE'):
    with open('$OPCODE_FILE') as f:
        # strip comments (JSONC) - basic approach
        lines = []
        for line in f:
            stripped = line.strip()
            if stripped.startswith('//') or stripped.startswith('#'):
                continue
            lines.append(line)
        content = ''.join(lines)
        if content.strip():
            cfg = json.loads(content)
if 'mcp' not in cfg:
    cfg['mcp'] = {}
cfg['mcp']['droid-re-chain'] = {
    'type': 'local',
    'command': ['bash', '$PROJECT_ROOT/mcp-entrypoint.sh'],
    'enabled': True,
    'timeout': 5000,
    'env': {
        'ANDROID_NDK_HOME': '${ANDROID_NDK_HOME:-}',
        'GHIDRA_HOME': '${GHIDRA_HOME:-}'
    }
}
with open('$OPCODE_FILE', 'w') as f:
    json.dump(cfg, f, indent=2)
    f.write('\n')
print('  updated')
" && install_count=$((install_count+1))
else
  echo "  skipped"
fi

echo ""
echo "=== Done ==="
echo "Config files written/updated: $install_count"
echo ""
echo "Restart your MCP host(s) to activate droid-re-chain."
echo "Test: python3 -m src.server"
echo "Docs: cat MCP_CLIENTS.md"