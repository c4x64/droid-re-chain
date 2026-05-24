"""Example: Start crash trap daemon, wait for crashes, and analyze."""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.shared import CrashTrapDaemon, _adb_run, ADB_BINARY


def main():
    # 1. Check device
    devices = _adb_run([ADB_BINARY, "devices"])
    print("Devices:", devices)

    # 2. Start crash trap
    daemon = CrashTrapDaemon()
    daemon.start()

    print("Watching for crashes (10 seconds)...")
    time.sleep(10)

    # 3. Get results
    crashes = daemon.get_crashes()
    daemon.stop()

    if crashes:
        print(f"Captured {len(crashes)} crash(es):")
        for c in crashes:
            print(f"  Signal: {c.get('signal', 'N/A')}")
            print(f"  Process: {c.get('process_name', 'N/A')}")
            print(f"  Backtrace frames: {len(c.get('backtrace', []))}")
    else:
        print("No crashes detected in the monitoring window.")


if __name__ == "__main__":
    main()