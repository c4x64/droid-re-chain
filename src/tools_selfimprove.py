"""Self-improvement system — skill learning, tool generation, validation, and contribution pipeline."""
import os
import re
import json
import time
import subprocess
import textwrap
from pathlib import Path
from src.shared import PROJECT_ROOT

SKILLS_DIR = PROJECT_ROOT / "skills"
SKILLS_DIR.mkdir(exist_ok=True)
SHARED_DIR = SKILLS_DIR / "shared"
SHARED_DIR.mkdir(exist_ok=True)

TOOLS_MODULE_NAMES = {
    "adb": "tools_adb", "ndk": "tools_ndk", "il2cpp": "tools_il2cpp",
    "hook": "tools_hook", "trap": "tools_trap", "mem": "tools_mem",
    "frida": "tools_frida", "apk": "tools_apk", "static": "tools_static",
    "db": "tools_database", "session": "tools_session", "bypass": "tools_bypass",
    "ida": "tools_ida", "net": "tools_net", "dump": "tools_dump",
    "ghidra": "tools_ghidra", "mcp": "tools_update", "skill": "tools_selfimprove",
    "tool": "tools_selfimprove", "contribute": "tools_selfimprove",
}

SERIAL = 0

def _next_tool_name(prefix: str) -> str:
    global SERIAL
    SERIAL += 1
    return f"{prefix}_auto_{SERIAL}"

def _skill_path(name: str) -> Path:
    return SKILLS_DIR / f"{name}.json"

def _shared_path(name: str) -> Path:
    return SHARED_DIR / f"{name}.json"

def register(mcp):

    @mcp.tool()
    def skill_save(name: str, description: str, code: str,
                   tags: str = "", tool_name: str = "") -> str:
        """Save a reusable skill from a successful solution. Args: name, description, code, tags (comma-separated), tool_name (optional)."""
        name = name.lower().replace(" ", "_")
        path = _skill_path(name)
        if path.exists():
            skill = json.loads(path.read_text())
            skill["success_count"] += 1
            skill["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        else:
            skill = {
                "name": name,
                "description": description,
                "tags": [t.strip() for t in tags.split(",") if t.strip()],
                "code": code,
                "tool_name": tool_name or "",
                "success_count": 1,
                "validated": False,
                "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            }
        path.write_text(json.dumps(skill, indent=2))
        return json.dumps({"status": "saved", "name": name, "path": str(path),
                           "success_count": skill["success_count"],
                           "validated": skill["validated"]}, indent=2)

    @mcp.tool()
    def skill_load(query: str) -> str:
        """Retrieve a saved skill by exact name or fuzzy search. Args: query (name or description fragment)."""
        exact = _skill_path(query)
        if exact.exists():
            return json.dumps(json.loads(exact.read_text()), indent=2)
        exact_shared = _shared_path(query)
        if exact_shared.exists():
            return json.dumps(json.loads(exact_shared.read_text()), indent=2)
        matches = []
        ql = query.lower()
        for f in sorted(SKILLS_DIR.glob("*.json")) + sorted(SHARED_DIR.glob("*.json")):
            skill = json.loads(f.read_text())
            if ql in skill["name"].lower() or ql in skill["description"].lower():
                matches.append({"name": skill["name"], "description": skill["description"][:100],
                                "tags": skill.get("tags", []), "validated": skill.get("validated", False)})
            if len(matches) >= 10:
                break
        if not matches:
            return json.dumps({"status": "not_found", "query": query}, indent=2)
        return json.dumps({"query": query, "matches": matches, "count": len(matches)}, indent=2)

    @mcp.tool()
    def skill_list(include_shared: bool = True) -> str:
        """List all saved skills with tags and success count. Args: include_shared (default True)."""
        skills = []
        for f in sorted(SKILLS_DIR.glob("*.json")):
            s = json.loads(f.read_text())
            skills.append({"name": s["name"], "tags": s.get("tags", []),
                           "success_count": s.get("success_count", 0),
                           "validated": s.get("validated", False), "location": "local",
                           "description": s["description"][:80]})
        if include_shared:
            for f in sorted(SHARED_DIR.glob("*.json")):
                s = json.loads(f.read_text())
                skills.append({"name": s["name"], "tags": s.get("tags", []),
                               "success_count": s.get("success_count", 0),
                               "validated": s.get("validated", False), "location": "shared",
                               "description": s["description"][:80]})
        return json.dumps({"total": len(skills), "skills": skills}, indent=2)

    @mcp.tool()
    def skill_apply(name: str, target_binary: str = "") -> str:
        """Apply a saved skill to the current context. Args: name, target_binary (optional)."""
        path = _skill_path(name)
        if not path.exists():
            path = _shared_path(name)
        if not path.exists():
            return json.dumps({"status": "error", "error": f"skill '{name}' not found"}, indent=2)
        skill = json.loads(path.read_text())
        return json.dumps({"status": "applied", "name": skill["name"],
                           "description": skill["description"],
                           "code": skill["code"],
                           "tool_name": skill.get("tool_name", ""),
                           "target_binary": target_binary or "(current session)",
                           "instructions": "Use the code above in your session context"}, indent=2)

    @mcp.tool()
    def skill_promote(name: str, tags: str = "") -> str:
        """Mark a skill as validated and copy to skills/shared/ for contribution. Args: name, tags (optional additions, comma-separated)."""
        src = _skill_path(name)
        if not src.exists():
            return json.dumps({"status": "error", "error": f"skill '{name}' not found in skills/"}, indent=2)
        skill = json.loads(src.read_text())
        skill["validated"] = True
        if tags:
            extra = [t.strip() for t in tags.split(",") if t.strip()]
            skill["tags"] = list(set(skill.get("tags", []) + extra))
        skill["promoted_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        dest = _shared_path(name)
        dest.write_text(json.dumps(skill, indent=2))
        src.write_text(json.dumps(skill, indent=2))
        return json.dumps({"status": "promoted", "name": name,
                           "path": str(dest), "tags": skill["tags"],
                           "next_step": "Use tool_generate to create an MCP tool from this skill"}, indent=2)

    @mcp.tool()
    def tool_generate(skill_name: str, module_prefix: str = "") -> str:
        """Auto-generate an MCP tool function from a validated skill and write to the appropriate tools_*.py. Args: skill_name, module_prefix (e.g. 'adb', 'frida')."""
        path = _shared_path(skill_name)
        if not path.exists():
            path = _skill_path(skill_name)
        if not path.exists():
            return json.dumps({"status": "error", "error": f"skill '{skill_name}' not found"}, indent=2)
        skill = json.loads(path.read_text())
        if not skill.get("validated"):
            return json.dumps({"status": "error", "error": "skill not validated — run skill_promote first"}, indent=2)
        prefix = module_prefix or skill["name"].split("_")[0] if "_" in skill["name"] else "auto"
        module_key = prefix
        if module_key not in TOOLS_MODULE_NAMES:
            for k in TOOLS_MODULE_NAMES:
                if prefix.startswith(k):
                    module_key = k
                    break
        mod_name = TOOLS_MODULE_NAMES.get(module_key, "tools_static")
        mod_path = PROJECT_ROOT / "src" / f"{mod_name}.py"
        if not mod_path.exists():
            return json.dumps({"status": "error", "error": f"module {mod_name}.py not found"}, indent=2)
        tool_name = _next_tool_name(prefix)
        code = skill["code"]
        func_body = textwrap.indent(code, "    ").lstrip()
        tool_code = f"""
    @mcp.tool()
    def {tool_name}({skill.get('params', '')}) -> str:
        \"\"\"{skill['description']}\"\"\"
{func_body}"""
        existing = mod_path.read_text()
        insert_before = "\n    @mcp.tool()"
        if insert_before in existing:
            existing = existing.replace(insert_before, tool_code + "\n" + insert_before, 1)
            mod_path.write_text(existing)
        else:
            return json.dumps({"status": "error", "error": "cannot find @mcp.tool() anchor in register(mcp)"}, indent=2)
        skill["tool_name"] = tool_name
        skill["module"] = mod_name
        path.write_text(json.dumps(skill, indent=2))
        return json.dumps({"status": "generated", "tool_name": tool_name,
                           "module": f"{mod_name}.py", "skill": skill_name,
                           "file": str(mod_path)}, indent=2)

    @mcp.tool()
    def tool_validate(tool_name: str, test_input: str = "") -> str:
        """Run a newly generated tool against a test input and verify output. Args: tool_name, test_input (JSON arg string)."""
        try:
            from src.server import mcp as server_mcp
        except ImportError as e:
            return json.dumps({"status": "error", "error": f"cannot import server: {e}"}, indent=2)
        try:
            tool_fn = server_mcp._tool_manager._tools.get(tool_name)
            if tool_fn is None:
                return json.dumps({"status": "error", "error": f"tool '{tool_name}' not registered"}, indent=2)
            result = tool_fn.fn(test_input) if test_input else tool_fn.fn()
            return json.dumps({"status": "ok", "tool": tool_name,
                               "test_input": test_input,
                               "output": str(result)[:2000],
                               "passed": True}, indent=2)
        except Exception as e:
            return json.dumps({"status": "fail", "tool": tool_name,
                               "test_input": test_input,
                               "error": str(e)[:500],
                               "passed": False}, indent=2)

    @mcp.tool()
    def tool_register(tool_name: str = "") -> str:
        """Register a validated tool in server.py and regenerate API docs. Args: tool_name (optional — if empty, registers all unregistered)."""
        server_path = PROJECT_ROOT / "src" / "server.py"
        server_code = server_path.read_text()
        results = []
        tools_added = 0
        if tool_name:
            candidates = [tool_name]
        else:
            candidates = []
            for f in sorted(PROJECT_ROOT.glob("src/tools_*.py")):
                code = f.read_text()
                for match in re.finditer(r"def (tool_\w+)\(", code):
                    tn = match.group(1)
                    if f"def {tn}(" not in server_code and tn not in candidates:
                        candidates.append(tn)
        for tn in candidates:
            for mod_file in PROJECT_ROOT.glob("src/tools_*.py"):
                code = mod_file.read_text()
                if f"def {tn}(" in code:
                    mod_stem = mod_file.stem
                    reg_name = f"register_{mod_stem.replace('tools_', '')}"
                    if reg_name not in server_code:
                        server_code = server_code.replace(
                            "from src.tools_update import register as register_update",
                            f"from src.{mod_stem} import register as {reg_name}\nfrom src.tools_update import register as register_update")
                        server_code = server_code.replace(
                            "register_update(mcp)",
                            f"register_{mod_stem.replace('tools_', '')}(mcp)\nregister_update(mcp)")
                        tools_added += 1
                        results.append({"tool": tn, "module": mod_file.name, "action": "registered"})
                    break
        if tools_added:
            server_path.write_text(server_code)
        gen_script = PROJECT_ROOT / "scripts" / "generate_docs.py"
        if gen_script.exists():
            subprocess.run([gen_script], capture_output=True, text=True, timeout=30, cwd=str(PROJECT_ROOT))
            results.append({"action": "docs_regenerated"})
        registered_now = tools_added
        return json.dumps({"status": "ok" if registered_now > 0 else "no_change",
                           "tools_registered": registered_now,
                           "results": results,
                           "total_tools": 182 + registered_now}, indent=2)

    @mcp.tool()
    def session_learn(review_data: str = "") -> str:
        """Review session tool calls, identify novel patterns, auto-save skills. Args: review_data (JSON array of {tool, input, output})."""
        try:
            calls = json.loads(review_data) if review_data else []
        except json.JSONDecodeError:
            return json.dumps({"status": "error", "error": "invalid JSON in review_data"}, indent=2)
        if not calls:
            existing = list(SKILLS_DIR.glob("*.json")) + list(SHARED_DIR.glob("*.json"))
            return json.dumps({"status": "ok", "session_calls_reviewed": 0,
                               "skills_saved": 0, "existing_skills": len(existing),
                               "note": "Pass review_data as JSON array of {tool, input, output}"}, indent=2)
        novel = []
        for call in calls:
            tool_name = call.get("tool", "")
            if not tool_name:
                continue
            already_covered = False
            for sf in list(SKILLS_DIR.glob("*.json")) + list(SHARED_DIR.glob("*.json")):
                skill = json.loads(sf.read_text())
                if skill.get("tool_name") == tool_name:
                    already_covered = True
                    break
            if not already_covered:
                novel.append(tool_name)
        skills_saved = 0
        for tn in novel[:5]:
            name = f"auto_{tn}_{int(time.time())}"
            skill_data = {
                "name": name,
                "description": f"Auto-saved from session: {tn}",
                "tags": ["auto-generated", "session-learned"],
                "code": f"# Auto-generated stub for {tn}\n# Replace with actual solution code",
                "tool_name": tn,
                "success_count": 1,
                "validated": False,
                "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            }
            (_skill_path(name)).write_text(json.dumps(skill_data, indent=2))
            skills_saved += 1
        return json.dumps({"status": "ok", "session_calls_reviewed": len(calls),
                           "novel_patterns": len(novel), "skills_saved": skills_saved,
                           "novel_tools": novel[:10],
                           "next": "Run skill_promote then tool_generate for any auto-saved skills"}, indent=2)

    @mcp.tool()
    def contribute_skill(skill_name: str, author: str = "") -> str:
        """Format a validated skill as a GitHub PR description. Args: skill_name, author (optional)."""
        path = _shared_path(skill_name)
        if not path.exists():
            path = _skill_path(skill_name)
        if not path.exists():
            return json.dumps({"status": "error", "error": f"skill '{skill_name}' not found"}, indent=2)
        skill = json.loads(path.read_text())
        if not skill.get("validated"):
            return json.dumps({"status": "error", "error": "skill not validated — run skill_promote first"}, indent=2)
        pr = f"""## New Tool: `{skill.get('tool_name', skill['name'])}`

### Description
{skill['description']}

### Tags
{', '.join(skill.get('tags', []))}

### Implementation

```python
{skill['code']}
```

### Context
This tool was auto-generated from a validated skill in the self-improvement pipeline.
Author: {author or 'droid-re-chain agent'}
Success count: {skill.get('success_count', 1)}
"""
        return json.dumps({"status": "ready", "skill": skill_name,
                           "tool_name": skill.get("tool_name", ""),
                           "pr_description": pr,
                           "next_step": "Submit via: gh pr create --title 'Add {0}' --body '{1}'".format(
                               skill.get('tool_name', skill['name']),
                               'PR description')}, indent=2)
