"""
tools/web_tools.py — Web & URL tools for Sara AI.

Fixed for Windows:
  - Uses subprocess 'start' command for reliable browser opening
  - Falls back to webbrowser module if subprocess fails
  - Properly URL-encodes search queries
"""

import os
import subprocess
import platform
import webbrowser
import urllib.parse
import logging

logger = logging.getLogger(__name__)
OS = platform.system()

DOWNLOADS_DIR = os.path.join(os.path.expanduser("~"), "Downloads", "SaraAI")
MAX_SCRAPE_CHARS = 3000


def _open_url_in_browser(url: str) -> bool:
    """
    Open a URL reliably across platforms.
    Windows: uses 'start' shell command (most reliable).
    macOS: uses 'open'.
    Linux: uses 'xdg-open'.
    Falls back to webbrowser module.
    """
    try:
        if OS == "Windows":
            # 'start "" "url"' is the most reliable way on Windows
            subprocess.Popen(
                f'start "" "{url}"',
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return True
        elif OS == "Darwin":
            subprocess.Popen(
                ["open", url],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return True
        else:
            subprocess.Popen(
                ["xdg-open", url],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return True
    except Exception as e:
        logger.warning(f"subprocess URL open failed ({e}), using webbrowser fallback")

    # Fallback
    try:
        webbrowser.open(url)
        return True
    except Exception:
        return False


def google_search(query: str) -> str:
    """Search Google and open result in the default browser."""
    q = query.strip()
    if not q:
        return "❓ Please provide a search query."
    url = "https://www.google.com/search?q=" + urllib.parse.quote_plus(q)
    ok = _open_url_in_browser(url)
    if ok:
        return f"🔍 Opened Google search for: **{q}**"
    return f"❌ Could not open browser. Try: {url}"


def youtube_search(query: str) -> str:
    """Search YouTube and open result in the default browser."""
    q = query.strip()
    if not q:
        return "❓ Please provide a search query."
    url = "https://www.youtube.com/results?search_query=" + urllib.parse.quote_plus(q)
    ok = _open_url_in_browser(url)
    if ok:
        return f"▶️ Opened YouTube search for: **{q}**"
    return f"❌ Could not open browser. Try: {url}"


def open_url(url: str) -> str:
    """Open any URL in the default browser."""
    url = url.strip()
    if not url:
        return "❓ Please provide a URL."
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    ok = _open_url_in_browser(url)
    if ok:
        return f"🌐 Opened: **{url}**"
    return f"❌ Could not open browser for: {url}"


def scrape_website(url: str) -> str:
    """Fetch and extract readable text from a webpage."""
    import requests
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        return "❌ Missing `beautifulsoup4`. Run: `pip install beautifulsoup4`"
    try:
        resp = requests.get(
            url,
            timeout=12,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Sara-AI/1.0"},
        )
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        for tag in soup(["script", "style", "nav", "footer", "header", "aside", "form"]):
            tag.decompose()

        text = soup.get_text(separator="\n")
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        clean = "\n".join(lines)
        if len(clean) > MAX_SCRAPE_CHARS:
            clean = clean[:MAX_SCRAPE_CHARS] + "\n... [truncated]"
        return f"🌐 **{url}**\n\n{clean}"

    except requests.exceptions.Timeout:
        return f"⌛ Request timed out for: {url}"
    except requests.exceptions.HTTPError as e:
        return f"❌ HTTP error: {e}"
    except Exception as e:
        return f"❌ Scrape error: {e}"


def download_file(url: str) -> str:
    """Download a file from a URL into ~/Downloads/SaraAI/."""
    import requests
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    file_name = url.split("/")[-1].split("?")[0] or "downloaded_file"
    os.makedirs(DOWNLOADS_DIR, exist_ok=True)
    dest = os.path.join(DOWNLOADS_DIR, file_name)

    try:
        resp = requests.get(
            url, stream=True, timeout=60,
            headers={"User-Agent": "Sara-AI/1.0"},
        )
        resp.raise_for_status()

        total = 0
        with open(dest, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    total += len(chunk)
                if total > 200 * 1024 * 1024:
                    break

        size_str = (
            f"{total/1024:.1f} KB" if total < 1024*1024
            else f"{total/1024/1024:.1f} MB"
        )
        return f"✅ Downloaded `{file_name}` ({size_str})\nSaved to: `{dest}`"

    except requests.exceptions.Timeout:
        return "⌛ Download timed out."
    except requests.exceptions.HTTPError as e:
        return f"❌ HTTP error: {e}"
    except Exception as e:
        return f"❌ Download error: {e}"
