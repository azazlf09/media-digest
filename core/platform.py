"""
MediaDigest v3.0 - URL Platform Detection
"""

import re


PLATFORMS = {
    "youtube": {
        "name": "YouTube",
        "domains": ["youtube.com", "youtu.be", "m.youtube.com", "www.youtube.com"],
        "patterns": [
            r"youtube\.com",
            r"youtu\.be",
        ],
    },
    "bilibili": {
        "name": "Bilibili",
        "domains": ["bilibili.com", "b23.tv", "www.bilibili.com"],
        "patterns": [
            r"bilibili\.com",
            r"b23\.tv",
        ],
    },
    "twitter": {
        "name": "X / Twitter",
        "domains": ["x.com", "twitter.com", "www.x.com"],
        "patterns": [
            r"\bx\.com",
            r"twitter\.com",
        ],
    },
}


def detect_platform(url):
    """
    Detect platform, video ID, and content type from a URL.

    Returns:
        dict: {
            platform: 'youtube' | 'bilibili' | 'twitter' | 'unknown',
            id: str,
            type: 'video' | 'channel' | 'unknown',
            platform_name: str
        }
    """
    url_lower = url.lower().strip()

    # YouTube
    if re.search(r"youtube\.com|youtu\.be", url_lower):
        vid = _extract_youtube_id(url)
        if vid:
            return {
                "platform": "youtube",
                "id": vid,
                "type": "video",
                "platform_name": "YouTube",
            }
        if "/@" in url or "/channel/" in url or "/c/" in url:
            return {
                "platform": "youtube",
                "id": "",
                "type": "channel",
                "platform_name": "YouTube",
            }
        return {"platform": "youtube", "id": "", "type": "unknown", "platform_name": "YouTube"}

    # Bilibili
    if re.search(r"bilibili\.com|b23\.tv", url_lower):
        vid = _extract_bilibili_id(url)
        if vid:
            return {
                "platform": "bilibili",
                "id": vid,
                "type": "video",
                "platform_name": "Bilibili",
            }
        if "/space/" in url:
            return {
                "platform": "bilibili",
                "id": "",
                "type": "channel",
                "platform_name": "Bilibili",
            }
        return {"platform": "bilibili", "id": "", "type": "unknown", "platform_name": "Bilibili"}

    # X / Twitter
    if re.search(r"\bx\.com|twitter\.com", url_lower):
        vid = _extract_twitter_id(url)
        if vid:
            return {
                "platform": "twitter",
                "id": vid,
                "type": "video",
                "platform_name": "X / Twitter",
            }
        return {"platform": "twitter", "id": "", "type": "unknown", "platform_name": "X / Twitter"}

    return {"platform": "unknown", "id": "", "type": "unknown", "platform_name": "Unknown"}


def _extract_youtube_id(url):
    """Extract YouTube video ID."""
    m = re.search(r"[?&]v=([a-zA-Z0-9_-]{11})", url)
    if m:
        return m.group(1)
    m = re.search(r"youtu\.be/([a-zA-Z0-9_-]{11})", url)
    if m:
        return m.group(1)
    m = re.search(r"embed/([a-zA-Z0-9_-]{11})", url)
    if m:
        return m.group(1)
    return ""


def _extract_bilibili_id(url):
    """Extract Bilibili video ID (BV or AV format)."""
    m = re.search(r"/video/(BV[a-zA-Z0-9]+)", url)
    if m:
        return m.group(1)
    m = re.search(r"/video/(av\d+)", url, re.IGNORECASE)
    if m:
        return m.group(1)
    return ""


def _extract_twitter_id(url):
    """Extract Twitter/X post ID."""
    m = re.search(r"/status/(\d+)", url)
    if m:
        return m.group(1)
    return ""


def build_video_url(video_id, platform):
    """Build a full video URL from video ID and platform."""
    if platform == "youtube":
        return f"https://www.youtube.com/watch?v={video_id}"
    elif platform == "bilibili":
        return f"https://www.bilibili.com/video/{video_id}"
    elif platform == "twitter":
        return f"https://x.com/i/status/{video_id}"
    return video_id


def platform_label(platform):
    """Get short label for platform."""
    labels = {"youtube": "YT", "bilibili": "BL", "twitter": "X", "unknown": "??"}
    return labels.get(platform, "??")
