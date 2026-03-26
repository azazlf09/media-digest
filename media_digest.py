#!/usr/bin/env python3
"""
MediaDigest v3.0 - Main Entry Point
Universal video summarization pipeline for YouTube, Bilibili, and X/Twitter.

Usage:
    python3 media_digest.py now <url>         Process a single video
    python3 media_digest.py check [count]     Check channels for new videos
    python3 media_digest.py add <url> [alias] Add a channel
    python3 media_digest.py remove <id>       Remove a channel
    python3 media_digest.py list              List channels
    python3 media_digest.py latest [count]    Show latest summaries
    python3 media_digest.py report            Generate text report
    python3 media_digest.py deps              Check dependencies
    python3 media_digest.py migrate <v2_dir>  Migrate v2.0 data
"""

import json
import os
import sys
from pathlib import Path

# Ensure the skill directory is on the path
BASE_DIR = Path(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, str(BASE_DIR))

from mdcore.config import OUTPUT_DIR, load_json, load_processed, load_channels
from mdcore.monitor import (
    add_channel, remove_channel, list_channels, check_channels,
    process_video, migrate_v2_data,
)
from mdcore.platform import detect_platform, platform_label
from mdcore.deps import check_all_print
from mdcore.downloader import download, download_metadata_only
from mdcore.transcriber import transcribe, extract_subtitles


def cmd_now(url):
    """Process a single video immediately."""
    print("=" * 60)
    print("MediaDigest - Single Video Processing")
    print("=" * 60)

    info = detect_platform(url)
    platform = info["platform"]
    video_id = info["id"]

    if platform == "unknown":
        print(f"Error: unsupported platform for URL: {url}")
        print("Supported: YouTube, Bilibili, X/Twitter")
        sys.exit(1)

    print(f"Platform: {info['platform_name']} [{platform_label(platform)}]")

    # For Twitter or unknown IDs, try to process via URL directly
    if not video_id:
        # Try downloading directly by URL
        dl_result = download(url)
        if not dl_result["success"]:
            meta = download_metadata_only(url)
            print(f"Title: {meta.get('title', 'N/A')}")
            print(f"Uploader: {meta.get('uploader', 'N/A')}")
            print(f"Error: {dl_result.get('error', 'Download failed')}")
            sys.exit(1)

        audio_path = dl_result["audio_path"]
        meta = dl_result.get("metadata", {})
        print(f"Title: {meta.get('title', 'N/A')}")
        print(f"Uploading audio...")
        tr_result = transcribe(audio_path)
        try:
            os.remove(audio_path)
        except OSError:
            pass

        if not tr_result["text"]:
            print(f"Error: {tr_result.get('error', 'Transcription failed')}")
            sys.exit(1)

        # Save result
        safe_name = "tweet" if platform == "twitter" else "video"
        summary_path = OUTPUT_DIR / f"{platform}_{safe_name}.json"
        summary = {
            "video_id": safe_name,
            "platform": platform,
            "title": meta.get("title", ""),
            "uploader": meta.get("uploader", ""),
            "duration": meta.get("duration", 0),
            "upload_date": meta.get("upload_date", ""),
            "language": tr_result.get("language", ""),
            "transcription_method": tr_result["method"],
            "transcript_length": len(tr_result["text"]),
            "transcript": tr_result["text"],
            "url": url,
            "processed_at": __import__("datetime").datetime.now(
                __import__("datetime").timezone.utc
            ).isoformat(),
        }
        from mdcore.config import save_json
        save_json(summary_path, summary)

        print(f"\n--- Summary ---")
        print(f"Language: {tr_result.get('language', 'N/A')}")
        print(f"Length: {len(tr_result['text'])} chars")
        print(f"Method: {tr_result['method']}")
        print(f"\nTranscript:\n{tr_result['text'][:2000]}")
        return

    # Check if already processed
    processed = load_processed()
    key = f"{platform}:{video_id}"
    if key in processed:
        print(f"Already processed: {video_id}")
        old_path = processed[key].get("summary_path", "")
        if old_path and os.path.exists(old_path):
            data = load_json(old_path)
            _print_summary(data)
        return

    # Process
    result = process_video(video_id, platform)

    if result["success"] and not result.get("skipped"):
        processed[key] = {
            "date": __import__("datetime").datetime.now(
                __import__("datetime").timezone.utc
            ).isoformat(),
            "title": result.get("title", ""),
            "summary_path": result.get("summary_path", ""),
        }
        from mdcore.config import save_processed
        save_processed(processed)

        if result.get("summary_path") and os.path.exists(result["summary_path"]):
            data = load_json(result["summary_path"])
            _print_summary(data)
    elif result.get("skipped"):
        pass
    else:
        print(f"Error: {result.get('error', 'Processing failed')}")
        sys.exit(1)


def cmd_add(url, alias=""):
    """Add a channel."""
    result = add_channel(url, alias)
    print(result["message"])


def cmd_remove(identifier):
    """Remove a channel."""
    result = remove_channel(identifier)
    print(result["message"])


def cmd_list():
    """List channels."""
    data = list_channels()
    channels = data["channels"]

    if not channels:
        print("No channels configured.")
        print("  Usage: python3 media_digest.py add <url> [alias]")
        return

    print(f"Channels ({len(channels)}):")
    for ch in channels:
        p = ch.get("platform", "")
        label = platform_label(p)
        name = ch.get("name", "")
        url = ch.get("url", "")[:60]
        added = ch.get("added_date", "")
        print(f"  [{label}] {name}")
        print(f"        {url}")
        if added:
            print(f"        Added: {added}")
    print(f"\nTotal processed videos: {data['total_processed']}")


def cmd_check(count=3):
    """Check channels for new videos."""
    print("=" * 60)
    print("MediaDigest - Channel Check")
    print("=" * 60)

    result = check_channels(count)
    videos = result["videos"]

    for v in videos:
        print(f"\n  [{platform_label(v['platform'])}] {v['title']}")
        print(f"    ID: {v['video_id']} | Method: {v.get('method', '')}")

    print(f"\n{'=' * 60}")
    print(f"Result: {result['message']}")
    print(f"{'=' * 60}")


def cmd_latest(count=3):
    """Show latest N processed summaries."""
    files = sorted(
        OUTPUT_DIR.glob("*.json"),
        key=lambda f: f.stat().st_mtime,
        reverse=True,
    )[:count]

    if not files:
        print("No summaries yet. Use 'now <url>' to process a video.")
        return

    for f in files:
        data = load_json(f)
        _print_summary(data)


def cmd_report():
    """Generate a text report of all summaries."""
    files = sorted(OUTPUT_DIR.glob("*.json"))
    if not files:
        print("No summaries yet.")
        return

    lines = []
    for f in files:
        data = load_json(f)
        p = data.get("platform", "unknown")
        date = data.get("upload_date", "unknown")
        channel = data.get("uploader", "unknown")
        title = data.get("title", "")
        transcript = data.get("transcript", "")
        vid = data.get("video_id", "")
        url = data.get("url", "")

        lines.append(f"[{platform_label(p)}][{date}] {channel}")
        lines.append(f"Title: {title}")
        lines.append(f"ID: {vid}")
        lines.append(f"URL: {url}")
        lines.append(f"Transcript ({len(transcript)} chars):")
        lines.append(transcript)
        lines.append("")
        lines.append("=" * 60)
        lines.append("")

    report = "\n".join(lines)
    from mdcore.config import DATA_DIR
    report_file = DATA_DIR / "report.txt"
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"Report saved: {report_file} ({len(report)} chars)")


def cmd_migrate(v2_dir):
    """Migrate v2.0 data."""
    result = migrate_v2_data(v2_dir)
    print(f"Migration complete:")
    print(f"  Channels migrated: {result['channels_migrated']}")
    print(f"  Videos migrated: {result['videos_migrated']}")


def _print_summary(data):
    """Print a formatted summary."""
    p = data.get("platform", "unknown")
    print(f"\n--- [{platform_label(p)}] Summary ---")
    print(f"Date:   {data.get('upload_date', 'N/A')}")
    print(f"Author: {data.get('uploader', 'N/A')}")
    print(f"Title:  {data.get('title', 'N/A')}")
    print(f"ID:     {data.get('video_id', 'N/A')}")
    print(f"Lang:   {data.get('language', 'N/A')} | "
          f"Length: {data.get('transcript_length', 0)} chars")
    print(f"URL:    {data.get('url', 'N/A')}")


def print_usage():
    print("""
MediaDigest v3.0 - Multi-Platform Video Summarization

Usage:
  python3 media_digest.py now <url>         Process a single video
  python3 media_digest.py check [count]     Check channels for new videos
  python3 media_digest.py add <url> [alias] Add a channel to monitor
  python3 media_digest.py remove <id>       Remove a channel
  python3 media_digest.py list              List monitored channels
  python3 media_digest.py latest [count]    Show latest N summaries
  python3 media_digest.py report            Generate text report
  python3 media_digest.py deps              Check dependencies
  python3 media_digest.py migrate <v2_dir>  Migrate v2.0 data

Supported platforms:
  - YouTube: youtube.com/watch?v=xxx, youtu.be/xxx
  - Bilibili: bilibili.com/video/BVxxx, b23.tv/xxx
  - X/Twitter: x.com/user/status/xxx (single link only)

News:
  python3 media_digest.py news fetch [--source hackernews|github|qbitai|all] [--count N]
  python3 media_digest.py news sources [--add <name> <url> <type>] [--remove <name>] [--list]
""")


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help", "help"):
        print_usage()
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == "now":
        if len(sys.argv) < 3:
            print("Error: provide a video URL")
            sys.exit(1)
        cmd_now(sys.argv[2])
    elif cmd == "add":
        if len(sys.argv) < 3:
            print("Error: provide a URL")
            sys.exit(1)
        cmd_add(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "")
    elif cmd == "remove":
        if len(sys.argv) < 3:
            print("Error: provide channel name or key")
            sys.exit(1)
        cmd_remove(sys.argv[2])
    elif cmd == "list":
        cmd_list()
    elif cmd == "check":
        cmd_check(int(sys.argv[2]) if len(sys.argv) > 2 else 3)
    elif cmd == "latest":
        cmd_latest(int(sys.argv[2]) if len(sys.argv) > 2 else 3)
    elif cmd == "report":
        cmd_report()
    elif cmd == "deps":
        ok = check_all_print()
        sys.exit(0 if ok else 1)
    elif cmd == "migrate":
        if len(sys.argv) < 3:
            print("Error: provide v2.0 data directory path")
            sys.exit(1)
        cmd_migrate(sys.argv[2])
    elif cmd == "news":
        from mdcore.news import parse_news_args, cmd_fetch, cmd_sources
        news_args = parse_news_args(sys.argv[2:])
        if news_args.subcmd == "fetch":
            cmd_fetch(news_args)
        elif news_args.subcmd == "sources":
            cmd_sources(news_args)
        else:
            print("Usage: news fetch | news sources")
            sys.exit(1)
    else:
        print(f"Unknown command: {cmd}")
        print_usage()
        sys.exit(1)
