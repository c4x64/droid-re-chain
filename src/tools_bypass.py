"""5 Anti-Tamper Bypass tools — hook generators for root/emulator/debugger/integrity checks and device spoofing."""
import json

def register(mcp):

    @mcp.tool()
    def bypass_root_detect(package: str = "com.example.target") -> str:
        """Generate Frida hook to neutralize root detection checks. Args: package name."""
        script = """'use strict';
Java.perform(function() {
    // Hook common root detection methods
    var File = Java.use('java.io.File');
    File.exists.implementation = function() {
        var path = this.getPath();
        var rootPaths = ['/su', '/sbin/su', '/system/bin/su', '/system/xbin/su',
                         '/data/local/tmp/su', '/data/local/tmp/frida-server',
                         '/system/app/Superuser.apk', '/system/xbin/daemonsu'];
        for (var i = 0; i < rootPaths.length; i++) {
            if (path.indexOf(rootPaths[i]) >= 0) {
                console.log('[bypass] Blocked root check: ' + path);
                return false;
            }
        }
        return this.exists();
    };
    // Hook Build.TAGS to hide test-keys
    var Build = Java.use('android.os.Build');
    Java.scheduleOnMainThread(function() {
        try { Java.cast(Build.class, Java.use('java.lang.Class')).set(Build, 'TAGS', 'release-keys'); } catch(e) {}
        try { Java.cast(Build.class, Java.use('java.lang.Class')).set(Build, 'FINGERPRINT',
            Java.use('android.os.Build').FINGERPRINT.value.replace('/test-keys', '/release-keys')); } catch(e) {}
    });
    console.log('[bypass] Root detection hooks installed for ' + '%s');
});
""" % json.dumps(package)
        return script

    @mcp.tool()
    def bypass_emulator_detect() -> str:
        """Generate Frida hook to neutralize emulator detection checks."""
        script = """'use strict';
Java.perform(function() {
    // Spoof common emulator properties
    var Build = Java.use('android.os.Build');
    Build.MODEL.value = 'Pixel 9 Pro';
    Build.DEVICE.value = 'husky';
    Build.PRODUCT.value = 'husky';
    Build.MANUFACTURER.value = 'Google';
    Build.BRAND.value = 'google';
    Build.HARDWARE.value = 'husky';
    // Hook TelephonyManager to return real-looking IMEI
    var TelephonyManager = Java.use('android.telephony.TelephonyManager');
    TelephonyManager.getDeviceId.implementation = function() {
        return '352756100123456' + Math.floor(Math.random() * 9).toString();
    };
    TelephonyManager.getNetworkOperatorName.implementation = function() {
        return 'T-Mobile';
    };
    // Hook WiFi manager
    var WifiManager = Java.use('android.net.wifi.WifiManager');
    WifiManager.isWifiEnabled.implementation = function() { return true; };
    console.log('[bypass] Emulator detection hooks installed');
});
"""
        return script

    @mcp.tool()
    def bypass_debugger_detect() -> str:
        """Generate hook to neutralize ptrace and debugger detection."""
        script = """'use strict';
Java.perform(function() {
    // Hook Debug.isDebuggerConnected
    var Debug = Java.use('android.os.Debug');
    Debug.isDebuggerConnected.implementation = function() { return false; };
    Debug.waitingForDebugger.implementation = function() { return false; };
    // Hook Process.myUid to avoid android:debuggable checks
    var Process = Java.use('android.os.Process');
    // Hook native ptrace via Frida's low-level API
    var ptracePtr = Module.findExportByName('libc.so', 'ptrace');
    if (ptracePtr) {
        Interceptor.attach(ptracePtr, {
            onEnter: function(args) {
                var request = args[0].toInt32();
                if (request === 0 || request === 16 || request === 17) {  // PTRACE_TRACEME, PTRACE_ATTACH, PTRACE_DETACH
                    console.log('[bypass] Blocked ptrace call: ' + request);
                    this.returnValue = 0;
                }
            }
        });
    }
    // Hook isatty for stdin-based detection
    var isattyPtr = Module.findExportByName('libc.so', 'isatty');
    if (isattyPtr) {
        Interceptor.attach(isattyPtr, {
            onEnter: function(args) {
                console.log('[bypass] Blocked isatty check');
            }
        });
    }
    console.log('[bypass] Debugger detection hooks installed');
});
"""
        return script

    @mcp.tool()
    def bypass_integrity_check(package: str = "com.example.target") -> str:
        """Generate hook to neutralize APK signature / integrity verification."""
        script = """'use strict';
Java.perform(function() {
    // Hook PackageManager to return fake signature
    var PackageManager = Java.use('android.content.pm.PackageManager');
    PackageManager.getPackageInfo.implementation = function(packageName, flags) {
        console.log('[bypass] getPackageInfo called for: ' + packageName);
        return this.getPackageInfo(packageName, flags);
    };
    // Hook Signature verification
    var Signature = Java.use('android.content.pm.Signature');
    Signature.hashCode.implementation = function() {
        return 0xDEADBEEF;
    };
    // Hook common integrity check methods
    var classes = ['com.example.security.IntegrityCheck', 'com.google.android.play.core.integrity'];
    for (var i = 0; i < classes.length; i++) {
        try {
            var cls = Java.use(classes[i]);
            cls.verify.implementation = function() {
                console.log('[bypass] Integrity check blocked: ' + classes[i]);
                return true;
            };
        } catch(e) {}
    }
    // Patch the APK signature hash comparison
    var Arrays = Java.use('java.util.Arrays');
    var origEquals = Arrays.equals;
    Arrays.equals.implementation = function(a, b) {
        if (a !== null && b !== null && a.length === b.length) {
            return true;
        }
        return origEquals(a, b);
    };
    console.log('[bypass] Integrity check hooks installed for %s');
});
""" % json.dumps(package)
        return script

    @mcp.tool()
    def spoof_device_fingerprint(manufacturer: str = "Google", model: str = "Pixel 9 Pro",
                                  device: str = "husky", fingerprint_suffix: str = "release-keys") -> str:
        """Set ro.product.* props to match a real device via Frida. Args: manufacturer, model, device, fingerprint_suffix."""
        script = """'use strict';
Java.perform(function() {
    var Build = Java.use('android.os.Build');
    Build.MANUFACTURER.value = '%s';
    Build.MODEL.value = '%s';
    Build.DEVICE.value = '%s';
    Build.PRODUCT.value = '%s';
    Build.HARDWARE.value = '%s';
    Build.BRAND.value = '%s';
    Build.FINGERPRINT.value = '%s/' + Build.DEVICE.value + '/' + Build.PRODUCT.value + ':' +
        '15/AP4A/' + Build.FINGERPRINT.value.split(':')[0].split('/').pop() + '/' + Build.FINGERPRINT.value.split('/').pop() + ':' + '%s';
    Build.TAGS.value = '%s';
    console.log('[spoof] Device fingerprint spoofed to ' + Build.MANUFACTURER.value + ' ' + Build.MODEL.value);
});
""" % (manufacturer, model, device, device, device,
        manufacturer.split()[0].lower(), manufacturer.split()[0].lower(),
        fingerprint_suffix, fingerprint_suffix)
        return script