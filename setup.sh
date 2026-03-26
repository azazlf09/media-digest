#!/usr/bin/env bash
# MediaDigest v3.0 - Setup Script (Linux / macOS)
# Installs: yt-dlp, ffmpeg, faster-whisper

set -e

echo "============================================"
echo " MediaDigest v3.0 - Setup"
echo "============================================"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# --- 1. System packages ---
echo ""
echo "[1/3] Checking system packages..."

if ! command -v ffmpeg &>/dev/null; then
    echo "  Installing ffmpeg..."
    if command -v apt-get &>/dev/null; then
        sudo apt-get update -qq && sudo apt-get install -y -qq ffmpeg 2>&1 | tail -1
    elif command -v brew &>/dev/null; then
        brew install ffmpeg 2>&1 | tail -3
    elif command -v yum &>/dev/null; then
        sudo yum install -y ffmpeg 2>&1 | tail -1
    else
        echo "  WARNING: Cannot auto-install ffmpeg. Please install manually."
        echo "  See: https://ffmpeg.org/download.html"
    fi
else
    echo "  ffmpeg: OK ($(ffmpeg -version 2>&1 | head -1))"
fi

# --- 2. yt-dlp ---
echo ""
echo "[2/3] Checking yt-dlp..."

if ! command -v yt-dlp &>/dev/null; then
    echo "  Installing yt-dlp..."
    pip3 install --break-system-packages yt-dlp 2>&1 | tail -2
else
    echo "  yt-dlp: OK ($(yt-dlp --version))"
fi

# --- 3. Python packages ---
echo ""
echo "[3/3] Checking Python packages..."

MISSING=""
for pkg in faster-whisper curl_cffi requests beautifulsoup4; do
    mod_name=$(echo "$pkg" | tr '-' '_')
    if python3 -c "import $mod_name" 2>/dev/null; then
        echo "  $pkg: OK"
    else
        echo "  $pkg: MISSING"
        MISSING="$MISSING $pkg"
    fi
done

if [ -n "$MISSING" ]; then
    echo "  Installing:$MISSING..."
    pip3 install --break-system-packages$MISSING 2>&1 | tail -3
fi

echo ""
echo "============================================"
echo " Setup complete!"
echo "============================================"
echo ""
echo "Quick start:"
echo "  python3 $SCRIPT_DIR/media_digest.py deps    # Verify installation"
echo "  python3 $SCRIPT_DIR/media_digest.py now <url>  # Process a video"
echo ""
