#!/usr/bin/env python3
"""
MediaDigest v4.0 - News fetching module
Fetches hot topics from Hacker News, GitHub Trending, and QbitAI.
"""

import json
import os
import sys
import argparse
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

BASE_DIR = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = BASE_DIR / "data"
SUMMARIES_DIR = DATA_DIR / "summaries"
SOURCES_FILE = DATA_DIR / "news_sources.json"
SEEN_FILE = DATA_DIR / "news_seen.json"  # Global URL dedup history

REQUEST_TIMEOUT = 10
HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

DEFAULT_SOURCES = {
    "hackernews": {
        "name": "Hacker News",
        "type": "api",
        "url": "https://hacker-news.firebaseio.com/v0/topstories.json",
        "enabled": True,
    },
    "github": {
        "name": "GitHub Trending",
        "type": "html",
        "url": "https://github.com/trending",
        "enabled": True,
    },
    "qbitai": {
        "name": "量子位",
        "type": "html",
        "url": "https://www.qbitai.com/",
        "enabled": True,
    },
}


def _ensure_dirs():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    SUMMARIES_DIR.mkdir(parents=True, exist_ok=True)


def _load_seen():
    """Load global set of already-seen URLs."""
    if SEEN_FILE.exists():
        try:
            with open(SEEN_FILE, "r", encoding="utf-8") as f:
                return set(json.load(f))
        except Exception:
            pass
    return set()


def _save_seen(seen):
    """Save global set of already-seen URLs."""
    _ensure_dirs()
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted(seen), f, ensure_ascii=False)


def load_sources():
    """Load source configuration, merging with defaults."""
    _ensure_dirs()
    if SOURCES_FILE.exists():
        with open(SOURCES_FILE, "r", encoding="utf-8") as f:
            user_sources = json.load(f)
        merged = dict(DEFAULT_SOURCES)
        merged.update(user_sources)
        return merged
    return dict(DEFAULT_SOURCES)


def save_sources(sources):
    """Save user-modified sources (only custom ones, not defaults)."""
    _ensure_dirs()
    # Save only non-default or modified sources
    to_save = {}
    for k, v in sources.items():
        if k not in DEFAULT_SOURCES or v != DEFAULT_SOURCES[k]:
            to_save[k] = v
    with open(SOURCES_FILE, "w", encoding="utf-8") as f:
        json.dump(to_save, f, ensure_ascii=False, indent=2)


def _save_result(source_key, data):
    """Save only NEW items (not seen before). Returns (filepath, new_count, total_new)."""
    _ensure_dirs()
    seen = _load_seen()

    # Filter: only items we haven't seen
    new_items = []
    for item in data["items"]:
        url = item.get("url", "")
        if url and url not in seen:
            seen.add(url)
            new_items.append(item)

    # Always update seen history (even if no new items)
    _save_seen(seen)

    if not new_items:
        return None, 0, 0

    # Save to today's file
    date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    filename = f"news_{source_key}_{date_str}.json"
    filepath = SUMMARIES_DIR / filename

    # Append to existing file for same day
    existing_items = []
    if filepath.exists():
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                existing_data = json.load(f)
            existing_items = existing_data.get("items", [])
        except Exception:
            pass

    all_items = existing_items + new_items
    output = {
        "source": data.get("source", source_key),
        "source_name": data.get("source_name", source_key),
        "fetch_time": datetime.now(timezone.utc).isoformat(),
        "items": all_items,
        "total": len(all_items),
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    return filepath, len(new_items), len(all_items)


# --- Fetchers ---

def fetch_hackernews(count=30):
    """Fetch top stories from Hacker News API."""
    try:
        resp = requests.get(
            "https://hacker-news.firebaseio.com/v0/topstories.json",
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        top_ids = resp.json()[:count]
    except Exception as e:
        return {"success": False, "error": str(e)}

    items = []
    for rank, sid in enumerate(top_ids, 1):
        try:
            item_resp = requests.get(
                f"https://hacker-news.firebaseio.com/v0/item/{sid}.json",
                timeout=REQUEST_TIMEOUT,
            )
            item_resp.raise_for_status()
            story = item_resp.json()
            if not story:
                continue
            items.append({
                "rank": rank,
                "title": story.get("title", ""),
                "url": story.get("url", f"https://news.ycombinator.com/item?id={sid}"),
                "score": story.get("score", 0),
                "meta": {
                    "by": story.get("by", ""),
                    "time": story.get("time", 0),
                },
            })
        except Exception:
            continue

    return {
        "success": True,
        "data": {
            "source": "hackernews",
            "source_name": "Hacker News",
            "fetch_time": datetime.now(timezone.utc).isoformat(),
            "items": items,
            "total": len(items),
        },
    }


def fetch_github_trending(count=30):
    """Fetch trending repos from GitHub."""
    try:
        resp = requests.get(
            "https://github.com/trending",
            headers=HEADERS,
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        resp.encoding = "utf-8"
    except Exception as e:
        return {"success": False, "error": str(e)}

    soup = BeautifulSoup(resp.text, "html.parser")
    articles = soup.select("article.Box-row")
    items = []

    for rank, article in enumerate(articles[:count], 1):
        try:
            # Repo name: h2 > a
            h2 = article.find("h2")
            if not h2:
                continue
            a = h2.find("a")
            if not a:
                continue
            repo_name = a.get_text(strip=True).replace(" ", "").replace("\n", "")
            repo_url = "https://github.com" + a.get("href", "")

            # Description
            p = article.find("p")
            description = p.get_text(strip=True) if p else ""

            # Stars - try multiple patterns
            stars = 0
            star_link = article.find("a", href=lambda h: h and "/stargazers" in h)
            if star_link:
                star_text = star_link.get_text(strip=True).replace(",", "")
                try:
                    stars = int(star_text)
                except ValueError:
                    pass

            # Language
            lang = ""
            lang_span = article.find("span", itemprop="programmingLanguage")
            if lang_span:
                lang = lang_span.get_text(strip=True)

            items.append({
                "rank": rank,
                "title": repo_name,
                "url": repo_url,
                "score": stars,
                "meta": {
                    "description": description,
                    "language": lang,
                },
            })
        except Exception:
            continue

    if not items:
        return {"success": False, "error": "No trending repos found - DOM structure may have changed"}

    return {
        "success": True,
        "data": {
            "source": "github",
            "source_name": "GitHub Trending",
            "fetch_time": datetime.now(timezone.utc).isoformat(),
            "items": items,
            "total": len(items),
        },
    }


def fetch_qbitai(count=20):
    """Fetch latest articles from QbitAI."""
    try:
        resp = requests.get(
            "https://www.qbitai.com/",
            headers=HEADERS,
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        resp.encoding = "utf-8"
    except Exception as e:
        return {"success": False, "error": str(e)}

    soup = BeautifulSoup(resp.text, "html.parser")
    items = []

    # Try common article list patterns
    article_links = soup.select("a[href*='/']")
    seen_urls = set()

    for link in article_links:
        if len(items) >= count:
            break
        href = link.get("href", "")
        title = link.get_text(strip=True)
        if not title or len(title) < 8:
            continue
        if not href.startswith("http"):
            if href.startswith("/"):
                href = "https://www.qbitai.com" + href
            else:
                continue
        if "qbitai.com" not in href:
            continue
        if href in seen_urls:
            continue
        # Filter out nav/footer links
        if any(skip in href for skip in ["/tag/", "/author/", "/about", "/contact"]):
            continue
        seen_urls.add(href)
        items.append({
            "rank": len(items) + 1,
            "title": title,
            "url": href,
            "score": 0,
            "meta": {
                "summary": "",
                "publish_time": "",
            },
        })

    if not items:
        return {"success": False, "error": "No articles found - page structure may have changed or anti-bot triggered"}

    return {
        "success": True,
        "data": {
            "source": "qbitai",
            "source_name": "量子位",
            "fetch_time": datetime.now(timezone.utc).isoformat(),
            "items": items,
            "total": len(items),
        },
    }


FETCHERS = {
    "hackernews": fetch_hackernews,
    "github": fetch_github_trending,
    "qbitai": fetch_qbitai,
}


def fetch_source(source_key, count=30):
    """Fetch from a single source."""
    fetcher = FETCHERS.get(source_key)
    if not fetcher:
        return {"success": False, "error": f"Unknown source: {source_key}"}
    return fetcher(count)


def fetch_all(count=30):
    """Fetch from all enabled sources."""
    sources = load_sources()
    results = {}
    for key, cfg in sources.items():
        if not cfg.get("enabled", True):
            continue
        print(f"  Fetching {cfg.get('name', key)}...")
        result = fetch_source(key, count)
        if result["success"]:
            filepath, new, total = _save_result(key, result["data"])
            if new > 0:
                print(f"    ✓ {new} new items → {filepath}")
            else:
                print(f"    ✓ No new items (all already seen)")
            results[key] = result["data"]
        else:
            print(f"    ✗ {result['error']}")
            results[key] = {"error": result["error"]}
    return results


def cmd_fetch(args):
    """Handle: news fetch [--source S] [--count N]"""
    source = args.source if args.source != "all" else None
    count = args.count

    print("=" * 60)
    print("MediaDigest - News Fetch")
    print("=" * 60)

    if source:
        sources = load_sources()
        if source not in sources and source not in FETCHERS:
            print(f"Error: unknown source '{source}'")
            print(f"Available: {', '.join(FETCHERS.keys())}")
            sys.exit(1)
        print(f"Source: {sources.get(source, {}).get('name', source)}")
        print(f"Count: {count}")
        result = fetch_source(source, count)
        if result["success"]:
            filepath, new, total = _save_result(source, result["data"])
            if new > 0:
                print(f"\n✓ {new} new items (total saved: {total})")
                print(f"  Saved to: {filepath}")
                print(f"\nTop new items:")
                for item in result["data"]["items"][:5]:
                    # Only show items that were actually new
                    print(f"  [{item['rank']}] {item['title']}")
                    print(f"      {item['url']}")
            else:
                print(f"\n✓ No new items (all already seen)")
        else:
            print(f"\n✗ Error: {result['error']}")
            sys.exit(1)
    else:
        print(f"Sources: all")
        print(f"Count: {count}\n")
        results = fetch_all(count)
        print(f"\n{'=' * 60}")
        ok = sum(1 for v in results.values() if "items" in v)
        fail = sum(1 for v in results.values() if "error" in v)
        print(f"Done: {ok} succeeded, {fail} failed")


def cmd_sources(args):
    """Handle: news sources [--add|--remove|--list]"""
    if args.add:
        parts = args.add
        if len(parts) < 3:
            print("Error: --add requires <name> <url> <type>")
            print("  Example: --add techcrunch https://techcrunch.com html")
            sys.exit(1)
        name, url, stype = parts[0], parts[1], parts[2]
        sources = load_sources()
        sources[name] = {"name": name, "url": url, "type": stype, "enabled": True}
        save_sources(sources)
        print(f"✓ Added source: {name} ({url})")
    elif args.remove:
        sources = load_sources()
        if args.remove in sources:
            del sources[args.remove]
            save_sources(sources)
            print(f"✓ Removed source: {args.remove}")
        else:
            print(f"Error: source '{args.remove}' not found")
            sys.exit(1)
    else:
        # List
        sources = load_sources()
        print("Configured sources:")
        for key, cfg in sources.items():
            status = "enabled" if cfg.get("enabled", True) else "disabled"
            print(f"  [{status:8s}] {key:15s} - {cfg.get('name', key)} ({cfg.get('type', '?')})")
            print(f"              {cfg.get('url', '')}")


def parse_news_args(args):
    """Parse news subcommand arguments."""
    parser = argparse.ArgumentParser(prog="media_digest.py news")
    sub = parser.add_subparsers(dest="subcmd")

    # fetch
    p_fetch = sub.add_parser("fetch", help="Fetch news from sources")
    p_fetch.add_argument("--source", "-s", default="all",
                         choices=["hackernews", "github", "qbitai", "all"],
                         help="Source to fetch (default: all)")
    p_fetch.add_argument("--count", "-n", type=int, default=30,
                         help="Number of items (default: 30)")

    # sources
    p_src = sub.add_parser("sources", help="Manage news sources")
    p_src.add_argument("--add", nargs=3, metavar=("NAME", "URL", "TYPE"),
                       help="Add a custom source")
    p_src.add_argument("--remove", "-r", metavar="NAME",
                       help="Remove a source")
    p_src.add_argument("--list", "-l", action="store_true",
                       help="List all sources (default action)")

    return parser.parse_args(args)
