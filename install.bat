@echo off
setlocal EnableDelayedExpansion

echo =======================================
echo  Installing Node.js, uv, and Ollama
echo =======================================
echo.

:: Check for winget
where winget >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: winget is not available. Please install App Installer from the Microsoft Store.
    exit /b 1
)

:: ---- Node.js ----
echo [1/3] Installing Node.js (LTS)...
winget install --id OpenJS.NodeJS.LTS --accept-source-agreements --accept-package-agreements
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to install Node.js.
    exit /b 1
)
echo Node.js installed successfully.
echo.

:: ---- uv ----
echo [2/3] Installing uv...
powershell -ExecutionPolicy ByPass -Command "irm https://astral.sh/uv/install.ps1 | iex"
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to install uv.
    exit /b 1
)
echo uv installed successfully.
echo.

:: ---- Ollama ----
echo [3/3] Installing Ollama...
winget install --id Ollama.Ollama --accept-source-agreements --accept-package-agreements
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to install Ollama.
    exit /b 1
)
echo Ollama installed successfully.
echo.

echo =======================================
echo  All tools installed successfully!
echo  Please restart your terminal so that
echo  PATH changes take effect.
echo =======================================

endlocal
