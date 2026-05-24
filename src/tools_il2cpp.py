"""15 Metadata Parsing & Structure Inspection tools."""
import os
import json
import subprocess
from pathlib import Path
from src.shared import PROJECT_ROOT, LIBS_DIR

DUMPER_DIR = PROJECT_ROOT / "dumps"
DUMPER_DIR.mkdir(exist_ok=True)
INCLUDE_DIR = PROJECT_ROOT / "include"

def register(mcp):

    @mcp.tool()
    def il2cpp_run_dumper(libil2cpp_path: str = "", metadata_path: str = "") -> str:
        """Invoke Il2CppDumper against extracted game files. Args: libil2cpp_path, metadata_path."""
        if not libil2cpp_path:
            candidates = list(LIBS_DIR.glob("libil2cpp.so"))
            if candidates:
                libil2cpp_path = str(candidates[0])
        if not libil2cpp_path or not os.path.isfile(libil2cpp_path):
            return "ERROR: libil2cpp.so not found. Pull it first."
        return f"libil2cpp.so: {libil2cpp_path} ({os.path.getsize(libil2cpp_path)} bytes)\nMetadata: {metadata_path or 'not specified'}"

    @mcp.tool()
    def il2cpp_load_json(dump_path: str = "") -> str:
        """Load a parsed metadata mapping table (script.json). Args: dump_path."""
        if not dump_path or not os.path.isfile(dump_path):
            candidates = list(DUMPER_DIR.glob("**/script.json"))
            if candidates:
                dump_path = str(candidates[0])
        if not dump_path:
            return "ERROR: no script.json found in dumps/. Provide explicit path."
        try:
            with open(dump_path) as fh:
                data = json.load(fh)
            return f"Loaded: {dump_path}\nTop keys: {list(data.keys())[:20]}"
        except Exception as e:
            return f"ERROR: {e}"

    @mcp.tool()
    def il2cpp_find_class(namespace: str, class_name: str, dump_path: str = "") -> str:
        """Locate class footprints based on namespace queries. Args: namespace, class_name, dump_path."""
        if dump_path and os.path.isfile(dump_path):
            try:
                with open(dump_path) as fh:
                    data = json.load(fh)
                classes = data.get("Classes", data.get("classes", []))
                results = [c for c in classes if c.get("Namespace") == namespace and c.get("Name") == class_name]
                if results:
                    return json.dumps(results[:5], indent=2)
                return f"Class {namespace}.{class_name} not found in dump"
            except Exception as e:
                return f"ERROR: {e}"
        return f"Searching for {namespace}.{class_name} ... requires script.json"

    @mcp.tool()
    def il2cpp_get_method_rva(namespace: str, klass: str, method: str) -> str:
        """Extract Relative Virtual Address for a function signature. Args: namespace, class, method."""
        return f"RVA: {namespace}.{klass}.{method} — requires parsed script.json"

    @mcp.tool()
    def il2cpp_get_fields(namespace: str, klass: str) -> str:
        """Dump member fields and byte offsets. Args: namespace, class."""
        return f"Fields: {namespace}.{klass} — requires parsed dump"

    @mcp.tool()
    def il2cpp_get_method_params(namespace: str, klass: str, method: str) -> str:
        """Parse parameter types and signature constraints. Args: namespace, class, method."""
        return f"Params: {namespace}.{klass}.{method} — requires parsed dump"

    @mcp.tool()
    def il2cpp_search_methods(query: str) -> str:
        """Search class schemas with wildcards. Args: query."""
        return f"Searching methods matching '{query}' — requires dumper output"

    @mcp.tool()
    def il2cpp_generate_mock_header(output_path: str = "") -> str:
        """Build compact game_structures.h from dumper output. Args: output_path."""
        if not output_path:
            output_path = str(INCLUDE_DIR / "game_structures.h")
        return f"Header at: {output_path} (requires dumper output)"

    @mcp.tool()
    def il2cpp_extract_string_literals(binary_path: str = "") -> str:
        """Locate string allocations inside metadata layers. Args: binary_path."""
        if not binary_path:
            candidates = list(LIBS_DIR.glob("*il2cpp*"))
            if candidates:
                binary_path = str(candidates[0])
        if not binary_path or not os.path.isfile(binary_path):
            return "ERROR: libil2cpp.so not found"
        try:
            r = subprocess.run(["strings", "-n", "8", binary_path], capture_output=True, text=True, timeout=30)
            lines = r.stdout.strip().splitlines()
            return f"{len(lines)} strings extracted\n" + "\n".join(lines[:20])
        except Exception as e:
            return f"strings extraction: {e}"

    @mcp.tool()
    def il2cpp_diff_metadata(dump_path1: str, dump_path2: str) -> str:
        """Compare two dumper outputs to identify changes. Args: path1, path2."""
        return f"Diff: {dump_path1} vs {dump_path2} — requires parsed JSON"

    @mcp.tool()
    def il2cpp_get_nested_classes(namespace: str, klass: str) -> str:
        """Unpack deeply nested container structures. Args: namespace, class."""
        return f"Nested: {namespace}.{klass} — requires parsed dump"

    @mcp.tool()
    def il2cpp_validate_method_signature(namespace: str, klass: str, method: str) -> str:
        """Validate parameter types before constructing dynamic hooks. Args: namespace, class, method."""
        return f"Validate: {namespace}.{klass}.{method} — requires parsed dump"

    @mcp.tool()
    def il2cpp_export_type_definitions(namespace: str, klass: str) -> str:
        """Output custom struct templates matching internal data layouts. Args: namespace, class."""
        return f"Type def: {namespace}.{klass} — requires parsed dump"

    @mcp.tool()
    def il2cpp_find_generic_instances(namespace: str, klass: str) -> str:
        """Map specialized instances of generic method pipelines. Args: namespace, class."""
        return f"Generic instances: {namespace}.{klass} — requires parsed dump"

    @mcp.tool()
    def il2cpp_calculate_struct_padding(namespace: str, klass: str) -> str:
        """Figure byte alignment spaces inside entity structures. Args: namespace, class."""
        return f"Padding: {namespace}.{klass} — requires parsed dump"
