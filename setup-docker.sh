#!/usr/bin/env bash
# MediaDigest v3.0 - Docker Setup Script
# Run this inside a Docker container to install all dependencies.

set -e

echo "============================================"
echo " MediaDigest v3.0 - Docker Setup"
echo "============================================"

# --- 1. System packages ---
echo ""
echo "[1/3] Installing system packages..."

apt-get update -qq
apt-get install -y -qq ffmpeg > /dev/null 2>&1
echo "  ffmpeg: OK"

# --- 2. yt-dlp ---
echo ""
echo "[2/3] Installing yt-dlp..."
pip3 install yt-dlp 2>&1 | tail -1
echo "  yt-dlp: OK"

# --- 3. faster-whisper ---
echo ""
echo "[3/3] Installing faster-whisper..."
pip3 install faster-whisper 2>&1 | tail -1
echo "  faster-whisper: OK"

# --- 4. Cookie setup ---
echo ""
echo "[4/4] Cookie configuration..."
COOKIES_DIR="/app/skills/media-digest/data/cookies"
mkdir -p "$COOKIES_DIR"/{youtube,bilibili,twitter}

if [ -d "/cookies" ]; then
    echo "  Found /cookies directory, copying..."
    cp -r /cookies/* "$COOKIES_DIR/" 2>/dev/null || true
fi

echo ""
echo "============================================"
echo " Docker setup complete!"
echo "============================================"
echo ""
echo "Cookie files can be mounted at:"
echo "  /app/skills/media-digest/data/cookies/youtube/cookies.txt"
echo "  /app/skills/media-digest/data/cookies/bilibili/cookies.txt"
echo "  /app/skills/media-digest/data/cookies/twitter/cookies.txt"
echo ""
echo "Or set the environment variable MEDIA_DIGEST_DIR"
echo "to point to your data directory."
echo ""
