"""15 APK Handling & Analysis tools."""
import os
import json
import subprocess
from pathlib import Path
from src.shared import _adb_run, _adb_shell, ADB_BINARY, PROJECT_ROOT, LIBS_DIR

APK_WORK = PROJECT_ROOT / "apk_work"
APK_WORK.mkdir(exist_ok=True)

def register(mcp):

    @mcp.tool()
    def apk_pull_from_device(package: str) -> str:
        """Pull installed APK from device. Args: package name."""
        pm_path = _adb_shell(f"pm path {package}", su=False)
        if "package:" not in pm_path:
            return f"ERROR: {package} not found"
        remote = pm_path.split("package:")[1].strip()
        local = str(APK_WORK / f"{package}.apk")
        return _adb_run([ADB_BINARY, "pull", remote, local], timeout=60)

    @mcp.tool()
    def apk_extract(apk_path: str, output_dir: str = "") -> str:
        """Unzip APK and organize contents. Args: apk_path, output_dir."""
        if not output_dir:
            output_dir = str(APK_WORK / Path(apk_path).stem)
        os.makedirs(output_dir, exist_ok=True)
        r = subprocess.run(["unzip", "-o", apk_path, "-d", output_dir], capture_output=True, text=True, timeout=60)
        if r.returncode != 0:
            return f"Extract failed: {r.stderr.strip()[:500]}"
        return f"Extracted to {output_dir}\n{r.stdout.strip()[:500]}"

    @mcp.tool()
    def apk_extract_native_libs(apk_path: str, abi: str = "arm64-v8a") -> str:
        """Pull .so files from APK for specific ABI. Args: apk_path, abi."""
        import zipfile
        out = APK_WORK / f"libs_{abi}"
        out.mkdir(exist_ok=True)
        count = 0
        try:
            with zipfile.ZipFile(apk_path) as z:
                for entry in z.namelist():
                    if f"lib/{abi}/" in entry and entry.endswith(".so"):
                        z.extract(entry, str(out))
                        count += 1
            return f"Extracted {count} .so files to {out}"
        except Exception as e:
            return f"ERROR: {e}"

    @mcp.tool()
    def apk_decompile_smali(apk_path: str, output_dir: str = "") -> str:
        """Decompile APK to smali using apktool. Args: apk_path, output_dir."""
        apktool = subprocess.run(["which", "apktool"], capture_output=True, text=True)
        if apktool.returncode != 0:
            return "apktool not found. Install: https://ibotpeaches.github.io/Apktool/"
        if not output_dir:
            output_dir = str(APK_WORK / f"{Path(apk_path).stem}_smali")
        r = subprocess.run(["apktool", "d", "-f", "-o", output_dir, apk_path], capture_output=True, text=True, timeout=120)
        if r.returncode != 0:
            return f"Decompile failed: {r.stderr.strip()[:500]}"
        return f"Decompiled to {output_dir}"

    @mcp.tool()
    def apk_recompile(smali_dir: str, output_path: str = "") -> str:
        """Recompile smali to APK. Args: smali_dir, output_path."""
        apktool = subprocess.run(["which", "apktool"], capture_output=True, text=True)
        if apktool.returncode != 0:
            return "apktool not found"
        if not output_path:
            output_path = str(APK_WORK / f"{Path(smali_dir).stem}_repacked.apk")
        r = subprocess.run(["apktool", "b", "-o", output_path, smali_dir], capture_output=True, text=True, timeout=120)
        if r.returncode != 0:
            return f"Recompile failed: {r.stderr.strip()[:500]}"
        return f"Recompiled: {output_path}"

    @mcp.tool()
    def apk_sign(input_apk: str) -> str:
        """Sign APK using apksigner. Args: input_apk."""
        apksigner = subprocess.run(["which", "apksigner"], capture_output=True, text=True)
        if apksigner.returncode != 0:
            return "apksigner not found. Install Android SDK build-tools."
        r = subprocess.run(["apksigner", "sign", "--ks", os.path.expanduser("~/.android/debug.keystore"),
                           "--ks-pass", "pass:android", "--ks-key-alias", "androiddebugkey", input_apk],
                           capture_output=True, text=True, timeout=60)
        if r.returncode != 0:
            return f"Sign failed: {r.stderr.strip()[:500]}"
        return f"Signed: {input_apk}"

    @mcp.tool()
    def apk_install_patched(apk_path: str) -> str:
        """Install re-signed APK. Args: apk_path."""
        return _adb_run([ADB_BINARY, "install", "-r", apk_path], timeout=120)

    @mcp.tool()
    def patch_manifest_debuggable(apk_path: str) -> str:
        """Set android:debuggable=true in AndroidManifest.xml. Args: apk_path."""
        work = APK_WORK / f"{Path(apk_path).stem}_tmp"
        os.makedirs(work, exist_ok=True)
        apk_extract(apk_path, str(work))
        manifest = work / "AndroidManifest.xml"
        if not manifest.exists():
            return "AndroidManifest.xml not found (binary format; use apktool first)"
        content = manifest.read_text(encoding="latin-1")
        if 'android:debuggable="true"' in content:
            return "Already debuggable"
        content = content.replace('<application ', '<application android:debuggable="true" ', 1)
        manifest.write_bytes(content.encode("latin-1"))
        return f"Patched debuggable flag in {manifest}"

    @mcp.tool()
    def detect_apk_protection(apk_path: str) -> str:
        """Identify known APK protection schemes. Args: apk_path."""
        import zipfile
        signatures = {
            "libprotect.so": "Tencent Protect",
            "libsecexe.so": "Tencent Protect",
            "libtprt.so": "Tencent Protect",
            "libnesec.so": "NetEase Protect",
            "libDexHelper.so": "Baidu Protect",
            "libjiagu.so": "Qihoo 360/Jiagu",
            "libegis.so": "Egis",
            "libkkgogo.so": "Kakao Protect",
        }
        found = []
        try:
            with zipfile.ZipFile(apk_path) as z:
                names = z.namelist()
                for lib, name in signatures.items():
                    for n in names:
                        if lib in n:
                            found.append(f"{name} ({n})")
                            break
            return json.dumps({"protections": found, "count": len(found)}, indent=2) if found else "No known protection detected"
        except Exception as e:
            return f"ERROR: {e}"

    @mcp.tool()
    def apk_verify_signature(apk_path: str) -> str:
        """Check APK signing info. Args: apk_path."""
        r = subprocess.run(["apksigner", "verify", "--verbose", apk_path], capture_output=True, text=True, timeout=30)
        if r.returncode == 0:
            return r.stdout.strip()
        alt = subprocess.run(["jarsigner", "-verify", "-verbose", "-certs", apk_path], capture_output=True, text=True, timeout=30)
        if alt.returncode == 0:
            return alt.stdout.strip()[:1000]
        return "APK signature verification tools not available (apksigner/jarsigner)"

    @mcp.tool()
    def apk_get_version(apk_path: str) -> str:
        """Read versionName/versionCode from APK. Args: apk_path."""
        r = subprocess.run(["aapt2", "dump", "badging", apk_path], capture_output=True, text=True, timeout=30)
        if r.returncode == 0:
            for line in r.stdout.splitlines():
                if "versionName" in line or "versionCode" in line or "package: name" in line:
                    return line.strip()
        return "aapt2 not available. Use apk_extract + read AndroidManifest.xml"

    @mcp.tool()
    def diff_apks(old_apk: str, new_apk: str) -> str:
        """Compare two APK versions. Args: old_apk, new_apk."""
        import hashlib
        def hash_file(p):
            h = hashlib.md5()
            with open(p, "rb") as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    h.update(chunk)
            return h.hexdigest()
        old_h = hash_file(old_apk)
        new_h = hash_file(new_apk)
        old_size = os.path.getsize(old_apk)
        new_size = os.path.getsize(new_apk)
        return json.dumps({"old": {"path": old_apk, "md5": old_h, "size": old_size},
                           "new": {"path": new_apk, "md5": new_h, "size": new_size},
                           "size_diff": new_size - old_size, "same": old_h == new_h}, indent=2)

    @mcp.tool()
    def search_java_source(smali_dir: str, keyword: str) -> str:
        """Search smali for keyword. Args: smali_dir, keyword."""
        results = subprocess.run(["grep", "-rl", keyword, smali_dir], capture_output=True, text=True, timeout=30)
        if results.returncode != 0:
            return f"No files containing '{keyword}' found"
        files = results.stdout.strip().splitlines()
        return f"Found {len(files)} files containing '{keyword}':\n" + "\n".join(files[:20])

    @mcp.tool()
    def detect_ssl_pinning(apk_path_or_dir: str) -> str:
        """Scan for SSL pinning patterns. Args: apk_path or smali_dir."""
        scan_dir = apk_path_or_dir
        if os.path.isfile(apk_path_or_dir):
            scan_dir = str(APK_WORK / "scan_tmp")
            os.makedirs(scan_dir, exist_ok=True)
            apk_extract(apk_path_or_dir, scan_dir)
        patterns = ["CertificatePinner", "pinning", "TrustManager", "checkServerTrusted"]
        found = []
        for pat in patterns:
            r = subprocess.run(["grep", "-rl", pat, scan_dir], capture_output=True, text=True, timeout=30)
            if r.stdout.strip():
                found.append({"pattern": pat, "files": r.stdout.strip().splitlines()[:5]})
        return json.dumps(found, indent=2) if found else "No SSL pinning patterns detected"
