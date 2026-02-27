@echo off
REM build_windows.bat -- Build Speech Bubble Editor v2 for Windows
REM
REM Outputs to: win\
REM   SpeechBubbleEditor-2.1.10-win64-portable.zip  (always created)
REM   SpeechBubbleEditor-2.1.10-win64-Setup.exe     (requires Inno Setup 6)
REM
REM Requirements:
REM   Python 3.11+ in PATH
REM   Inno Setup 6 (optional, for the Setup.exe installer):
REM     https://jrsoftware.org/isdl.php

setlocal EnableDelayedExpansion
cd /d "%~dp0"

set APP_NAME=SpeechBubbleEditor
set VERSION=2.1.10
set WIN_DIR=%~dp0win

echo === Speech Bubble Editor v%VERSION% -- Windows Build ===
if not exist "%WIN_DIR%" mkdir "%WIN_DIR%"

REM -- 1. Virtual environment --------------------------------------------------
echo.
echo [1/5] Setting up virtual environment...
if not exist ".build_venv" (
    python -m venv .build_venv
)
call .build_venv\Scripts\activate.bat
python -m pip install --quiet --upgrade pip
python -m pip install --quiet -r requirements.txt

REM -- 2. Generate icons -------------------------------------------------------
echo.
echo [2/5] Generating icons...
python create_icon.py

REM -- 3. PyInstaller ----------------------------------------------------------
echo.
echo [3/5] Building binary with PyInstaller...
python -m PyInstaller --clean --noconfirm speech_bubble_v2.spec

call .build_venv\Scripts\deactivate.bat
rmdir /s /q .build_venv

if not exist "dist\%APP_NAME%.exe" (
    echo ERROR: PyInstaller did not produce dist\%APP_NAME%.exe
    pause
    exit /b 1
)
echo   OK: dist\%APP_NAME%.exe

REM -- 4. Portable ZIP ---------------------------------------------------------
echo.
echo [4/5] Creating portable zip...
set ZIP_NAME=%APP_NAME%-%VERSION%-win64-portable.zip
powershell -NoProfile -Command ^
    "Compress-Archive -Path 'dist\%APP_NAME%.exe' -DestinationPath '%WIN_DIR%\%ZIP_NAME%' -Force"
echo   OK: %ZIP_NAME%

REM -- 5. Inno Setup installer (optional) -------------------------------------
echo.
echo [5/5] Creating installer...

REM Search common install locations. Use "set" without surrounding quotes
REM so the variable holds a plain path (no embedded quotes).
REM Then use "if defined ISCC" which is the correct CMD way to test for empty.
set "ISCC="
if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" set "ISCC=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if exist "C:\Program Files\Inno Setup 6\ISCC.exe"       set "ISCC=C:\Program Files\Inno Setup 6\ISCC.exe"
if exist "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" set "ISCC=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"

REM Also check if ISCC is already in PATH
if not defined ISCC (
    for /f "delims=" %%I in ('where ISCC.exe 2^>nul') do (
        if not defined ISCC set "ISCC=%%I"
    )
)

if defined ISCC (
    echo   Found: !ISCC!
    echo   Running Inno Setup...
    "!ISCC!" installer.iss /O"%WIN_DIR%" /F"%APP_NAME%-%VERSION%-win64-Setup"
    if errorlevel 1 (
        echo   ERROR: Inno Setup returned an error.
    ) else (
        echo   OK: %APP_NAME%-%VERSION%-win64-Setup.exe
    )
) else (
    echo   Inno Setup not found -- skipping installer.
    echo   Download free from: https://jrsoftware.org/isdl.php
    echo   Install it, then re-run this script to also get the Setup.exe.
    echo   The portable zip above works without an installer.
)

REM -- Summary -----------------------------------------------------------------
echo.
echo === Build complete -- output in win\ ===
dir "%WIN_DIR%"
pause
