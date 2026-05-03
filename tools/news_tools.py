"""
tools/news_tools.py — Live News Headlines for Sara AI.

Uses Google News RSS + feedparser (no API key required).
Requires: pip install feedparser

Functions:
  get_news(query)         — Top 5 headlines for a topic
  get_trending_news()     — Top global headlines right now
"""

import logging
import html
import re

logger = logging.getLogger(__name__)

_GOOGLE_NEWS_URL = "https://news.google.com/rss/search?q={query}&hl=en-IN&gl=IN&ceid=IN:en"
_GOOGLE_TOP_URL  = "https://news.google.com/rss?hl=en-IN&gl=IN&ceid=IN:en"


def _clean_title(title: str) -> str:
    """Strip trailing source attribution from RSS titles."""
    title = html.unescape(title or "")
    # Google News appends " - Source Name" at the end
    title = re.sub(r"\s*-\s*[^-]{3,40}$", "", title).strip()
    return title


def _fetch_feed(url: str, max_items: int = 5) -> list[dict]:
    """Fetch and parse an RSS feed. Returns list of {title, link, published}."""
    try:
        import feedparser
    except ImportError:
        raise ImportError("feedparser not installed. Run: `pip install feedparser`")

    try:
        feed = feedparser.parse(url)
        items = []
        for entry in feed.entries[:max_items]:
            items.append({
                "title":     _clean_title(entry.get("title", "No title")),
                "link":      entry.get("link", ""),
                "published": entry.get("published", ""),
            })
        return items
    except Exception as e:
        raise RuntimeError(f"Feed fetch error: {e}")


def fetch_news_items(query: str, max_items: int = 5) -> list[dict]:
    """
    Return structured news items for a topic without formatting.
    Falls back to top headlines when the query is blank.
    """
    query = query.strip()
    if not query:
        return _fetch_feed(_GOOGLE_TOP_URL, max_items=max_items)
    url = _GOOGLE_NEWS_URL.format(query=query.replace(" ", "+"))
    return _fetch_feed(url, max_items=max_items)


def get_news(query: str) -> str:
    """
    Fetch top 5 news headlines for a given topic.
    Input: topic/keywords e.g. 'AI technology', 'cricket', 'Python programming'
    """
    query = query.strip()
    if not query:
        return get_trending_news("")

    try:
        items = fetch_news_items(query, max_items=6)

        if not items:
            return f"📰 No news found for **{query}**. Try a different topic."

        lines = [f"📰 **Top news for '{query}':**\n"]
        for i, item in enumerate(items, 1):
            title = item["title"]
            link  = item["link"]
            pub   = item["published"][:16] if item["published"] else ""
            pub_str = f" _{pub}_" if pub else ""
            lines.append(f"{i}. [{title}]({link}){pub_str}")

        return "\n".join(lines)

    except ImportError as e:
        return f"❌ {e}"
    except Exception as e:
        logger.error(f"get_news error: {e}")
        return f"❌ Could not fetch news for '{query}': {e}"


def get_trending_news(unused: str = "") -> str:
    """Fetch the top 6 trending global news headlines right now."""
    try:
        items = _fetch_feed(_GOOGLE_TOP_URL, max_items=6)

        if not items:
            return "📰 Could not fetch trending news right now."

        lines = ["📰 **Top Headlines:**\n"]
        for i, item in enumerate(items, 1):
            title = item["title"]
            link  = item["link"]
            lines.append(f"{i}. [{title}]({link})")

        return "\n".join(lines)

    except ImportError as e:
        return f"❌ {e}"
    except Exception as e:
        logger.error(f"get_trending_news error: {e}")
        return f"❌ Could not fetch trending news: {e}"
