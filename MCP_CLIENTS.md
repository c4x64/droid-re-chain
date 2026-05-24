# MCP Client Setup Reference

How to connect droid-re-chain to every major MCP-compatible client — IDEs, desktop apps, CLI tools, and multi-agent frameworks.

---

## AI-Native IDEs & Code Editors

### 1. Cursor

**Config location:** `.cursor/mcp.json` (project root)

```json
{
  "mcpServers": {
    "droid-re-chain": {
      "command": "bash",
      "args": ["mcp-entrypoint.sh"]
    }
  }
}
```

Or via **Cursor Settings → Features → MCP Servers → Add new server**.

---

### 2. Windsurf

**Config location:** `~/.codeium/windsurf/mcp_config.json` (global only)

```json
{
  "mcpServers": {
    "droid-re-chain": {
      "command": "bash",
      "args": ["/absolute/path/to/mcp-entrypoint.sh"]
    }
  }
}
```

Create the file if it doesn't exist. Windsurf has a **100-tool hard limit** across all servers — droid-re-chain exposes 122, so some tools will be unavailable. Disable other servers or use a subset.

---

### 3. Google Antigravity

**Config location:** `mcp_config.json` (project root)

```json
{
  "mcpConfig": {
    "servers": [
      {
        "name": "droid-re-chain",
        "transport": "stdio",
        "command": ["bash", "mcp-entrypoint.sh"]
      }
    ]
  }
}
```

---

### 4. PearAI

**Config location:** `.pearai/mcp.json` (project root) or PearAI Settings → MCP

```json
{
  "mcpServers": {
    "droid-re-chain": {
      "command": "bash",
      "args": ["mcp-entrypoint.sh"]
    }
  }
}
```

---

## Desktop Applications & Assistants

### 5. Claude Desktop

**Config location:**
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`
- Linux: `~/.config/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "droid-re-chain": {
      "command": "bash",
      "args": ["/absolute/path/to/mcp-entrypoint.sh"]
    }
  }
}
```

Restart Claude Desktop after saving. The droid-re-chain tools appear in the chat UI.

---

### 6. ChatGPT Desktop

**Config location:** ChatGPT Settings → MCP Servers → Add Server

```json
{
  "mcpServers": {
    "droid-re-chain": {
      "command": "bash",
      "args": ["/absolute/path/to/mcp-entrypoint.sh"]
    }
  }
}
```

---

### 7. LibreChat

**Config location:** `librechat.yaml` (project root)

```yaml
mcp:
  servers:
    droid-re-chain:
      type: stdio
      command: bash
      args:
        - mcp-entrypoint.sh
```

---

### 8. Jan

**Config location:** `~/jan/plugins/` or Jan Settings → MCP

Place `droid-re-chain.json` in the plugins directory:

```json
{
  "mcpServers": {
    "droid-re-chain": {
      "command": "bash",
      "args": ["/absolute/path/to/mcp-entrypoint.sh"]
    }
  }
}
```

---

## Terminal, CLI & Orchestration Tools

### 9. Goose CLI

**Config location:** `~/.goose/config.yaml`

```yaml
name: droid-re-chain
version: 0.3.0
type: stdio
command: bash
args:
  - "/absolute/path/to/mcp-entrypoint.sh"
env:
  ANDROID_NDK_HOME: "${ANDROID_NDK_HOME}"
```

Or run on-the-fly: `goose run --mcp bash mcp-entrypoint.sh`

---

### 10. Claude Code

**Config location:** `.claude/settings.json` (project root) or `~/.claude/settings.json`

```json
{
  "mcpServers": {
    "droid-re-chain": {
      "command": "bash",
      "args": ["mcp-entrypoint.sh"]
    }
  }
}
```

Project-level config takes precedence over global. Restart Claude Code to activate.

---

### 11. Aider

**Config location:** `.aider.conf.yml` or `~/.aider.conf.yml`

```yaml
mcp-servers:
  droid-re-chain:
    command: bash
    args:
      - mcp-entrypoint.sh
```

Or pass on CLI: `aider --mcp-servers droid-re-chain=bash,mcp-entrypoint.sh`

---

## Multi-Agent Frameworks

### 12. AutoGen Studio

**Config location:** Workspace settings (AutoGen Studio UI → Add MCP Server)

```json
{
  "version": "0.1.0",
  "components": {
    "droid-re-chain": {
      "type": "mcp",
      "config": {
        "command": "bash",
        "args": ["mcp-entrypoint.sh"],
        "transport": "stdio"
      }
    }
  }
}
```

---

### 13. CrewAI Enterprise

**Config location:** `crew.yaml` or environment variable

```yaml
mcp_servers:
  - name: droid-re-chain
    type: stdio
    command: bash
    args:
      - mcp-entrypoint.sh
```

Or via env: `CREWAI_MCP_SERVERS='[{"name":"droid-re-chain","command":"bash","args":["mcp-entrypoint.sh"]}]'`

---

### 14. LangGraph / LangChain

**Config location:** `langgraph.json` (project root) or Python code

```json
{
  "node": {
    "mcpServers": {
      "droid-re-chain": {
        "command": "bash",
        "args": ["mcp-entrypoint.sh"]
      }
    }
  }
}
```

Or in Python:

```python
from langchain_mcp import McpServer
server = McpServer(name="droid-re-chain", command="bash", args=["mcp-entrypoint.sh"])
```

---

## VS Code Extensions

### 15. Roo Code

**Config location:** `.roo/mcp.json` (project level) or VS Code global storage

Project-level (recommended, shareable via git):

```json
{
  "mcpServers": {
    "droid-re-chain": {
      "command": "bash",
      "args": ["mcp-entrypoint.sh"],
      "alwaysAllow": ["health_check"],
      "disabled": false
    }
  }
}
```

Global config path:
- macOS: `~/Library/Application Support/Code/User/globalStorage/rooveterinaryinc.roo-cline/settings/mcp_settings.json`
- Linux: `~/.config/Code/User/globalStorage/rooveterinaryinc.roo-cline/settings/mcp_settings.json`
- Windows: `%APPDATA%\Code\User\globalStorage\rooveterinaryinc.roo-cline\settings\mcp_settings.json`

Open via Roo Code panel → MCP Servers → Edit Global/Project MCP.

---

### 16. Continue

**Config location:** `.continue/mcpServers/mcp.json` or `~/.continue/config.yaml`

Place a JSON file in `.continue/mcpServers/`:

```json
{
  "mcpServers": {
    "droid-re-chain": {
      "command": "bash",
      "args": ["mcp-entrypoint.sh"]
    }
  }
}
```

Or add to `~/.continue/config.yaml`:

```yaml
mcpServers:
  - name: droid-re-chain
    command: bash
    args:
      - mcp-entrypoint.sh
```

Continue auto-discovers both formats. Reload the VS Code window after saving.

---

### 17. VS Code Native MCP (1.102+)

**Config location:** `.vscode/mcp.json` (workspace level)

```json
{
  "mcpServers": {
    "droid-re-chain": {
      "command": "bash",
      "args": ["mcp-entrypoint.sh"]
    }
  }
}
```

VS Code 1.102+ reads this file automatically. Tools appear in Copilot Chat and agent mode.

---

## Enterprise & Specialized Platforms

### 18. Composio

**Config location:** Composio Dashboard → Add Tool → Custom MCP

```json
{
  "mcpServers": {
    "droid-re-chain": {
      "command": "bash",
      "args": ["mcp-entrypoint.sh"]
    }
  }
}
```

Composio's agent execution core handles on-demand tool loading. No further config needed.

---

### 19. LlamaIndex Workflows

Configure in Python:

```python
from llama_index.core.agent.workflow import AgentWorkflow
from llama_index.core.tools import McpToolSpec

mcp_spec = McpToolSpec(command="bash", args=["mcp-entrypoint.sh"])
tool_spec = mcp_spec.to_tool_list()
workflow = AgentWorkflow.from_tools(tool_spec)
```

---

### 20. Harvey AI (Enterprise)

Enterprise deployments configure MCP via Harvey's admin dashboard. Provide your platform team with:

```json
{
  "mcpServers": {
    "droid-re-chain": {
      "command": "bash",
      "args": ["/secure/path/to/mcp-entrypoint.sh"],
      "env": {
        "ANDROID_NDK_HOME": "/path/to/ndk"
      }
    }
  }
}
```

---

## Quick Reference: Config Paths by Platform

| # | Client | Config File | Scope |
|---|--------|------------|-------|
| 1 | Cursor | `.cursor/mcp.json` | Project |
| 2 | Windsurf | `~/.codeium/windsurf/mcp_config.json` | Global |
| 3 | Antigravity | `mcp_config.json` | Project |
| 4 | PearAI | `.pearai/mcp.json` | Project |
| 5 | Claude Desktop | `~/Library/Application Support/Claude/claude_desktop_config.json` | Global |
| 6 | ChatGPT Desktop | Settings → MCP | Global |
| 7 | LibreChat | `librechat.yaml` | Project |
| 8 | Jan | `~/jan/plugins/droid-re-chain.json` | Global |
| 9 | Goose CLI | `~/.goose/config.yaml` | Global |
| 10 | Claude Code | `.claude/settings.json` | Project |
| 11 | Aider | `.aider.conf.yml` | Project |
| 12 | AutoGen Studio | Workspace config | Project |
| 13 | CrewAI | `crew.yaml` | Project |
| 14 | LangGraph | `langgraph.json` | Project |
| 15 | Roo Code | `.roo/mcp.json` | Project |
| 16 | Continue | `.continue/mcpServers/` | Project |
| 17 | VS Code | `.vscode/mcp.json` | Workspace |
| 18 | Composio | Dashboard | Cloud |
| 19 | LlamaIndex | Python code | Runtime |
| 20 | Harvey AI | Admin dashboard | Enterprise |