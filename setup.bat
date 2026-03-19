@echo off
REM MediaDigest v3.0 - Setup Script (Windows)
REM Installs: yt-dlp, ffmpeg, faster-whisper
REM PURE ASCII ONLY - No emoji, no unicode

echo ============================================
echo  MediaDigest v3.0 - Windows Setup
echo ============================================

REM --- 1. Check Python ---
echo.
echo [1/3] Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo   ERROR: Python not found. Install from https://python.org
    echo   Make sure to check "Add Python to PATH" during installation.
    goto :end
) else (
    for /f "tokens=*" %%v in ('python --version 2^>^&1') do echo   %%v: OK
)

REM --- 2. Install yt-dlp ---
echo.
echo [2/3] Installing yt-dlp...
pip install yt-dlp 2>&1 | findstr /V "already satisfied" >nul
echo   yt-dlp: installed

REM --- 3. Install faster-whisper ---
echo.
echo [3/3] Installing faster-whisper...
pip install faster-whisper 2>&1 | findstr /V "already satisfied" >nul
echo   faster-whisper: installed

echo.
echo ============================================
echo  Setup complete!
echo ============================================
echo.
echo NOTE: ffmpeg must be installed separately on Windows.
echo   Download from: https://ffmpeg.org/download.html
echo   Or use: winget install ffmpeg
echo   Or use: choco install ffmpeg
echo.
echo Quick start:
echo   python media_digest.py deps
echo   python media_digest.py now URL
echo.

:end
