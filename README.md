# MediaDigest v3.0

<p align="center">
  <strong>Universal Video Summarization Pipeline</strong><br>
  Download • Transcribe • Summarize<br>
  <em>YouTube • Bilibili • X/Twitter</em>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-blue.svg" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/Platform-YouTube%20%7C%20Bilibili%20%7C%20X%2FTwitter-green.svg" alt="Platforms">
  <img src="https://img.shields.io/badge/API_Cost-Zero-success.svg" alt="Zero API Cost">
  <img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="MIT License">
</p>

<p align="center">
  <a href="README_CN.md">简体中文</a> | English
</p>

---

## What is MediaDigest?

MediaDigest is a **standalone Python CLI tool** that downloads audio from YouTube, Bilibili, and X/Twitter videos, transcribes it locally using Whisper (zero API cost), and outputs structured summaries. It also supports channel monitoring — automatically check YouTube and Bilibili channels for new content.

**MediaDigest works on its own — no AI platform or cloud service required.** Just install the dependencies and run.

It also includes an **OpenClaw Skill integration** (`SKILL.md`): if you're an [OpenClaw](https://openclaw.ai) user, drop it into your `skills/` folder and the AI agent can call it automatically — you just send a video link and get a summary back.

### Features

- **Multi-platform** — YouTube, Bilibili, X/Twitter in one tool
- **Zero API cost** — Local Whisper transcription, no cloud services needed
- **Smart subtitle extraction** — Prefers YouTube auto-subs over Whisper when available
- **Cookie auto-retry** — Automatically detects auth errors and retries with browser cookies
- **Channel monitoring** — Add YouTube/Bilibili channels and check for new videos
- **Graceful degradation** — Works even if some components are missing
- **Docker ready** — Cookie file mounting and dedicated setup script
---

## Quick Start

### Option 1: Local (Windows / Mac / Linux)

```bash
# 1. Clone and enter
git clone https://github.com/azazlf09/media-digest.git
cd media-digest

# 2. Install dependencies
bash setup.sh          # Mac/Linux
setup.bat              # Windows

# 3. Process a video
python3 media_digest.py now "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
```

**Requirements:** Python 3.11+, yt-dlp, ffmpeg, faster-whisper (all installed by setup script)

### Option 2: Docker Users

```bash
# 1. Clone
git clone https://github.com/azazlf09/media-digest.git

# 2. Export cookies from your browser (for auth-required videos)
#    Use browser extension: "Get cookies.txt LOCALLY"
#    Place at: data/cookies/youtube/cookies.txt (etc.)

# 3. Build and run with cookie mount
docker build -t media-digest .
docker run -v ./data/cookies:/app/data/cookies media-digest \
  python3 media_digest.py now "https://www.youtube.com/watch?v=..."
```

### Option 3: OpenClaw Users

```bash
# Drop the entire media-digest/ folder into your skills/ directory
# The AI agent will automatically use it when you send video URLs

# Or set up monitoring via cron
python3 skills/media-digest/media_digest.py add "https://youtube.com/@channel" "My Channel"
python3 skills/media-digest/media_digest.py check 5
```

---

## Usage

### Single Video

```bash
python3 media_digest.py now <VIDEO_URL>
```

Supports:
- `https://www.youtube.com/watch?v=...`
- `https://youtu.be/...`
- `https://www.bilibili.com/video/BV...`
- `https://b23.tv/...`
- `https://x.com/user/status/...`

### Channel Monitoring

```bash
# Add channels
python3 media_digest.py add "https://youtube.com/@channel" "Channel Name"
python3 media_digest.py add "https://bilibili.com/space/12345" "UP Name"

# Check for new videos (processes up to 3 per channel by default)
python3 media_digest.py check 5

# List channels
python3 media_digest.py list

# Remove channel
python3 media_digest.py remove "Channel Name"
```

### View Results

```bash
# Latest 5 summaries
python3 media_digest.py latest 5

# Full text report
python3 media_digest.py report

# Check dependencies
python3 media_digest.py deps
```

---

## Architecture

```
                    MediaDigest v3.0
                    ================

  Input URL ──> Platform Detection ──> Download Pipeline
                    (core/platform)      (core/downloader)
                                          |
                                          |  Direct download
                                          |  → Auth error?
                                          |     ├── Browser cookies (local)
                                          |     └── Cookie file (Docker)
                                          v
                                    Audio File
                                          |
                                          v
                               Transcription Pipeline
                               (core/transcriber)
                                          |
                                    YouTube subs?
                                   /           \
                                  Yes           No
                                  |             |
                              SRT parse    Whisper (local)
                                  \           /
                                   v         v
                                Transcript
                                      |
                                      v
                              Structured Summary (JSON)
                                      |
                              +-------+-------+
                              |               |
                         Channel Monitor    CLI Output
                         (core/monitor)   (media_digest.py)
```

### Module Structure

```
media_digest.py          # Main CLI entry point
core/
  platform.py            # URL parsing and platform detection
  downloader.py          # Unified download with cookie retry
  transcriber.py         # Whisper transcription + subtitle extraction
  monitor.py             # Channel management and batch processing
  deps.py                # Dependency checker
  config.py              # Configuration and data management
data/
  channels.json          # Monitored channels list
  processed.json         # Deduplication records
  summaries/             # Output: one JSON per video
  cookies/               # Cookie files (gitignored)
tools/
  cookie_helper.py       # Browser cookie export utility
```

---

## Cookie Setup (for protected content)

Some videos require authentication. MediaDigest handles this automatically:

### Local Users
On first auth failure, MediaDigest auto-detects your browser (Chrome, Edge, Firefox, Brave) and retries with browser cookies. Just make sure you're logged into the platform in your browser.

### Docker Users
1. Install the browser extension **"Get cookies.txt LOCALLY"**
2. Visit the platform (YouTube/Bilibili/X) and log in
3. Click the extension → Export
4. Place the file:
   ```
   data/cookies/youtube/cookies.txt
   data/cookies/bilibili/cookies.txt
   data/cookies/twitter/cookies.txt
   ```
5. Mount in Docker: `-v ./data/cookies:/app/data/cookies`

Or use the helper tool:
```bash
python3 tools/cookie_helper.py export --browser chrome --platform youtube
```

---

## Migration from v2.0

If you're upgrading from the `channel-monitor` v2.0:

```bash
python3 media_digest.py migrate /path/to/skills/yt-channel-monitor/data/
```

This migrates:
- `channels.json` → New list format
- `processed.json` → New dict format
- Existing summaries are preserved in their original location

---

## Output Format

Each processed video produces a JSON file:

```json
{
  "video_id": "dQw4w9WgXcQ",
  "platform": "youtube",
  "title": "Rick Astley - Never Gonna Give You Up",
  "uploader": "Rick Astley",
  "duration": 212,
  "upload_date": "2009-10-25",
  "language": "en",
  "transcription_method": "whisper",
  "transcript_length": 1520,
  "transcript": "Full transcript text here...",
  "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
  "processed_at": "2026-03-19T15:00:00Z"
}
```

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MEDIA_DIGEST_DIR` | `./data/` | Data directory path |
| `MEDIA_DIGEST_WHISPER_MODEL` | `base` | Whisper model (tiny/base/small/medium/large) |

---

## Supported Platforms

| Platform | URL Formats | Auth | Subtitles | Channel Monitor |
|----------|------------|------|-----------|-----------------|
| **YouTube** | youtube.com, youtu.be | Rare | Auto-subs + Whisper | Yes |
| **Bilibili** | bilibili.com, b23.tv | Rare | Whisper | Yes |
| **X/Twitter** | x.com, twitter.com | Always | Whisper | Manual only |

---

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Make changes and test
4. Commit: `git commit -m "Add my feature"`
5. Push: `git push origin feature/my-feature`
6. Open a Pull Request

Guidelines:
- All code and comments in English
- Follow existing code style
- Test edge cases (no internet, no whisper, no cookies)
- Keep dependencies minimal (yt-dlp, faster-whisper, ffmpeg only)

---

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

---

<p align="center">
  Built with ❤ by <a href="https://github.com/dagestudio">Da Ge Studio</a>
</p>
