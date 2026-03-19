"""
MediaDigest v3.0 - Whisper Transcription
Transcribes audio files using faster-whisper. Falls back gracefully if not installed.
"""

import os
import subprocess
import sys


def transcribe(audio_path, language=None, model_size=None):
    """
    Transcribe audio file using faster-whisper.

    Args:
        audio_path: Path to audio file
        language: Language code (e.g., 'en', 'zh'). Auto-detects if None.
        model_size: Whisper model size (tiny/base/small/medium/large). Default from config.

    Returns:
        dict: {
            text: str,
            language: str,
            duration: float,
            segments: list,
            method: 'whisper' | 'error'
        }
    """
    if not os.path.exists(audio_path):
        return {
            "text": "",
            "language": "",
            "duration": 0,
            "segments": [],
            "method": "error",
            "error": f"Audio file not found: {audio_path}",
        }

    # Check if faster-whisper is available
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        return {
            "text": "",
            "language": "",
            "duration": 0,
            "segments": [],
            "method": "error",
            "error": (
                "faster-whisper not installed. "
                "Install: pip install faster-whisper"
            ),
        }

    # Get model size from config if not specified
    if model_size is None:
        from .config import WHISPER_MODEL
        model_size = WHISPER_MODEL

    try:
        # Load model (CPU with int8 quantization for broad compatibility)
        device = "cpu"
        compute_type = "int8"
        model = WhisperModel(model_size, device=device, compute_type=compute_type)

        # Transcribe
        segments_iter, info = model.transcribe(
            audio_path,
            language=language,
            beam_size=5,
            vad_filter=True,  # Skip silence
            vad_parameters=dict(min_silence_duration_ms=500),
        )

        # Collect results
        segments = []
        text_parts = []
        for seg in segments_iter:
            segments.append({
                "start": round(seg.start, 2),
                "end": round(seg.end, 2),
                "text": seg.text,
            })
            text_parts.append(seg.text)

        full_text = "".join(text_parts).strip()

        return {
            "text": full_text,
            "language": info.language,
            "duration": info.duration,
            "segments": segments,
            "method": "whisper",
        }

    except Exception as e:
        return {
            "text": "",
            "language": language or "",
            "duration": 0,
            "segments": [],
            "method": "error",
            "error": f"Transcription failed: {e}",
        }


def extract_subtitles(video_url, output_dir):
    """
    Try to extract subtitles/captions from YouTube using yt-dlp.
    This is preferred over Whisper when available (faster, more accurate).

    Returns:
        dict: {text: str, language: str, source: 'youtube-subs' | 'none'}
    """
    import tempfile
    from .platform import detect_platform

    info = detect_platform(video_url)
    if info["platform"] != "youtube":
        return {"text": "", "language": "", "source": "none"}

    with tempfile.TemporaryDirectory() as tmpdir:
        cmd = [
            "yt-dlp",
            "--write-auto-sub", "--write-sub",
            "--sub-lang", "en,zh,ja,ko,-live_chat",
            "--convert-subs", "srt",
            "--skip-download",
            "--no-warnings",
            "-o", os.path.join(tmpdir, "subs"),
            video_url,
        ]
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return {"text": "", "language": "", "source": "none"}

        if r.returncode != 0:
            return {"text": "", "language": "", "source": "none"}

        # Find and read subtitle files
        for lang_code in ["en", "zh", "ja", "ko"]:
            for f in os.listdir(tmpdir):
                if f.endswith(f".{lang_code}.srt"):
                    srt_path = os.path.join(tmpdir, f)
                    text = _parse_srt(srt_path)
                    if text:
                        return {"text": text, "language": lang_code, "source": "youtube-subs"}

        # Try any srt file
        for f in os.listdir(tmpdir):
            if f.endswith(".srt"):
                srt_path = os.path.join(tmpdir, f)
                text = _parse_srt(srt_path)
                if text:
                    return {"text": text, "language": "", "source": "youtube-subs"}

    return {"text": "", "language": "", "source": "none"}


def _parse_srt(srt_path):
    """Parse SRT subtitle file to plain text."""
    try:
        with open(srt_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except (UnicodeDecodeError, OSError):
        try:
            with open(srt_path, "r", encoding="latin-1") as f:
                lines = f.readlines()
        except OSError:
            return ""

    text_parts = []
    for line in lines:
        line = line.strip()
        # Skip sequence numbers and timestamps
        if line and not line.isdigit() and "-->" not in line:
            text_parts.append(line)

    return " ".join(text_parts).strip()
