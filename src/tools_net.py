"""4 Network Analysis tools — HTTPS interception, traffic dump, endpoint discovery, protobuf decode."""
import os
import re
import json
import subprocess
from pathlib import Path
from src.shared import PROJECT_ROOT, _adb_shell, ADB_BINARY, ADB_HOST, ADB_PORT

MITM_DIR = PROJECT_ROOT / "mitm_data"
MITM_DIR.mkdir(exist_ok=True)

def register(mcp):

    @mcp.tool()
    def net_intercept_https(mitm_port: str = "8080") -> str:
        """Configure device to route through mitmproxy. Args: mitm_port (default: 8080)."""
        steps = []
        steps.append(f"1. Start mitmproxy: mitmproxy -p {mitm_port}")
        steps.append(f"2. Push CA cert to device:")
        steps.append(f"   {ADB_BINARY} push ~/.mitmproxy/mitmproxy-ca-cert.cer /sdcard/")
        steps.append(f"3. Install CA cert (Android 7+ needs root or MoveCert system):")
        steps.append(f"   {ADB_BINARY} shell su -c 'cp /sdcard/mitmproxy-ca-cert.cer /system/etc/security/cacerts/ && chmod 644 /system/etc/security/cacerts/mitmproxy-ca-cert.cer'")
        steps.append(f"4. Set proxy on device WiFi (manual proxy: {ADB_HOST}:{mitm_port})")
        steps.append(f"   Or use adb: {ADB_BINARY} shell settings put global http_proxy {ADB_HOST}:{mitm_port}")
        tips = []
        tips.append("To capture HTTPS, ensure mitmproxy CA is trusted by the app's network security config.")
        tips.append("Some apps use SSL pinning — use bypass_ssl_pinning or frida_hook_instance_method to bypass.")
        return json.dumps({"steps": steps, "tips": tips, "mitm_port": mitm_port, "device": f"{ADB_HOST}:{ADB_PORT}"}, indent=2)

    @mcp.tool()
    def net_dump_traffic(mitm_log: str = "") -> str:
        """Parse captured mitmproxy/flows file and return HTTP summary. Args: path to mitmproxy dump file."""
        if mitm_log and os.path.isfile(mitm_log):
            try:
                r = subprocess.run(["mitmdump", "--read-flows", mitm_log, "--set", "flow_detail=1"],
                                   capture_output=True, text=True, timeout=30)
                text = r.stdout or r.stderr
            except FileNotFoundError:
                try:
                    r = subprocess.run(["mitmproxy", "--read-flows", mitm_log],
                                       capture_output=True, text=True, timeout=30)
                    text = r.stdout or r.stderr
                except FileNotFoundError:
                    text = ""
        else:
            text = _adb_shell("cat /sdcard/mitm_log.txt 2>/dev/null || echo 'No mitm log on device'", su=False)
        requests = []
        for line in text.splitlines():
            if "GET " in line or "POST " in line or "PUT " in line or "DELETE " in line:
                parts = line.strip().split()
                if len(parts) >= 3:
                    requests.append({"method": parts[0], "url": parts[1], "status": parts[-1] if len(parts) > 2 else "?"})
        return json.dumps({"source": mitm_log or "device log", "total_requests": len(requests),
                           "requests": requests[:50]}, indent=2)

    @mcp.tool()
    def net_find_endpoints(binary_path: str) -> str:
        """Scan binary for hardcoded API URLs and endpoints. Args: binary_path."""
        if not os.path.isfile(binary_path):
            return f"ERROR: file not found: {binary_path}"
        try:
            with open(binary_path, "rb") as f:
                data = f.read()
        except Exception as e:
            return f"ERROR: {e}"
        strings = []
        current = b""
        for byte in data:
            if 32 <= byte < 127:
                current += bytes([byte])
            else:
                if len(current) >= 6:
                    strings.append(current.decode("ascii", errors="replace"))
                current = b""
        url_pat = re.compile(r'https?://[^\s"\'<>]+')
        api_pat = re.compile(r'/api/[-a-zA-Z0-9/._~%]+')
        host_pat = re.compile(r'([a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}')
        found = {"urls": [], "api_paths": [], "hosts": []}
        seen = {"urls": set(), "api_paths": set(), "hosts": set()}
        for s in strings:
            for m in url_pat.finditer(s):
                v = m.group()
                if v not in seen["urls"]:
                    seen["urls"].add(v)
                    found["urls"].append(v)
            for m in api_pat.finditer(s):
                v = m.group()
                if v not in seen["api_paths"]:
                    seen["api_paths"].add(v)
                    found["api_paths"].append(v)
            for m in host_pat.finditer(s):
                v = m.group()
                if v not in seen["hosts"] and v not in ("localhost", "android"):
                    seen["hosts"].add(v)
                    found["hosts"].append(v)
        return json.dumps({"binary": binary_path, "found": found,
                           "totals": {k: len(v) for k, v in found.items()}}, indent=2)

    @mcp.tool()
    def net_decode_protobuf(hex_data: str) -> str:
        """Attempt to decode captured protobuf payload from hex string. Args: hex_data (raw hex)."""
        try:
            data = bytes.fromhex(hex_data)
        except ValueError:
            return "ERROR: invalid hex string"
        try:
            import google.protobuf as _pb
            from google.protobuf import descriptor_pb2, json_format
            tmp = descriptor_pb2.DescriptorProto()
            tmp.ParseFromString(data)
            return "Protobuf descriptor detected:\n" + str(tmp)[:2000]
        except Exception:
            pass
        decoded = []
        pos = 0
        while pos < len(data) and len(decoded) < 50:
            try:
                tag = data[pos]
                field_num = tag >> 3
                wire_type = tag & 0x07
                pos += 1
                if wire_type == 0:
                    value = 0
                    shift = 0
                    while pos < len(data):
                        byte = data[pos]
                        value |= (byte & 0x7F) << shift
                        shift += 7
                        pos += 1
                        if not (byte & 0x80):
                            break
                    decoded.append({"field": field_num, "type": "varint", "value": value})
                elif wire_type == 2:
                    length = 0
                    shift = 0
                    while pos < len(data):
                        byte = data[pos]
                        length |= (byte & 0x7F) << shift
                        shift += 7
                        pos += 1
                        if not (byte & 0x80):
                            break
                    if pos + length > len(data):
                        length = len(data) - pos
                    text = data[pos:pos+length]
                    try:
                        text_val = text.decode('utf-8')
                        decoded.append({"field": field_num, "type": "string", "value": text_val})
                    except UnicodeDecodeError:
                        decoded.append({"field": field_num, "type": "bytes", "value": text.hex()})
                    pos += length
                else:
                    decoded.append({"field": field_num, "type": f"wire_type_{wire_type}", "value": data[pos:pos+4].hex()})
                    pos += 4
            except (IndexError, ValueError) as e:
                decoded.append({"error": str(e), "pos": hex(pos)})
                break
        return json.dumps({"hex_length": len(hex_data) // 2, "fields_decoded": len(decoded),
                           "fields": decoded}, indent=2)