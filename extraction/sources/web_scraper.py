"""
Web Scraper — Tier 4 Fallback for Unstructured Sources
=========================================================
Used ONLY when no API exists for a source.
Starts with httpx for static pages. Playwright is added
when JavaScript-rendered pages are needed.

Ethical constraints:
- Respects robots.txt
- Rate-limited (minimum 2 second delay between requests)
- No circumvention of paywalls or access controls
- Identifies itself honestly in User-Agent
"""

import httpx
import re
import time
from typing import Optional
from pathlib import Path
from extraction.source_interface import SourceResult

USER_AGENT = "DisruptiveAI-Ecosystem/1.0 (Research; mailto:ecosystem@disruptive.ai)"
MIN_DELAY = 2.0  # Minimum seconds between requests to same domain
_last_request_time: dict[str, float] = {}


def _rate_limit(domain: str):
    """Enforce minimum delay between requests to the same domain."""
    now = time.time()
    last = _last_request_time.get(domain, 0)
    wait = MIN_DELAY - (now - last)
    if wait > 0:
        time.sleep(wait)
    _last_request_time[domain] = time.time()


def _get_domain(url: str) -> str:
    """Extract domain from URL."""
    match = re.search(r"https?://([^/]+)", url)
    return match.group(1) if match else "unknown"


def check_robots_txt(url: str) -> bool:
    """Check if robots.txt allows scraping this URL.

    Returns True if scraping is allowed or robots.txt can't be fetched.
    """
    domain = _get_domain(url)
    robots_url = f"https://{domain}/robots.txt"

    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(robots_url, headers={"User-Agent": USER_AGENT})
            if resp.status_code != 200:
                return True  # No robots.txt = allowed

            text = resp.text.lower()
            # Simple check — look for Disallow: /
            if "disallow: /" in text and "disallow: / " not in text:
                # Check if it's for all user agents
                lines = text.split("\n")
                for i, line in enumerate(lines):
                    if "user-agent: *" in line:
                        for j in range(i + 1, min(i + 10, len(lines))):
                            if lines[j].strip() == "disallow: /":
                                return False  # Blocked
                            if lines[j].startswith("user-agent:"):
                                break
            return True
    except Exception:
        return True  # Can't fetch = assume allowed


def fetch_page(url: str, check_robots: bool = True) -> Optional[str]:
    """Fetch a web page and return its HTML content.

    Returns None if the page can't be fetched or robots.txt blocks it.
    """
    if check_robots and not check_robots_txt(url):
        print(f"  [Scraper] Blocked by robots.txt: {url}")
        return None

    domain = _get_domain(url)
    _rate_limit(domain)

    try:
        with httpx.Client(timeout=30.0, follow_redirects=True) as client:
            resp = client.get(url, headers={"User-Agent": USER_AGENT})
            resp.raise_for_status()
            return resp.text
    except httpx.HTTPError as e:
        print(f"  [Scraper] Fetch failed: {e}")
        return None


def extract_text_from_html(html: str) -> str:
    """Extract readable text from HTML, stripping tags and scripts."""
    # Remove script and style blocks
    text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
    # Remove HTML tags
    text = re.sub(r"<[^>]+>", " ", text)
    # Clean whitespace
    text = re.sub(r"\s+", " ", text).strip()
    # Decode HTML entities
    text = text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    text = text.replace("&quot;", '"').replace("&#39;", "'")
    return text


def scrape_to_result(url: str, source_type: str = "website") -> Optional[SourceResult]:
    """Scrape a URL and return a SourceResult with extracted content.

    This is for pages where we need the content but no API exists.
    """
    html = fetch_page(url)
    if not html:
        return None

    # Extract title
    title_match = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    title = title_match.group(1).strip() if title_match else url

    # Extract meta description
    desc_match = re.search(r'<meta[^>]+name=["\']description["\'][^>]+content=["\'](.*?)["\']', html, re.IGNORECASE)
    abstract = desc_match.group(1)[:500] if desc_match else ""

    # Extract main text content
    text = extract_text_from_html(html)

    return SourceResult(
        source_type=source_type,
        title=title[:200],
        abstract=abstract if abstract else text[:500],
        url=url,
        credibility_tier="tier4_scraped",
        has_open_access=True,
        source_api="web_scraper",
        raw_data={"full_text": text[:5000]},
    )


def download_file(url: str, output_dir: str = "data/downloads") -> Optional[Path]:
    """Download a file from a URL."""
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # Generate filename from URL
    filename = url.split("/")[-1].split("?")[0]
    if not filename:
        filename = "download"
    output_path = Path(output_dir) / filename

    if output_path.exists() and output_path.stat().st_size > 100:
        return output_path

    domain = _get_domain(url)
    _rate_limit(domain)

    try:
        with httpx.Client(timeout=60.0, follow_redirects=True) as client:
            resp = client.get(url, headers={"User-Agent": USER_AGENT})
            resp.raise_for_status()
            output_path.write_bytes(resp.content)
            return output_path
    except httpx.HTTPError as e:
        print(f"  [Scraper] Download failed: {e}")
        return None
