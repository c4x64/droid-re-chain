# Changelog

## 0.3.0 (2026-05-24)

- NDK build improvements: ccache/LTO support, ELF verification (readelf + nm)
- Code quality: `include/logging.h` with thread-safe logging, BUILD_HASH, null guards
- `src/main.cpp`: constructor guard (atomic CAS), `install_hook()` with mutex, destructor
- `docs/api.md`: auto-generated API reference
- `scripts/build_ndk.py`: advanced builder with sanitizers, error parsing
- Fix: `Android.mk` removed `LOCAL_ARM_MODE` (meaningless on arm64), `Application.mk` API 21→29
- Fix: `setup.sh` handles `--break-system-packages` for Debian 12+/Ubuntu 23+
- 36 tests (up from 13), all green

## 0.2.0 (2026-05-24)

- 30 new tools: Frida integration (15) + APK handling (15)
- `src/tools_frida.py`: attach, spawn, stalker, memory read/write, Java hooks
- `src/tools_apk.py`: pull, decompile/recompile, sign, detect protection, SSL pinning
- Cross-platform `src/shared.py`: auto-detects macOS/Linux/Windows for ADB/NDK
- Tests: `tests/test_shared.py` with crash parser, OS detection, ADB error handling
- `setup.sh` / `setup.bat` for cross-platform setup

## 0.1.0 (2026-05-24)

- Initial release: 90 tools across 6 modules (ADB, NDK, il2cpp, hook, trap, mem)
- `CrashTrapDaemon` background thread reading `adb logcat -b crash`
- NDK compilation pipeline with ELF header verification
- Modular architecture: `src/server.py` + 6 `tools_*.py` modules