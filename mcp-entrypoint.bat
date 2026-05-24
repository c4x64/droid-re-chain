@echo off
:: Portable launcher for droid-re-chain MCP server on Windows.
:: Resolves project root regardless of where the script lives.
set SCRIPT_DIR=%~dp0
set PROJECT_ROOT=%SCRIPT_DIR%..
cd /d "%PROJECT_ROOT%"

if "%ANDROID_NDK_HOME%"=="" (
    if exist "%LOCALAPPDATA%\Android\Sdk\ndk\25.2.9519653" (
        set "ANDROID_NDK_HOME=%LOCALAPPDATA%\Android\Sdk\ndk\25.2.9519653"
    )
)

python -m src.server %*