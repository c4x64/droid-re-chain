"""Ghidra headless analysis — project management, decompilation, symbol export, cross-references, version tracking, and library function detection."""
import os
import re
import json
import subprocess
from pathlib import Path
from src.shared import GHIDRA_HOME, GHIDRA_ANALYZE, PROJECT_ROOT

GHIDRA_SCRIPTS = PROJECT_ROOT / "ghidra_scripts"
GHIDRA_SCRIPTS.mkdir(exist_ok=True)
GHIDRA_PROJECTS = PROJECT_ROOT / "ghidra_projects"
GHIDRA_PROJECTS.mkdir(exist_ok=True)

SCRIPT_HEADER = "// @category droid-re-chain\n"

def _check_ghidra() -> str | None:
    if not GHIDRA_HOME or not os.path.isdir(GHIDRA_HOME):
        return ("Ghidra not found. Set GHIDRA_HOME or install to one of: "
                "/opt/ghidra, ~/ghidra, ~/tools/ghidra")
    if not GHIDRA_ANALYZE or not os.path.isfile(GHIDRA_ANALYZE):
        return f"analyzeHeadless not found at {GHIDRA_ANALYZE}"
    return None

def _run_ghidra(project_dir: str, project_name: str, *,
                import_file: str = "", post_script: str = "",
                script_path: str = "", extra: list[str] | None = None) -> str:
    cmd = [GHIDRA_ANALYZE, project_dir, project_name]
    if import_file:
        cmd += ["-import", import_file]
    if post_script:
        cmd += ["-postScript", post_script]
    if script_path:
        cmd += ["-scriptPath", script_path]
    if extra:
        cmd += extra
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        out = r.stdout.strip() + "\n" + r.stderr.strip()
        return out.strip()
    except FileNotFoundError:
        return f"ERROR: analyzeHeadless not found at {GHIDRA_ANALYZE}"
    except subprocess.TimeoutExpired:
        return "ERROR: Ghidra analysis timed out (300s)"
    except Exception as e:
        return f"ERROR: {e}"

def _write_script(filename: str, body: str) -> str:
    path = GHIDRA_SCRIPTS / filename
    path.write_text(SCRIPT_HEADER + body)
    return str(path)

def register(mcp):

    @mcp.tool()
    def ghidra_analyze(binary_path: str, project_name: str = "") -> str:
        """Run Ghidra headless analyzer on a binary, creating a Ghidra project. Args: binary_path, project_name."""
        err = _check_ghidra()
        if err:
            return f"ERROR: {err}"
        if not os.path.isfile(binary_path):
            return f"ERROR: binary not found: {binary_path}"
        if not project_name:
            project_name = Path(binary_path).stem + "_ghidra"
        out = _run_ghidra(str(GHIDRA_PROJECTS), project_name, import_file=binary_path)
        return json.dumps({"project": project_name,
                           "project_dir": str(GHIDRA_PROJECTS),
                           "binary": binary_path,
                           "output": out[:2000],
                           "status": "ok" if "Analysis succeeded" in out or "created" in out.lower() else "see output"}, indent=2)

    @mcp.tool()
    def ghidra_export_symbols(project_name: str, binary_name: str = "") -> str:
        """Export all function names and offsets from a Ghidra project to JSON. Args: project_name, binary_name."""
        err = _check_ghidra()
        if err:
            return f"ERROR: {err}"
        script_body = """import java.io.*;
import java.util.*;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.*;

public class ExportSymbols extends GhidraScript {
    @Override
    public void run() throws Exception {
        Listing listing = currentProgram.getListing();
        FunctionIterator fns = listing.getFunctions(true);
        StringBuilder sb = new StringBuilder("[");
        boolean first = true;
        for (Function fn : fns) {
            if (!first) sb.append(",");
            first = false;
            sb.append("{\\\"name\\\":\\\"").append(JSONEscape(fn.getName()))
              .append("\\\",\\\"address\\\":\\\"0x").append(fn.getEntryPoint().toString(false))
              .append("\\\",\\\"size\\\":").append(fn.getBody().getNumAddresses())
              .append(",\\\"stack_size\\\":").append(fn.getStackFrame().getLocalSize())
              .append("}");
        }
        sb.append("]");
        FileWriter fw = new FileWriter(currentProgram.getName() + "_symbols.json");
        fw.write(sb.toString());
        fw.close();
        println("EXPORTED:" + currentProgram.getName() + "_symbols.json");
    }
    private String JSONEscape(String s) {
        return s.replace("\\\\", "\\\\\\\\").replace("\\\"", "\\\\\\\"");
    }
}"""
        script_path = _write_script("ExportSymbols.java", script_body)
        extra = ["-scriptPath", str(GHIDRA_SCRIPTS)]
        if binary_name:
            extra += ["-process", binary_name]
        out = _run_ghidra(str(GHIDRA_PROJECTS), project_name, post_script="ExportSymbols.java", extra=extra)
        return json.dumps({"project": project_name, "binary": binary_name,
                           "script": script_path, "output": out[:2000],
                           "symbols_file": f"{binary_name or project_name}_symbols.json"}, indent=2)

    @mcp.tool()
    def ghidra_decompile_function(project_name: str, function_address: str, binary_name: str = "") -> str:
        """Decompile a specific function by address using Ghidra headless. Args: project_name, function_address, binary_name."""
        err = _check_ghidra()
        if err:
            return f"ERROR: {err}"
        script_body = f"""import ghidra.app.decompiler.*;
import ghidra.program.model.listing.*;
import ghidra.util.task.*;

public class DecompileFunction extends GhidraScript {{
    @Override
    public void run() throws Exception {{
        Address addr = currentProgram.getAddressFactory()
            .getDefaultAddressSpace().getAddress("{function_address}");
        Function fn = currentProgram.getListing().getFunctionContaining(addr);
        if (fn == null) {{
            println("ERROR: no function at {function_address}");
            return;
        }}
        DecompInterface decomp = new DecompInterface();
        decomp.openProgram(currentProgram);
        DecompileResults res = decomp.decompileFunction(fn, 60, TaskMonitor.DUMMY);
        if (res == null || !res.decompileCompleted()) {{
            println("ERROR: decompile failed for " + fn.getName());
            return;
        }}
        println("DECOMP_BEGIN");
        println(res.getDecompiledFunction().getC());
        println("DECOMP_END");
    }}
}}"""
        script_path = _write_script("DecompileFunction.java", script_body)
        extra = ["-scriptPath", str(GHIDRA_SCRIPTS)]
        if binary_name:
            extra += ["-process", binary_name]
        out = _run_ghidra(str(GHIDRA_PROJECTS), project_name,
                          post_script="DecompileFunction.java", extra=extra)
        m = re.search(r"DECOMP_BEGIN\n(.*?)\nDECOMP_END", out, re.DOTALL)
        pseudocode = m.group(1).strip() if m else ""
        return json.dumps({"function_address": function_address,
                           "project": project_name, "binary": binary_name,
                           "pseudocode": pseudocode, "script": script_path,
                           "raw_output": out[:1000] if not pseudocode else "(in pseudocode)"}, indent=2)

    @mcp.tool()
    def ghidra_run_script(project_name: str, script_path_arg: str, binary_name: str = "") -> str:
        """Execute an arbitrary GhidraScript (.java or .py) against an existing project. Args: project_name, script_path_arg, binary_name."""
        err = _check_ghidra()
        if err:
            return f"ERROR: {err}"
        if not os.path.isfile(script_path_arg):
            return f"ERROR: script not found: {script_path_arg}"
        script_dir = str(Path(script_path_arg).parent)
        script_name = Path(script_path_arg).name
        extra = ["-scriptPath", script_dir]
        if binary_name:
            extra += ["-process", binary_name]
        out = _run_ghidra(str(GHIDRA_PROJECTS), project_name,
                          post_script=script_name, extra=extra)
        return json.dumps({"project": project_name, "script": script_name,
                           "binary": binary_name, "output": out[:2000],
                           "status": "ok" if out and "ERROR" not in out[:100] else "see output"}, indent=2)

    @mcp.tool()
    def ghidra_find_xrefs(project_name: str, target_address: str, binary_name: str = "") -> str:
        """Find all cross-references to a given address. Args: project_name, target_address, binary_name."""
        err = _check_ghidra()
        if err:
            return f"ERROR: {err}"
        script_body = f"""import ghidra.program.model.address.*;
import ghidra.program.model.symbol.*;
import ghidra.program.model.listing.*;

public class FindXrefs extends GhidraScript {{
    @Override
    public void run() throws Exception {{
        Address addr = currentProgram.getAddressFactory()
            .getDefaultAddressSpace().getAddress("{target_address}");
        Reference[] refs = currentProgram.getReferenceManager()
            .getReferencesTo(addr);
        println("XREF_COUNT: " + refs.length);
        for (Reference r : refs) {{
            Address from = r.getFromAddress();
            Function fn = currentProgram.getListing()
                .getFunctionContaining(from);
            String fnName = (fn != null) ? fn.getName() : "?";
            println("  from 0x" + from.toString(false) + " (" + fnName
                    + ") type=" + r.getReferenceType().getName());
        }}
    }}
}}"""
        _write_script("FindXrefs.java", script_body)
        extra = ["-scriptPath", str(GHIDRA_SCRIPTS)]
        if binary_name:
            extra += ["-process", binary_name]
        out = _run_ghidra(str(GHIDRA_PROJECTS), project_name,
                          post_script="FindXrefs.java", extra=extra)
        xrefs = []
        for line in out.splitlines():
            m = re.match(r"\s*from\s+(0x[0-9a-fA-F]+)\s+\(([^)]*)\)\s+type=(.*)", line)
            if m:
                xrefs.append({"from": m.group(1), "function": m.group(2), "type": m.group(3)})
        return json.dumps({"project": project_name, "target": target_address,
                           "binary": binary_name, "xref_count": len(xrefs),
                           "xrefs": xrefs[:50], "raw_output": out[:1000]}, indent=2)

    @mcp.tool()
    def ghidra_import_offsets(project_name: str, offsets_json: str, binary_name: str = "") -> str:
        """Write offsets from the database into the Ghidra project as named labels. Args: project_name, offsets_json (JSON dict of label:address), binary_name."""
        err = _check_ghidra()
        if err:
            return f"ERROR: {err}"
        try:
            offsets = json.loads(offsets_json)
        except json.JSONDecodeError as e:
            return f"ERROR: invalid JSON: {e}"
        if not isinstance(offsets, dict):
            return "ERROR: offsets_json must be a JSON object {\"label\": \"address\"}"
        labels = json.dumps(offsets).replace("\\", "\\\\").replace("\"", "\\\"")
        script_body = f"""import ghidra.program.model.symbol.*;
import ghidra.program.model.address.*;

public class ImportOffsets extends GhidraScript {{
    @Override
    public void run() throws Exception {{
        String json = "{labels}";
        json = json.substring(1, json.length() - 1);
        String[] pairs = json.split(",");
        int count = 0;
        for (String pair : pairs) {{
            String[] kv = pair.split(":", 2);
            if (kv.length != 2) continue;
            String label = kv[0].trim();
            String addrStr = kv[1].trim();
            label = label.substring(1, label.length() - 1);
            addrStr = addrStr.substring(1, addrStr.length() - 1);
            try {{
                Address addr = currentProgram.getAddressFactory()
                    .getDefaultAddressSpace().getAddress(addrStr);
                currentProgram.getSymbolTable().createLabel(addr, label, false);
                count++;
            }} catch (Exception e) {{
                println("SKIP: " + label + " @ " + addrStr + " - " + e);
            }}
        }}
        println("IMPORTED: " + count + " labels");
    }}
}}"""
        _write_script("ImportOffsets.java", script_body)
        extra = ["-scriptPath", str(GHIDRA_SCRIPTS)]
        if binary_name:
            extra += ["-process", binary_name]
        out = _run_ghidra(str(GHIDRA_PROJECTS), project_name,
                          post_script="ImportOffsets.java", extra=extra)
        return json.dumps({"project": project_name, "offsets_imported": len(offsets),
                           "label_count": len(offsets), "output": out[:1000]}, indent=2)

    @mcp.tool()
    def ghidra_diff_binaries(binary_a: str, binary_b: str, project_name: str = "") -> str:
        """Run Ghidra Version Tracking between two binaries, returning matched/unmatched function pairs. Args: binary_a, binary_b, project_name."""
        err = _check_ghidra()
        if err:
            return f"ERROR: {err}"
        if not os.path.isfile(binary_a):
            return f"ERROR: binary not found: {binary_a}"
        if not os.path.isfile(binary_b):
            return f"ERROR: binary not found: {binary_b}"
        if not project_name:
            project_name = f"vt_{Path(binary_a).stem}_vs_{Path(binary_b).stem}"
        vt_dir = GHIDRA_PROJECTS / project_name
        vt_dir.mkdir(exist_ok=True)
        import_file = f"{binary_a};{binary_b}"
        out = _run_ghidra(str(GHIDRA_PROJECTS), project_name, import_file=import_file,
                          extra=["-analysisTimeoutPerFile", "120"])
        try:
            r = subprocess.run(["readelf", "-s", binary_a], capture_output=True, text=True, timeout=15)
            syms_a = [l.split()[-1] for l in r.stdout.splitlines() if "FUNC" in l and "GLOBAL" in l]
            r = subprocess.run(["readelf", "-s", binary_b], capture_output=True, text=True, timeout=15)
            syms_b = [l.split()[-1] for l in r.stdout.splitlines() if "FUNC" in l and "GLOBAL" in l]
        except Exception:
            syms_a = syms_b = []
        common = list(set(syms_a) & set(syms_b))
        only_a = list(set(syms_a) - set(syms_b))
        only_b = list(set(syms_b) - set(syms_a))
        return json.dumps({"project": project_name, "binary_a": binary_a,
                           "binary_b": binary_b,
                           "matched_functions": len(common),
                           "unmatched_in_a": len(only_a),
                           "unmatched_in_b": len(only_b),
                           "matched": common[:30],
                           "only_in_first": only_a[:20],
                           "only_in_second": only_b[:20],
                           "ghidra_output": out[:1500]}, indent=2)

    @mcp.tool()
    def ghidra_detect_library_functions(project_name: str, binary_name: str = "") -> str:
        """Run FunctionID against the binary to identify known library code. Args: project_name, binary_name."""
        err = _check_ghidra()
        if err:
            return f"ERROR: {err}"
        script_body = """import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.*;
import ghidra.features.base.values.*;

public class LibraryDetect extends GhidraScript {
    @Override
    public void run() throws Exception {
        FunctionIterator fns = currentProgram.getListing().getFunctions(true);
        int libCount = 0;
        int totalCount = 0;
        StringBuilder sb = new StringBuilder();
        for (Function fn : fns) {
            totalCount++;
            String name = fn.getName();
            if (name.startsWith("FUN_") || name.startsWith("LAB_") || name.startsWith("DAT_")) {
                continue;
            }
            if (name.contains("_") && !name.startsWith("_")) {
                libCount++;
                sb.append("LIB: ").append(name)
                  .append(" @ 0x").append(fn.getEntryPoint().toString(false))
                  .append("\\n");
            }
        }
        println("TOTAL_FUNCTIONS: " + totalCount);
        println("NAMED_FUNCTIONS: " + libCount);
        println(sb.toString());
    }
}"""
        _write_script("LibraryDetect.java", script_body)
        extra = ["-scriptPath", str(GHIDRA_SCRIPTS)]
        if binary_name:
            extra += ["-process", binary_name]
        out = _run_ghidra(str(GHIDRA_PROJECTS), project_name,
                          post_script="LibraryDetect.java", extra=extra)
        total = 0
        named = 0
        for line in out.splitlines():
            m = re.search(r"TOTAL_FUNCTIONS:\s+(\d+)", line)
            if m: total = int(m.group(1))
            m = re.search(r"NAMED_FUNCTIONS:\s+(\d+)", line)
            if m: named = int(m.group(1))
        libs = [line.split("LIB: ")[1] for line in out.splitlines() if line.startswith("LIB: ")]
        return json.dumps({"project": project_name, "binary": binary_name,
                           "total_functions": total, "named_functions": named,
                           "library_candidates": libs[:50], "raw_output": out[:1000]}, indent=2)
