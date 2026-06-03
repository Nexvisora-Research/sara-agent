"""
tools/browser_tools.py — Browser Automation via Playwright.

Playwright runs Chromium headlessly. First-time setup:
    playwright install chromium

Tools:
  browser_open(url)           — Navigate and return page title + URL
  browser_screenshot(url)     — Take a screenshot, save to ~/Screenshots/SaraAI/
    browser_fill_form(data)     — Fill + submit a form.
                                                                Also supports site search shortcuts like
                                                                "query=phone Redmi, url=https://flipkart.com/"
"""

import os
import logging
import re
import urllib.parse

logger = logging.getLogger(__name__)

SCREENSHOTS_DIR = os.path.join(os.path.expanduser("~"), "Pictures", "SaraAI_Screenshots")


def _check_playwright():
    """Return (playwright, error_message). Import check."""
    try:
        from playwright.sync_api import sync_playwright  # type: ignore[import-not-found]
        return sync_playwright, None
    except ImportError:
        return None, (
            "❌ Playwright is not installed.\n"
            "Run: `python -m pip install playwright`\n"
            "Then (optional): `playwright install chromium`\n"
            "If browser download fails on newer Ubuntu, set `SARA_PLAYWRIGHT_CHANNEL=chrome`."
        )


def _launch_chromium(p, *, headless: bool = True):
    """Launch Chromium with robust fallbacks.

    On some platforms (e.g. very new Ubuntu releases), Playwright may not provide
    managed browser builds. In that case we fall back to system-installed browsers
    via Playwright channels (chrome/chromium/msedge) or an explicit executable path.
    """
    preferred_channel = os.getenv("SARA_PLAYWRIGHT_CHANNEL", "").strip() or None
    preferred_executable = os.getenv("SARA_PLAYWRIGHT_EXECUTABLE_PATH", "").strip() or None

    def _try_launch(*, channel: str | None = None, executable_path: str | None = None):
        kwargs = {"headless": headless}
        if channel:
            kwargs["channel"] = channel
        if executable_path:
            kwargs["executable_path"] = executable_path
        return p.chromium.launch(**kwargs)

    # 1) Normal managed browser
    try:
        if preferred_channel or preferred_executable:
            return _try_launch(channel=preferred_channel, executable_path=preferred_executable)
        return _try_launch()
    except Exception as first_exc:
        logger.debug("Playwright default launch failed: %s", first_exc)

    # 2) Known channels for system browsers
    channels: list[str] = []
    if preferred_channel:
        channels.append(preferred_channel)
    channels.extend(["chrome", "chromium", "msedge"])
    tried: set[str] = set()
    for channel in channels:
        if not channel or channel in tried:
            continue
        tried.add(channel)
        try:
            return _try_launch(channel=channel)
        except Exception as exc:
            logger.debug("Playwright launch failed for channel=%s: %s", channel, exc)

    # 3) Explicit executable path
    if preferred_executable:
        try:
            return _try_launch(executable_path=preferred_executable)
        except Exception as exc:
            logger.debug("Playwright launch failed for executable_path=%s: %s", preferred_executable, exc)

    # Nothing worked
    raise first_exc


def _parse_key_values(value: str) -> dict[str, str]:
    pairs: dict[str, str] = {}
    for chunk in re.split(r"[;,]", value):
        chunk = chunk.strip()
        if "=" not in chunk:
            continue
        key, item_value = chunk.split("=", 1)
        pairs[key.strip().lower()] = item_value.strip().strip('"').strip("'")
    return pairs


def _build_search_url(base_url: str, query: str) -> str | None:
    base = base_url.strip().lower().rstrip("/")
    encoded = urllib.parse.quote_plus(query.strip())

    if not base or not query.strip():
        return None

    if "flipkart.com" in base:
        return f"https://www.flipkart.com/search?q={encoded}"
    if "amazon." in base or "amazon.com" in base:
        return f"https://www.amazon.in/s?k={encoded}"
    if "myntra.com" in base:
        return f"https://www.myntra.com/{encoded}"
    if "ajio.com" in base:
        return f"https://www.ajio.com/search/?text={encoded}"
    if "meesho.com" in base:
        return f"https://www.meesho.com/search?q={encoded}"
    if "nykaa.com" in base:
        return f"https://www.nykaa.com/search/result/?q={encoded}"
    if "croma.com" in base:
        return f"https://www.croma.com/searchBff?q={encoded}"
    if "firstcry.com" in base:
        return f"https://www.firstcry.com/search/?query={encoded}"
    if "snapdeal.com" in base:
        return f"https://www.snapdeal.com/search?keyword={encoded}"
    if "youtube.com" in base:
        return f"https://www.youtube.com/results?search_query={encoded}"
    if "google." in base:
        return f"https://www.google.com/search?q={encoded}"

    if base.startswith("http://") or base.startswith("https://"):
        separator = "&" if "?" in base else "?"
        return f"{base}{separator}q={encoded}"

    return None


def browser_open(url: str) -> str:
    """Open a URL in a headless Chromium browser and return the page title."""
    sync_playwright, err = _check_playwright()
    if err:
        return err

    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    try:
        with sync_playwright() as p:
            browser = _launch_chromium(p, headless=True)
            page = browser.new_page()
            page.goto(url, timeout=20000, wait_until="domcontentloaded")
            title = page.title()
            final_url = page.url
            browser.close()
        return f"🌐 **{title or 'No title'}**\n📎 {final_url}"
    except Exception as e:
        return f"❌ Browser error: {e}"


def browser_screenshot(url: str) -> str:
    """Take a full-page screenshot of a URL and save it locally."""
    sync_playwright, err = _check_playwright()
    if err:
        return err

    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    os.makedirs(SCREENSHOTS_DIR, exist_ok=True)
    safe_name = url.replace("https://", "").replace("http://", "").replace("/", "_")[:60]
    file_path = os.path.join(SCREENSHOTS_DIR, f"{safe_name}.png")

    try:
        with sync_playwright() as p:
            browser = _launch_chromium(p, headless=True)
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            page.goto(url, timeout=20000, wait_until="networkidle")
            page.screenshot(path=file_path, full_page=True)
            title = page.title()
            browser.close()
        return (
            f"📸 Screenshot of **{title or url}** saved!\n"
            f"📁 Path: `{file_path}`"
        )
    except Exception as e:
        return f"❌ Screenshot error: {e}"


def browser_fill_form(value: str) -> str:
    """
    Fill and submit a web form.
    Input format: 'url::selector=value;selector2=value2'
    Example: 'https://example.com/login::input[name=email]=test@test.com;input[name=password]=secret'
    """
    sync_playwright, err = _check_playwright()
    fields: dict[str, str] = {}
    url = ""

    if "::" in value:
        url, fields_str = value.split("::", 1)
        url = url.strip()
        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        for pair in fields_str.split(";"):
            pair = pair.strip()
            if "=" in pair:
                sel, val = pair.split("=", 1)
                fields[sel.strip()] = val.strip()
    else:
        parsed = _parse_key_values(value)
        url = parsed.pop("url", parsed.pop("site", parsed.pop("website", "")))
        fields = {key: val for key, val in parsed.items()}

    if not url:
        return (
            "❓ Format: `url::css_selector=value;css_selector2=value2`\n"
            "Or use: `query=phone Redmi, url=https://flipkart.com/`"
        )

    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    search_query = fields.pop("query", fields.pop("q", fields.pop("search", "")))
    only_search_fields = not fields

    if search_query and only_search_fields:
        search_url = _build_search_url(url, search_query)
        if search_url:
            try:
                from tools.web_tools import open_url

                return open_url(search_url)
            except Exception:
                pass

    if not fields:
        if search_query:
            return f"❓ Couldn't map search query to a search page for: `{url}`"
        return "❓ No fields provided. Format: `selector=value;selector2=value2`"

    if sync_playwright is None:
        return err

    try:
        with sync_playwright() as p:
            browser = _launch_chromium(p, headless=True)
            page = browser.new_page()
            page.goto(url, timeout=20000, wait_until="domcontentloaded")

            filled = []
            for selector, val in fields.items():
                try:
                    page.fill(selector, val)
                    filled.append(f"`{selector}` = `{val}`")
                except Exception as fe:
                    logger.warning(f"Could not fill {selector}: {fe}")

            # Try to find and click submit button
            for submit_sel in ["input[type=submit]", "button[type=submit]", "button:text('Submit')"]:
                try:
                    page.click(submit_sel, timeout=3000)
                    break
                except Exception:
                    pass

            result_url = page.url
            browser.close()

        fields_summary = "\n".join(f"  • {f}" for f in filled)
        return (
            f"✅ Form filled and submitted on `{url}`\n\n"
            f"Fields:\n{fields_summary}\n\n"
            f"📍 Landed on: {result_url}"
        )
    except Exception as e:
        return f"❌ Form automation error: {e}"

def browser_click_nth_item(url: str, nth: int = 1) -> str:
    """Click the nth search result item on an e-commerce page."""
    sync_playwright, err = _check_playwright()
    if err:
        return err
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    try:
        with sync_playwright() as p:
            browser = _launch_chromium(p, headless=True)
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            page.goto(url, timeout=20000, wait_until="networkidle")
            selectors = {
                "flipkart": "a[data-id]", "amazon": "div[data-component-type='s-search-result']", "myntra": "li.productCardImg", "ajio": "a.productCardImg",
            }
            base = url.lower()
            selector = next((sel for site, sel in selectors.items() if site in base), "a[href*='/p/']")
            try:
                page.wait_for_selector(selector, timeout=5000)
            except Exception:
                pass
            items = page.query_selector_all(selector)
            if nth <= 0 or nth > len(items):
                browser.close()
                return f"❌ Item {nth} not found. Found {len(items)} items total."
            item = items[nth - 1]
            try:
                item_url = item.get_attribute("href") if item.evaluate("node => node.tagName") == "A" else (item.query_selector("a").get_attribute("href") if item.query_selector("a") else None)
                if item_url and not item_url.startswith("http"):
                    from urllib.parse import urljoin
                    item_url = urljoin(url, item_url)
                title = page.title()
                browser.close()
                return f"✅ Found item {nth}.\n🌐 **{title}**\n📎 {item_url or url}"
            except Exception as inner_e:
                browser.close()
                return f"❌ Error extracting link: {inner_e}"
    except Exception as e:
        return f"❌ Click error: {e}"

def browser_add_to_cart(url: str) -> str:
    """Add current item to cart."""
    sync_playwright, err = _check_playwright()
    if err:
        return err
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    try:
        with sync_playwright() as p:
            browser = _launch_chromium(p, headless=True)
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            page.goto(url, timeout=20000, wait_until="networkidle")
            cart_selectors = [
                "button:has-text('ADD TO CART')", "button:has-text('Add to Cart')", "button:has-text('add to cart')",
                "button[data-action='add-to-cart']", "a[data-action='add-to-cart']",
                "button._2KpZ6l._2U9uOA._3v1-ww", "button.QqFHMw", "input#add-to-cart-button", 
            ]
            added = False
            for sel in cart_selectors:
                try:
                    btn = page.query_selector(sel)
                    if btn and btn.is_visible():
                        btn.click()
                        page.wait_for_timeout(2000)
                        added = True
                        break
                except Exception:
                    continue
            browser.close()
            return "✅ Added to cart!" if added else "⚠️ Could not find 'Add to Cart' button. Please check manually."
    except Exception as e:
        return f"❌ Cart error: {e}"
