"""
MediaDigest v3.0 - Channel Monitoring
Unified channel management for YouTube and Bilibili.
X/Twitter: manual link submission only (no auto-monitoring).
"""

import subprocess
import sys
from datetime import datetime, timezone

from .config import load_channels, save_channels, load_processed, save_processed, DATA_DIR
from .platform import detect_platform, build_video_url, platform_label
from .downloader import download, download_metadata_only
from .transcriber import transcribe, extract_subtitles


def resolve_channel_url(url, platform=None):
    """Resolve a video or user URL to a canonical channel URL."""
    if platform is None:
        platform = detect_platform(url)["platform"]

    if platform == "twitter":
        # No channel monitoring for Twitter
        return None

    # Already a channel URL
    if "/channel/" in url or "/@" in url or "/c/" in url or "/space/" in url:
        return url

    # Video URL -> extract channel
    cmd = [
        "yt-dlp", "--flat-playlist", "--print", "%(channel_url)s",
        "--no-warnings", url,
    ]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    # youtu.be short link
    if "youtu.be/" in url:
        vid = url.split("youtu.be/")[1].split("?")[0]
        return resolve_channel_url(
            f"https://www.youtube.com/watch?v={vid}", platform
        )

    return url


def add_channel(url, alias=""):
    """
    Add a channel to monitor.

    Returns:
        dict: {success: bool, key: str, message: str}
    """
    channels = load_channels()
    info = detect_platform(url)
    platform = info["platform"]

    if platform == "unknown":
        return {
            "success": False, "key": "",
            "message": f"Unsupported platform for URL: {url}",
        }

    if platform == "twitter":
        return {
            "success": False, "key": "",
            "message": "X/Twitter does not support channel monitoring. "
                       "Use the 'now' command to process individual tweet links.",
        }

    channel_url = resolve_channel_url(url, platform)
    if not channel_url:
        return {
            "success": False, "key": "",
            "message": f"Could not resolve channel URL from: {url}",
        }

    key = f"{platform}:{channel_url}"

    # Check for duplicates
    for ch in channels:
        if ch.get("key") == key:
            return {
                "success": False, "key": key,
                "message": f"Channel already monitored: {alias or channel_url}",
            }

    channels.append({
        "key": key,
        "platform": platform,
        "name": alias or channel_url.split("/")[-1] or channel_url,
        "url": channel_url,
        "added_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "source_url": url,
    })
    save_channels(channels)

    return {
        "success": True,
        "key": key,
        "message": f"Added [{platform_label(platform)}] {alias or channel_url}",
    }


def remove_channel(identifier):
    """
    Remove a channel by key or alias.

    Returns:
        dict: {success: bool, message: str}
    """
    channels = load_channels()
    identifier_lower = identifier.lower()

    for i, ch in enumerate(channels):
        if identifier_lower in ch.get("key", "").lower() or \
           identifier_lower in ch.get("name", "").lower():
            removed = channels.pop(i)
            save_channels(channels)
            return {
                "success": True,
                "message": f"Removed [{platform_label(removed['platform'])}] {removed['name']}",
            }

    return {"success": False, "message": f"Channel not found: {identifier}"}


def list_channels():
    """List all monitored channels. Returns list of channel dicts."""
    channels = load_channels()
    processed = load_processed()
    return {
        "channels": channels,
        "total_processed": len(processed),
    }


def get_channel_videos(channel_url, platform, limit=10):
    """
    Get recent video IDs from a channel, oldest first.

    Returns:
        list: [video_id, ...]
    """
    cmd = [
        "yt-dlp", "--flat-playlist", "--print", "%(id)s",
        "--playlist-end", str(limit), "--no-warnings", channel_url,
    ]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if r.returncode == 0:
            ids = [l.strip() for l in r.stdout.strip().split("\n") if l.strip()]
            ids.reverse()  # Oldest first
            return ids
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return []


def check_channels(limit_per_channel=3):
    """
    Check all monitored channels for new unprocessed videos.

    Returns:
        list: [dict with video info for each newly processed video]
    """
    channels = load_channels()
    processed = load_processed()
    new_videos = []

    if not channels:
        return {"videos": [], "message": "No channels configured. Add one first."}

    for ch in channels:
        platform = ch["platform"]
        channel_url = ch["url"]
        name = ch.get("name", "")

        video_ids = get_channel_videos(channel_url, platform, limit=limit_per_channel)
        unprocessed = [vid for vid in video_ids
                       if f"{platform}:{vid}" not in processed]

        if not unprocessed:
            continue

        for vid in unprocessed:
            result = process_video(vid, platform)
            if result["success"]:
                processed[f"{platform}:{vid}"] = {
                    "date": datetime.now(timezone.utc).isoformat(),
                    "title": result.get("title", ""),
                    "summary_path": result.get("summary_path", ""),
                }
                new_videos.append(result)

    save_processed(processed)
    return {
        "videos": new_videos,
        "message": f"Processed {len(new_videos)} new video(s)",
    }


def process_video(video_id, platform, force=False):
    """
    Full pipeline: metadata -> download -> transcribe -> save summary.

    Returns:
        dict: {success, title, platform, video_id, transcript, summary_path, ...}
    """
    from .config import OUTPUT_DIR, save_json

    url = build_video_url(video_id, platform)

    # 1. Get metadata
    meta = download_metadata_only(url)
    title = meta.get("title", "") or video_id

    # 2. Check if already processed
    if not force:
        import os
        summary_path = OUTPUT_DIR / f"{platform}_{video_id}.json"
        if summary_path.exists():
            return {
                "success": True, "title": title, "platform": platform,
                "video_id": video_id, "transcript": "[already processed]",
                "summary_path": str(summary_path), "skipped": True,
            }

    # 3. Try YouTube subtitles first
    sub_result = extract_subtitles(url, str(OUTPUT_DIR))
    if sub_result["text"]:
        transcript = sub_result["text"]
        lang = sub_result["language"]
        method = "youtube-subs"
    else:
        # 4. Download audio and transcribe
        dl_result = download(url)
        if not dl_result["success"]:
            return {
                "success": False,
                "title": title,
                "platform": platform,
                "video_id": video_id,
                "transcript": "",
                "error": dl_result.get("error", "Download failed"),
            }

        audio_path = dl_result["audio_path"]
        tr_result = transcribe(audio_path)
        transcript = tr_result["text"]
        lang = tr_result.get("language", "")
        method = tr_result["method"]

        # Cleanup temp audio
        try:
            os.remove(audio_path)
        except OSError:
            pass

        if not transcript:
            return {
                "success": False,
                "title": title,
                "platform": platform,
                "video_id": video_id,
                "transcript": "",
                "error": tr_result.get("error", "Transcription failed"),
            }

    # 5. Save summary
    summary = {
        "video_id": video_id,
        "platform": platform,
        "title": meta.get("title", ""),
        "uploader": meta.get("uploader", ""),
        "duration": meta.get("duration", 0),
        "upload_date": meta.get("upload_date", ""),
        "language": lang,
        "transcription_method": method,
        "transcript_length": len(transcript),
        "transcript": transcript,
        "url": url,
        "processed_at": datetime.now(timezone.utc).isoformat(),
    }

    summary_path = OUTPUT_DIR / f"{platform}_{video_id}.json"
    save_json(summary_path, summary)

    return {
        "success": True,
        "title": title,
        "platform": platform,
        "video_id": video_id,
        "transcript": transcript,
        "summary_path": str(summary_path),
        "language": lang,
        "method": method,
    }


def migrate_v2_data(v2_dir):
    """
    Migrate v2.0 channel-monitor data to v3.0 format.

    Args:
        v2_dir: Path to v2.0 data directory

    Returns:
        dict: {channels_migrated: int, videos_migrated: int}
    """
    import os
    from pathlib import Path

    v2_path = Path(v2_dir)
    channels_migrated = 0
    videos_migrated = 0

    # Migrate channels.json (v2 format: dict keyed by platform:url)
    v2_channels = v2_path / "channels.json"
    if v2_channels.exists():
        from .config import load_json
        old = load_json(v2_channels, {})
        current = load_channels()
        existing_keys = {ch["key"] for ch in current}

        for key, info in old.items():
            if key not in existing_keys:
                current.append({
                    "key": key,
                    "platform": info.get("platform", ""),
                    "name": info.get("alias", ""),
                    "url": info.get("channel_url", ""),
                    "added_date": info.get("added_at", "")[:10] if info.get("added_at") else "",
                    "source_url": info.get("source_url", ""),
                    "migrated_from": "v2.0",
                })
                channels_migrated += 1
        save_channels(current)

    # Migrate processed.json (v2 format: list of "platform:id" strings)
    v2_processed = v2_path / "processed.json"
    if v2_processed.exists():
        from .config import load_json
        old_list = load_json(v2_processed, [])
        current = load_processed()

        for entry in old_list:
            if isinstance(entry, str) and entry not in current:
                current[entry] = {
                    "date": "",
                    "title": "",
                    "summary_path": "",
                    "migrated_from": "v2.0",
                }
                videos_migrated += 1
        save_processed(current)

    return {
        "channels_migrated": channels_migrated,
        "videos_migrated": videos_migrated,
    }
