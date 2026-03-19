"""
MediaDigest v3.0 - Configuration Management
"""

import json
import os
from pathlib import Path

# Base directories
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("MEDIA_DIGEST_DIR", BASE_DIR / "data"))
OUTPUT_DIR = DATA_DIR / "summaries"
TEMP_DIR = DATA_DIR / "temp"
COOKIES_DIR = DATA_DIR / "cookies"

CHANNELS_FILE = DATA_DIR / "channels.json"
PROCESSED_FILE = DATA_DIR / "processed.json"

WHISPER_MODEL = os.environ.get("MEDIA_DIGEST_WHISPER_MODEL", "base")

for d in [DATA_DIR, OUTPUT_DIR, TEMP_DIR, COOKIES_DIR]:
    d.mkdir(parents=True, exist_ok=True)


def load_json(path, default=None):
    """Load JSON file, return default if missing."""
    path = Path(path)
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return default if default is not None else {}


def save_json(path, data):
    """Save data to JSON file with pretty formatting."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_channels():
    """Load channel list."""
    return load_json(CHANNELS_FILE, [])


def save_channels(channels):
    """Save channel list."""
    save_json(CHANNELS_FILE, channels)


def load_processed():
    """Load processed video records."""
    return load_json(PROCESSED_FILE, {})


def save_processed(records):
    """Save processed video records."""
    save_json(PROCESSED_FILE, records)


def is_processed(platform, video_id):
    """Check if a video has already been processed."""
    records = load_processed()
    return f"{platform}:{video_id}" in records


def mark_processed(platform, video_id, title="", summary_path=""):
    """Mark a video as processed."""
    records = load_processed()
    records[f"{platform}:{video_id}"] = {
        "date": __import__("datetime").datetime.now(
            __import__("datetime").timezone.utc
        ).isoformat(),
        "title": title,
        "summary_path": str(summary_path),
    }
    save_processed(records)
