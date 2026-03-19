@echo off
REM MediaDigest - Cookie Helper (Windows)
REM Helps Docker users set up cookie files
REM PURE ASCII ONLY

echo MediaDigest Cookie Helper (Windows)
echo ===================================
echo.
echo To set up cookies for Docker deployment:
echo.
echo 1. Install the browser extension:
echo    "Get cookies.txt LOCALLY" for Chrome/Firefox
echo    Search for it in your browser extension store
echo.
echo 2. Visit the platform website and log in:
echo    - YouTube: youtube.com
echo    - Bilibili: bilibili.com
echo    - Twitter: x.com
echo.
echo 3. Click the extension icon, then "Export" 
echo    Save the file as "cookies.txt"
echo.
echo 4. Place the file in the correct directory:
echo.
echo    For YouTube:
echo      data\cookies\youtube\cookies.txt
echo.
echo    For Bilibili:
echo      data\cookies\bilibili\cookies.txt
echo.
echo    For Twitter:
echo      data\cookies\twitter\cookies.txt
echo.
echo 5. If using Docker, mount the cookies directory:
echo    docker run -v /path/to/cookies:/app/skills/media-digest/data/cookies ...
echo.
echo Current cookie status:
echo.

set "BASE_DIR=%~dp0.."
if exist "%BASE_DIR%\data\cookies\youtube\cookies.txt" (
    echo   [OK] YouTube cookies found
) else (
    echo   [--] YouTube cookies missing
)

if exist "%BASE_DIR%\data\cookies\bilibili\cookies.txt" (
    echo   [OK] Bilibili cookies found
) else (
    echo   [--] Bilibili cookies missing
)

if exist "%BASE_DIR%\data\cookies\twitter\cookies.txt" (
    echo   [OK] Twitter cookies found
) else (
    echo   [--] Twitter cookies missing
)

echo.
pause
