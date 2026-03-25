"""
MediaDigest v3.0 - Unified Download Pipeline
Downloads audio from YouTube, Bilibili, and X/Twitter with automatic cookie retry.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

from .config import BASE_DIR, COOKIES_DIR, TEMP_DIR
from .platform import detect_platform, build_video_url


def _run_yt_dlp(args, timeout=180):
    """Run yt-dlp with given arguments. Returns (returncode, stdout, stderr)."""
    cmd = ["yt-dlp"] + args
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout, r.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "Timeout"
    except FileNotFoundError:
        return -1, "", "yt-dlp not found. Install: pip install yt-dlp"


def _is_auth_error(stderr):
    """Check if the error indicates authentication is required."""
    auth_signals = [
        "403", "401", "forbidden", "unauthorized",
        "login", "sign in", "members only", "private",
        "content you requested is not available",
        "age-restricted",
    ]
    stderr_lower = stderr.lower()
    return any(sig in stderr_lower for sig in auth_signals)


def _is_docker():
    """Check if running inside Docker container."""
    return os.path.exists("/.dockerenv")


def _find_cookies_file(platform):
    """Find cookies file for a given platform in standard locations."""
    cookie_filename = "cookies.txt"
    search_paths = [
        COOKIES_DIR / platform / cookie_filename,
        BASE_DIR / "cookies" / platform / cookie_filename,
        Path.home() / ".openclaw" / "cookies" / platform / cookie_filename,
        Path.home() / ".config" / "media-digest" / "cookies" / platform / cookie_filename,
    ]
    for p in search_paths:
        if p.exists():
            return str(p)
    return None


def _find_browser_cookies(platform):
    """Detect available browsers for cookie extraction."""
    # Safari is excluded on macOS because Keychain blocks external cookie access
    # yt-dlp --cookies-from-browser safari often fails with permission errors
    browsers = ["chrome", "edge", "firefox", "brave", "opera"]
    if sys.platform != "darwin":
        browsers.append("safari")

    available = []
    for browser in browsers:
        if sys.platform == "darwin":
            # macOS - check both CLI name and .app bundle
            browser_path = shutil.which(browser)
            if browser_path:
                available.append(browser)
            else:
                # Check /Applications for .app bundles
                app_names = {
                    "chrome": "Google Chrome",
                    "firefox": "Firefox",
                    "brave": "Brave Browser",
                    "edge": "Microsoft Edge",
                    "opera": "Opera",
                }
                app_path = Path(f"/Applications/{app_names.get(browser, browser)}.app/Contents/MacOS")
                if app_path.exists():
                    available.append(browser)
        elif sys.platform == "win32":
            # Windows - check registry or common paths
            if browser == "chrome":
                p = Path(os.environ.get("PROGRAMFILES", "")) / "Google/Chrome/Application/chrome.exe"
                if p.exists():
                    available.append(browser)
            elif browser == "edge":
                p = Path(os.environ.get("PROGRAMFILES(X86)", "")) / "Microsoft/Edge/Application/msedge.exe"
                if p.exists():
                    available.append(browser)
            elif browser == "firefox":
                p = Path(os.environ.get("PROGRAMFILES", "")) / "Mozilla Firefox/firefox.exe"
                if p.exists():
                    available.append(browser)
        else:
            # Linux - check if browser binary exists
            browser_names = {
                "chrome": ["google-chrome", "google-chrome-stable", "chromium", "chromium-browser"],
                "edge": ["microsoft-edge", "microsoft-edge-stable"],
                "firefox": ["firefox"],
                "brave": ["brave", "brave-browser"],
                "opera": ["opera"],
                "safari": [],
            }
            for name in browser_names.get(browser, []):
                if shutil.which(name):
                    available.append(browser)
                    break
    return available


def download(url, output_dir=None, cookies_file=None, audio_format="mp3", quality=5):
    """
    Download audio from a video URL with automatic cookie retry.

    Args:
        url: Video URL (YouTube, Bilibili, or X/Twitter)
        output_dir: Output directory (default: data/temp/)
        cookies_file: Optional path to cookies file
        audio_format: Audio format (default: mp3)
        quality: Audio quality 0-10, lower is better (default: 5)

    Returns:
        dict: {
            success: bool,
            audio_path: str or None,
            metadata: dict,
            method: str,  # 'direct' | 'cookies-browser' | 'cookies-file' | 'failed'
            error: str or None
        }
    """
    if output_dir is None:
        output_dir = str(TEMP_DIR)
    else:
        Path(output_dir).mkdir(parents=True, exist_ok=True)

    info = detect_platform(url)
    platform = info["platform"]
    video_id = info["id"]

    # Build output template
    safe_id = video_id or "download"
    output_template = os.path.join(output_dir, f"{platform}_{safe_id}.%(ext)s")

    # Base yt-dlp arguments
    base_args = [
        "-x", "--audio-format", audio_format,
        "--audio-quality", str(quality),
        "-o", output_template,
        "--no-warnings",
        "--no-playlist",  # Only download single video
    ]

    # Note: YouTube subtitle extraction is handled separately by extract_subtitles()
    # in transcriber.py. The download function always downloads audio.

    # === Attempt 1: Direct download (no cookies) ===
    rc, stdout, stderr = _run_yt_dlp(base_args + [url])
    audio_path = _find_audio_file(output_dir, f"{platform}_{safe_id}", audio_format)

    if audio_path:
        meta = _extract_metadata(stdout, platform, video_id, url)
        return {
            "success": True,
            "audio_path": audio_path,
            "metadata": meta,
            "method": "direct",
            "error": None,
        }

    if not _is_auth_error(stderr) and rc != -1:
        # Not an auth error - something else went wrong
        meta = _extract_metadata(stdout, platform, video_id, url)
        return {
            "success": False,
            "audio_path": None,
            "metadata": meta,
            "method": "failed",
            "error": stderr.strip() or "Download failed",
        }

    # === Attempt 2: Cookie-based retry ===
    # If user provided a cookies file, use it
    if cookies_file and os.path.exists(cookies_file):
        rc, stdout, stderr = _run_yt_dlp(
            base_args + ["--cookies", cookies_file, url]
        )
        audio_path = _find_audio_file(output_dir, f"{platform}_{safe_id}", audio_format)
        if audio_path:
            meta = _extract_metadata(stdout, platform, video_id, url)
            return {
                "success": True,
                "audio_path": audio_path,
                "metadata": meta,
                "method": "cookies-file",
                "error": None,
            }

    # Auto-detect environment and try appropriate cookie method
    if _is_docker():
        # Docker: look for cookie files
        cookie_file = _find_cookies_file(platform)
        if cookie_file:
            rc, stdout, stderr = _run_yt_dlp(
                base_args + ["--cookies", cookie_file, url]
            )
            audio_path = _find_audio_file(output_dir, f"{platform}_{safe_id}", audio_format)
            if audio_path:
                meta = _extract_metadata(stdout, platform, video_id, url)
                return {
                    "success": True,
                    "audio_path": audio_path,
                    "metadata": meta,
                    "method": "cookies-file",
                    "error": None,
                }
        return {
            "success": False,
            "audio_path": None,
            "metadata": _extract_metadata("", platform, video_id, url),
            "method": "failed",
            "error": (
                f"Authentication required for {platform} video. "
                f"Running in Docker - place cookies file at: "
                f"data/cookies/{platform}/cookies.txt\n"
                f"To export cookies:\n"
                f"  Chrome/Firefox: Install 'Get cookies.txt LOCALLY' extension, "
                f"visit YouTube, log in, then export.\n"
                f"  macOS Safari: Install a cookie export extension in Safari, "
                f"export YouTube cookies to a file, then copy to the path above."
            ),
        }
    else:
        # Local: try browser cookies
        browsers = _find_browser_cookies(platform)
        for browser in browsers:
            rc, stdout, stderr = _run_yt_dlp(
                base_args + [f"--cookies-from-browser", browser, url]
            )
            audio_path = _find_audio_file(output_dir, f"{platform}_{safe_id}", audio_format)
            if audio_path:
                meta = _extract_metadata(stdout, platform, video_id, url)
                return {
                    "success": True,
                    "audio_path": audio_path,
                    "metadata": meta,
                    "method": "cookies-browser",
                    "error": None,
                }

        return {
            "success": False,
            "audio_path": None,
            "metadata": _extract_metadata("", platform, video_id, url),
            "method": "failed",
            "error": (
                f"Authentication required for {platform} video. "
                f"No browser cookies found.\n"
                f"Try: (1) Open the video in your browser and log in, "
                f"then retry; (2) Export cookies to data/cookies/{platform}/cookies.txt "
                f"using a browser extension like 'Get cookies.txt LOCALLY'."
                + (
                    "\n\nmacOS Safari users: Safari cookies cannot be read by external "
                    "programs due to Keychain restrictions. Please install Chrome or Firefox, "
                    "or export cookies manually using a Safari cookie export extension, "
                    "then save to data/cookies/" + platform + "/cookies.txt"
                    if sys.platform == "darwin"
                    else ""
                )
            ),
        }


def download_metadata_only(url):
    """
    Get video metadata without downloading audio.

    Returns:
        dict: {title, uploader, duration, platform, id, upload_date, url, description}
    """
    args = [
        "--no-download", "--no-warnings",
        "--print", "%(title)s|%(uploader)s|%(duration)s|%(upload_date)s|%(description)s",
        url,
    ]
    rc, stdout, stderr = _run_yt_dlp(args, timeout=30)
    info = detect_platform(url)

    if rc == 0 and stdout.strip():
        parts = stdout.strip().split("|", 4)
        return {
            "title": parts[0] if len(parts) > 0 else "",
            "uploader": parts[1] if len(parts) > 1 else "",
            "duration": _parse_duration(parts[2] if len(parts) > 2 else "0"),
            "platform": info["platform"],
            "id": info["id"],
            "upload_date": parts[3] if len(parts) > 3 else "",
            "url": url,
            "description": parts[4] if len(parts) > 4 else "",
        }
    return {
        "title": "",
        "uploader": "",
        "duration": 0,
        "platform": info["platform"],
        "id": info["id"],
        "upload_date": "",
        "url": url,
        "description": "",
    }


def _find_audio_file(directory, prefix, audio_format):
    """Find the downloaded audio file."""
    d = Path(directory)
    for ext in [audio_format, "mp3", "m4a", "opus", "webm", "wav"]:
        candidate = d / f"{prefix}.{ext}"
        if candidate.exists():
            return str(candidate)
    # Also try without platform prefix (fallback)
    safe_id = prefix.split("_", 1)[-1] if "_" in prefix else prefix
    for ext in [audio_format, "mp3", "m4a", "opus", "webm", "wav"]:
        candidate = d / f"{safe_id}.{ext}"
        if candidate.exists():
            return str(candidate)
    return None


def _extract_metadata(stdout, platform, video_id, url):
    """Extract metadata from yt-dlp output."""
    return {
        "title": "",
        "uploader": "",
        "duration": 0,
        "platform": platform,
        "id": video_id,
        "upload_date": "",
        "url": url,
    }


def _parse_duration(s):
    """Parse duration string to seconds."""
    try:
        return int(float(s))
    except (ValueError, TypeError):
        return 0
