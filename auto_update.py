"""
auto_update.py — Check GitHub releases and update OpenAGI

How OpenClaw/Goose do it:
OpenClaw: Electron + electron-updater → checks GitHub releases API → downloads .exe
Goose: Rust + self_update crate → same pattern

Our Python version:
1. Check https://api.github.com/repos/ApeironAILab/OpenAGI/releases/latest
2. Compare tag_name with current VERSION
3. If newer: download the zip → extract → restart

Usage:
python auto_update.py --check (check only)
python auto_update.py --update (check + apply)
python auto_update.py --version (print version)
"""
import sys
import os
import json
import shutil
import zipfile
import subprocess
from pathlib import Path

VERSION = "5.3.0"
GITHUB_REPO = "ApeironAILab/OpenAGI"
RELEASES_API = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"


def get_latest_release() -> dict:
    """Fetch latest release from GitHub API."""
    import urllib.request
    try:
        req = urllib.request.Request(
            RELEASES_API,
            headers={"User-Agent": "OpenAGI-Updater/1.0", "Accept": "application/vnd.github.v3+json"}
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read().decode('utf-8'))
    except Exception as e:
        return {"error": str(e)}


def version_tuple(v: str):
    """Convert version string to tuple for comparison."""
    return tuple(int(x) for x in v.strip("vV").split("."))


def check_update() -> dict:
    """Check if an update is available."""
    release = get_latest_release()
    if "error" in release:
        return {"available": False, "error": release["error"]}

    latest = release.get("tag_name", "v0.0.0")
    notes = release.get("body", "")
    assets = release.get("assets", [])

    # Find .zip asset
    zip_url = None
    zip_name = None
    for asset in assets:
        name = asset.get("name", "")
        if name.endswith(".zip"):
            zip_url = asset.get("browser_download_url")
            zip_name = name
            break

    current_ver = version_tuple(VERSION)
    latest_ver = version_tuple(latest)

    if latest_ver > current_ver:
        return {
            "available": True,
            "current": VERSION,
            "latest": latest,
            "notes": notes[:500] if notes else "",
            "zip_url": zip_url,
            "zip_name": zip_name,
            "published_at": release.get("published_at", "")
        }

    return {"available": False, "current": VERSION, "latest": latest}


def apply_update(zip_url: str, zip_name: str = "update.zip"):
    """Download and extract update."""
    import urllib.request
    import tempfile

    print(f"Downloading update from {zip_url}...")

    # Create temp directory
    tmp_dir = Path(tempfile.gettempdir()) / "openagi_update"
    tmp_dir.mkdir(parents=True, exist_ok=True)

    tmp_zip = tmp_dir / zip_name

    try:
        # Download with progress
        def download_progress(block_num, block_size, total_size):
            downloaded = block_num * block_size
            percent = min(downloaded / total_size * 100, 100) if total_size > 0 else 0
            if block_num % 10 == 0 or percent >= 100:
                print(f"  Downloaded: {percent:.1f}%", end='\r')

        urllib.request.urlretrieve(zip_url, tmp_zip, reporthook=download_progress)
        print("\nDownload complete!")

        # Create backup
        backup_dir = Path("./backup_v" + VERSION)
        if backup_dir.exists():
            shutil.rmtree(backup_dir)
        backup_dir.mkdir(parents=True, exist_ok=True)

        # Backup critical directories
        for dirname in ["core", "interfaces", "autonomy", "evolution", "control", "generation", "agentic", "safety", "routing"]:
            src = Path(f"./{dirname}")
            if src.exists():
                dst = backup_dir / dirname
                shutil.copytree(src, dst, dirs_exist_ok=True)
        print(f"Backup saved to {backup_dir}")

        # Extract update
        extract_dir = tmp_dir / "extracted"
        if extract_dir.exists():
            shutil.rmtree(extract_dir)
        extract_dir.mkdir(parents=True, exist_ok=True)

        print("Extracting...")
        with zipfile.ZipFile(tmp_zip, 'r') as z:
            z.extractall(extract_dir)

        # Find the root of extracted content
        src_root = extract_dir
        items = list(extract_dir.iterdir())
        if len(items) == 1 and items[0].is_dir():
            src_root = items[0]  # Handle common "repo-main/" subfolder

        # Files to preserve (user data)
        PRESERVE = {
            ".env", "workspace", "google_credentials.json", "google_token.json",
            "memory", "logs", "backup_"
        }

        # Copy new files
        print("Installing update...")
        for item in src_root.rglob("*"):
            rel_path = item.relative_to(src_root)
            rel_str = str(rel_path)

            # Skip preserved paths
            if any(rel_str.startswith(p) or p in rel_str for p in PRESERVE):
                continue

            dest = Path(".") / rel_path

            if item.is_dir():
                dest.mkdir(parents=True, exist_ok=True)
            else:
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(item, dest)

        # Cleanup
        shutil.rmtree(tmp_dir)
        print("\nUpdate applied successfully!")
        print(f"New version: {VERSION}")
        print("Please restart OpenAGI to use the new version.")
        return True

    except Exception as e:
        print(f"Update failed: {e}")
        return False


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "--check"

    if cmd == "--version" or cmd == "-v":
        print(f"OpenAGI v{VERSION}")
        return 0

    elif cmd == "--check" or cmd == "-c":
        info = check_update()
        if info.get("available"):
            print(f"Update available: v{info['current']} → {info['latest']}")
            print(f"Published: {info.get('published_at', 'unknown')}")
            if info.get('notes'):
                print(f"\nRelease notes:\n{info['notes'][:300]}...")
            print(f"\nRun 'python auto_update.py --update' to apply.")
            return 1
        else:
            if info.get("error"):
                print(f"Check failed: {info['error']}")
                return 1
            print(f"Up to date (v{info.get('current', VERSION)})")
            return 0

    elif cmd == "--update" or cmd == "-u":
        info = check_update()
        if not info.get("available"):
            if info.get("error"):
                print(f"Check failed: {info['error']}")
                return 1
            print("Already up to date.")
            return 0

        if not info.get("zip_url"):
            print("No zip asset found in release.")
            return 1

        print(f"Update: v{info['current']} → {info['latest']}")
        confirm = input("Apply update? [y/N] ")
        if confirm.lower() == 'y':
            return 0 if apply_update(info["zip_url"], info.get("zip_name", "update.zip")) else 1
        else:
            print("Cancelled.")
            return 0

    else:
        print(f"OpenAGI Updater v{VERSION}")
        print("")
        print("Usage:")
        print("  python auto_update.py --version  Show current version")
        print("  python auto_update.py --check     Check for updates")
        print("  python auto_update.py --update    Apply update")
        return 0


if __name__ == "__main__":
    sys.exit(main())
