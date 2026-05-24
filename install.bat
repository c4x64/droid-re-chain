@echo off
:: droid-re-chain — Universal one-liner installer for Windows
:: Usage:
::   curl -fsSL https://raw.githubusercontent.com/c4x64/droid-re-chain/main/install.bat | cmd
::   powershell -Command "iwr -Uri https://raw.githubusercontent.com/c4x64/droid-re-chain/main/install.bat -OutFile install.bat && install.bat"

setlocal enabledelayedexpansion
set "REPO=c4x64/droid-re-chain"
set "BRANCH=main"
set "INSTALL_DIR=%USERPROFILE%\droid-re-chain"

echo.
echo ============================================
echo   droid-re-chain — Universal Installer
echo   OS: Windows
echo   Target: %INSTALL_DIR%
echo ============================================
echo.

:: 1. Check git
where git >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: git is required. Install from https://git-scm.com/downloads
    exit /b 1
)

:: 2. Check python
where python >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: python is required. Install from https://python.org/downloads
    exit /b 1
)

:: 3. Clone
if exist "%INSTALL_DIR%\.git" (
    echo [2/5] Updating existing installation...
    cd /d "%INSTALL_DIR%"
    git pull --ff-only origin %BRANCH%
) else (
    echo [2/5] Cloning droid-re-chain...
    git clone --depth 1 --branch %BRANCH% https://github.com/%REPO%.git "%INSTALL_DIR%"
)
cd /d "%INSTALL_DIR%"

:: 4. Install deps
echo [3/5] Installing Python dependencies...
pip install -r requirements.txt

:: 5. Check NDK
echo [4/5] Checking Android NDK...
if "%ANDROID_NDK_HOME%"=="" (
    if exist "%LOCALAPPDATA%\Android\Sdk\ndk\25.2.9519653" (
        setx ANDROID_NDK_HOME "%LOCALAPPDATA%\Android\Sdk\ndk\25.2.9519653"
        echo   ANDROID_NDK_HOME set to %%LOCALAPPDATA%%\Android\Sdk\ndk\25.2.9519653
    ) else (
        echo   WARNING: ANDROID_NDK_HOME not set.
        echo   Set it: setx ANDROID_NDK_HOME C:\Users\you\AppData\Local\Android\Sdk\ndk\25.2.9519653
    )
) else (
    echo   ANDROID_NDK_HOME=%ANDROID_NDK_HOME%
)

:: 6. Clients
echo [5/5] Writing MCP client configs...

> "%INSTALL_DIR%\.cursor\mcp.json" (
echo { "mcpServers": { "droid-re-chain": { "command": "cmd", "args": ["/c", "%INSTALL_DIR%\mcp-entrypoint.bat"] } } }
)
if not exist "%INSTALL_DIR%\.claude" mkdir "%INSTALL_DIR%\.claude"
> "%INSTALL_DIR%\.claude\settings.json" (
echo { "mcpServers": { "droid-re-chain": { "command": "cmd", "args": ["/c", "%INSTALL_DIR%\mcp-entrypoint.bat"] } } }
)

echo.
echo ============================================
echo   droid-re-chain installed!
echo   Location: %INSTALL_DIR%
echo   Tools:    122 across 8 categories
echo.
echo   Server:
echo     cd /d %INSTALL_DIR% ^&^& python -m src.server
echo     cd /d %INSTALL_DIR% ^&^& python -m src.server --sse --port 8000
echo.
echo   One-liner:
echo     powershell -Command "iwr -Uri https://raw.githubusercontent.com/c4x64/droid-re-chain/main/install.bat -OutFile install.bat ^&^& install.bat"
echo ============================================
echo.
pause