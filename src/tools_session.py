"""4 Session & Replay tools — snapshot, restore, replay, export."""
import os
import json
import time
from pathlib import Path
from src.shared import PROJECT_ROOT

SESSION_DIR = PROJECT_ROOT / "sessions"
SESSION_DIR.mkdir(exist_ok=True)

def register(mcp):

    @mcp.tool()
    def session_save(name: str = "") -> str:
        """Snapshot current session state (loaded offsets, binary under analysis). Args: name (optional)."""
        from src.tools_database import DB_DIR
        ts = time.strftime("%Y%m%dT%H%M%S")
        slug = name.replace(" ", "_") if name else f"session_{ts}"
        snapshot = {
            "name": slug,
            "created": ts,
            "offset_db_files": [str(f.relative_to(DB_DIR)) for f in DB_DIR.glob("*.json") if f.is_file()],
            "libs": [str(f.name) for f in PROJECT_ROOT.glob("libs/*.so")],
        }
        path = SESSION_DIR / f"{slug}.json"
        path.write_text(json.dumps(snapshot, indent=2))
        return json.dumps({"session": slug, "path": str(path), "tool_calls": 0, "offsets": len(snapshot["offset_db_files"])}, indent=2)

    @mcp.tool()
    def session_restore(session_name: str) -> str:
        """Restore a previous session state. Args: session_name (filename without .json)."""
        path = SESSION_DIR / f"{session_name}.json"
        if not path.exists():
            existing = [f.stem for f in SESSION_DIR.glob("*.json")]
            return f"ERROR: session '{session_name}' not found. Available: {existing[:10]}"
        snapshot = json.loads(path.read_text())
        return json.dumps({"restored": session_name, "offset_db_files": snapshot.get("offset_db_files", []),
                           "libs_present": snapshot.get("libs", []), "note": "Snapshot loaded. Use db_load_offsets to restore offset data."}, indent=2)

    @mcp.tool()
    def session_replay(session_name: str) -> str:
        """Replay registered offsets against the current binary in libs/. Args: session_name."""
        path = SESSION_DIR / f"{session_name}.json"
        if not path.exists():
            return f"ERROR: session '{session_name}' not found"
        snapshot = json.loads(path.read_text())
        from src.tools_database import _binary_hash, _load_db
        results = []
        for lib in snapshot.get("libs", []):
            lib_path = PROJECT_ROOT / "libs" / lib
            if lib_path.exists():
                bhash = _binary_hash(str(lib_path))
                db = _load_db(bhash)
                results.append({"library": lib, "hash": bhash, "offsets_found": len(db.get("offsets", {}))})
        return json.dumps({"session": session_name, "replay_results": results,
                           "total_offsets": sum(r["offsets_found"] for r in results)}, indent=2)

    @mcp.tool()
    def session_export(session_name: str) -> str:
        """Bundle session data into a shareable JSON archive. Args: session_name."""
        path = SESSION_DIR / f"{session_name}.json"
        if not path.exists():
            return f"ERROR: session '{session_name}' not found"
        snapshot = json.loads(path.read_text())
        bundle = {
            "session": snapshot,
            "offset_data": {},
        }
        from src.tools_database import DB_DIR
        for fname in snapshot.get("offset_db_files", []):
            dp = DB_DIR / fname
            if dp.exists():
                bundle["offset_data"][fname] = json.loads(dp.read_text())
        export_path = SESSION_DIR / f"{session_name}_export.json"
        export_path.write_text(json.dumps(bundle, indent=2))
        return json.dumps({"exported": str(export_path), "size_bytes": export_path.stat().st_size,
                           "sessions_included": 1, "offset_files": len(bundle["offset_data"])}, indent=2)