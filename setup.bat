@echo off
echo === droid-re-chain Setup (Windows) ===

REM 1. Python deps
pip install -r requirements.txt

REM 2. Verify ADB
where adb >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo WARNING: adb not on PATH. Install Android platform-tools.
    echo Download: https://developer.android.com/studio/releases/platform-tools
)

REM 3. Verify NDK
if "%ANDROID_NDK_HOME%"=="" (
    echo WARNING: ANDROID_NDK_HOME not set.
    echo Set it to your NDK r25+ path, e.g.:
    echo set ANDROID_NDK_HOME=C:\Users\you\AppData\Local\Android\Sdk\ndk\25.2.9519653
)

REM 4. Create directories
if not exist libs mkdir libs
if not exist logs mkdir logs
if not exist patches mkdir patches
if not exist frida_scripts mkdir frida_scripts
if not exist apk_work mkdir apk_work

REM 5. Verify imports
echo Verifying module imports...
python -c "from src.server import mcp; print('OK:', len(mcp._tools), 'tools registered')"

echo === Setup complete ===
echo Run: python -m src.server