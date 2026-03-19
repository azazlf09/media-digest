"""
MediaDigest v3.0 - Dependency Checker
Checks for required external tools and Python packages.
"""

import shutil
import subprocess
import sys


def _run_version(cmd):
    """Run a command and return version string."""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if r.returncode == 0:
            return r.stdout.strip().split("\n")[0][:80]
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass
    return ""


def check_all():
    """
    Check all dependencies.

    Returns:
        dict: {name: {installed: bool, version: str, install_cmd: str}}
    """
    results = {}

    # --- System tools ---
    for name, cmd, install in [
        ("python3", ["python3", "--version"], "See https://python.org"),
        ("yt-dlp", ["yt-dlp", "--version"], "pip install yt-dlp"),
        ("ffmpeg", ["ffmpeg", "-version"], "sudo apt install ffmpeg  # or: brew install ffmpeg"),
    ]:
        path = shutil.which(name) or shutil.which(name.replace("python3", "python"))
        installed = path is not None
        version = ""
        if installed:
            version = _run_version(cmd)
        results[name] = {
            "installed": installed,
            "version": version,
            "install_cmd": install,
        }

    # --- Python packages ---
    for name, import_name, install in [
        ("faster-whisper", "faster_whisper", "pip install faster-whisper"),
    ]:
        installed = False
        version = ""
        try:
            mod = __import__(import_name)
            installed = True
            version = getattr(mod, "__version__", "installed")
        except ImportError:
            pass
        results[name] = {
            "installed": installed,
            "version": version,
            "install_cmd": install,
        }

    return results


def check_all_print():
    """Check and print dependency status."""
    results = check_all()
    all_ok = True

    print("MediaDigest - Dependency Check")
    print("=" * 50)

    for name, info in results.items():
        if info["installed"]:
            print(f"  [OK] {name}: {info['version']}")
        else:
            all_ok = False
            print(f"  [--] {name}: NOT INSTALLED")
            print(f"       Install: {info['install_cmd']}")

    print("=" * 50)
    if all_ok:
        print("All dependencies installed.")
    else:
        missing = [n for n, i in results.items() if not i["installed"]]
        print(f"Missing: {', '.join(missing)}")
        print("Run 'bash setup.sh' to install.")
    return all_ok


if __name__ == "__main__":
    ok = check_all_print()
    sys.exit(0 if ok else 1)
