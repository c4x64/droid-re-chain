#!/usr/bin/env bash
# Setup droid-re-chain for use with other agentic tools.
# Links MCP configs into Claude Code, Cursor, and opencode.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

echo "=== droid-re-chain MCP Integration Setup ==="

# --- Claude Code (CLI app) ---
CLAUDE_CLI_DIR="$HOME/.claude"
mkdir -p "$CLAUDE_CLI_DIR"
CLAUDE_CONFIG="$CLAUDE_CLI_DIR/settings.json"
if [ -f "$CLAUDE_CONFIG" ]; then
  echo "Merging with existing $CLAUDE_CONFIG..."
  python3 -c "
import json
with open('$CLAUDE_CONFIG') as f: cfg = json.load(f)
servers = cfg.setdefault('mcpServers', {})
servers['droid-re-chain'] = {
    'command': 'bash',
    'args': ['$PROJECT_ROOT/mcp-entrypoint.sh'],
    'env': {'ANDROID_NDK_HOME': '${ANDROID_NDK_HOME:-}'}
}
with open('$CLAUDE_CONFIG', 'w') as f: json.dump(cfg, f, indent=2)
print('Updated Claude Code config')
"
else
  python3 -c "
import json
cfg = {
    'mcpServers': {
        'droid-re-chain': {
            'command': 'bash',
            'args': ['$PROJECT_ROOT/mcp-entrypoint.sh'],
            'env': {'ANDROID_NDK_HOME': '${ANDROID_NDK_HOME:-}'}
        }
    }
}
with open('$CLAUDE_CONFIG', 'w') as f: json.dump(cfg, f, indent=2)
print('Created Claude Code config')
"
fi

# --- Cursor ---
CURSOR_CONFIG_DIR="$HOME/.cursor"
mkdir -p "$CURSOR_CONFIG_DIR"
CURSOR_CONFIG="$CURSOR_CONFIG_DIR/mcp.json"
if [ -f "$CURSOR_CONFIG" ]; then
  echo "Cursor config exists at $CURSOR_CONFIG — add manually or merge."
  echo "  Source: $PROJECT_ROOT/.cursor/mcp.json"
else
  python3 -c "
import json
cfg = {
    'mcpServers': {
        'droid-re-chain': {
            'type': 'local',
            'command': 'bash',
            'args': ['$PROJECT_ROOT/mcp-entrypoint.sh'],
            'env': {'ANDROID_NDK_HOME': '${ANDROID_NDK_HOME:-}'},
            'disabled': false,
            'autoApprove': []
        }
    }
}
with open('$CURSOR_CONFIG', 'w') as f: json.dump(cfg, f, indent=2)
print('Created Cursor config')
"
fi

# --- opencode (project-level config already exists) ---
echo "opencode config: $PROJECT_ROOT/config/opencode.json"
echo "  Symlink: ln -sf $PROJECT_ROOT/config/opencode.json \$PWD/opencode.json"

# --- VS Code (via MCP extension) ---
VSCODE_CONFIG="$HOME/Library/Application Support/Code/User/globalStorage/rooveterinaryinc.roo-cline/settings/cline_mcp_settings.json"
if [ -f "$VSCODE_CONFIG" ]; then
  echo "VS Code MCP config found at $VSCODE_CONFIG"
else
  echo "VS Code MCP config not found (Roo Cline / Continue extension not installed?)"
fi

echo ""
echo "=== Setup complete ==="
echo "Restart your MCP host (Claude Code, Cursor, etc.) to pick up the new server."
echo "Test with: python3 -m src.server"