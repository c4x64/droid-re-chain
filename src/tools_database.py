"""6 Offset Database tools — persist, load, remap, import/export, diff across versions."""
import os
import json
import hashlib
from pathlib import Path
from src.shared import PROJECT_ROOT

DB_DIR = PROJECT_ROOT / "offset_db"
DB_DIR.mkdir(exist_ok=True)

def _binary_hash(path: str) -> str:
    if not os.path.isfile(path):
        return ""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()[:16]

def _db_path(binary_hash: str) -> Path:
    return DB_DIR / f"{binary_hash}.json"

def _load_db(bhash: str) -> dict:
    p = _db_path(bhash)
    if p.exists():
        return json.loads(p.read_text())
    return {"hash": bhash, "offsets": {}}

def _save_db(data: dict):
    p = _db_path(data["hash"])
    p.write_text(json.dumps(data, indent=2))

def register(mcp):

    @mcp.tool()
    def db_save_offset(binary_path: str, method_name: str, offset: str, notes: str = "") -> str:
        """Persist a confirmed offset by binary hash + method name. Args: binary_path, method_name, offset (hex), notes."""
        bhash = _binary_hash(binary_path)
        if not bhash:
            return "ERROR: binary not found"
        db = _load_db(bhash)
        db["offsets"][method_name] = {"offset": offset, "notes": notes, "binary": binary_path}
        _save_db(db)
        return json.dumps({"hash": bhash, "method": method_name, "offset": offset, "total_saved": len(db["offsets"])}, indent=2)

    @mcp.tool()
    def db_load_offsets(binary_path: str) -> str:
        """Retrieve all saved offsets for a binary. Args: binary_path."""
        bhash = _binary_hash(binary_path)
        if not bhash:
            return "ERROR: binary not found"
        db = _load_db(bhash)
        if not db["offsets"]:
            return f"No offsets saved for hash {bhash}"
        return json.dumps(db, indent=2)

    @mcp.tool()
    def db_remap_offsets(old_binary: str, new_binary: str) -> str:
        """Re-resolve saved method names in a new binary version by signature matching. Args: old_binary, new_binary."""
        old_hash = _binary_hash(old_binary)
        new_hash = _binary_hash(new_binary)
        if not old_hash or not new_hash:
            return "ERROR: one or both binaries not found"
        if old_hash == new_hash:
            return "Binaries are identical — no remapping needed"
        old_db = _load_db(old_hash)
        if not old_db["offsets"]:
            return "No offsets in old binary to remap"
        new_db = _load_db(new_hash)
        new_db["remapped_from"] = old_hash
        remapped = 0
        for method, entry in old_db["offsets"].items():
            if method not in new_db["offsets"]:
                new_db["offsets"][method] = {"offset": "UNRESOLVED", "notes": entry.get("notes", "") + " [remapped]", "binary": new_binary}
                remapped += 1
        _save_db(new_db)
        return json.dumps({"old_hash": old_hash, "new_hash": new_hash, "total_carried": len(old_db["offsets"]),
                           "remapped": remapped, "resolved": len(old_db["offsets"]) - remapped}, indent=2)

    @mcp.tool()
    def db_export_json(binary_path: str) -> str:
        """Export offset database as JSON. Args: binary_path."""
        bhash = _binary_hash(binary_path)
        if not bhash:
            return "ERROR: binary not found"
        db = _load_db(bhash)
        if not db["offsets"]:
            return "{}"
        return json.dumps(db, indent=2)

    @mcp.tool()
    def db_import_json(json_data: str) -> str:
        """Import offsets from JSON string. Args: json_data (raw JSON string)."""
        try:
            data = json.loads(json_data)
        except json.JSONDecodeError as e:
            return f"ERROR: invalid JSON: {e}"
        if "hash" not in data or "offsets" not in data:
            return "ERROR: JSON must contain 'hash' and 'offsets' keys"
        _save_db(data)
        return json.dumps({"hash": data["hash"], "imported": len(data["offsets"]),
                           "methods": list(data["offsets"].keys())[:20]}, indent=2)

    @mcp.tool()
    def db_diff_versions(binary_a: str, binary_b: str) -> str:
        """Compare offsets between two binary versions. Args: binary_a, binary_b."""
        hash_a = _binary_hash(binary_a)
        hash_b = _binary_hash(binary_b)
        if not hash_a or not hash_b:
            return "ERROR: one or both binaries not found"
        db_a = _load_db(hash_a)
        db_b = _load_db(hash_b)
        only_in_a = set(db_a["offsets"]) - set(db_b["offsets"])
        only_in_b = set(db_b["offsets"]) - set(db_a["offsets"])
        changed = {}
        for method in set(db_a["offsets"]) & set(db_b["offsets"]):
            if db_a["offsets"][method].get("offset") != db_b["offsets"][method].get("offset"):
                changed[method] = {"old": db_a["offsets"][method]["offset"], "new": db_b["offsets"][method]["offset"]}
        return json.dumps({"binary_a": binary_a, "binary_b": binary_b,
                           "total_in_a": len(db_a["offsets"]), "total_in_b": len(db_b["offsets"]),
                           "only_in_a": list(only_in_a)[:20], "only_in_b": list(only_in_b)[:20],
                           "changed": changed, "unchanged": len(set(db_a["offsets"]) & set(db_b["offsets"])) - len(changed)}, indent=2)