"""
Parse radixweb.com sitemap(s) to get a complete list of page URLs
before crawling begins — far more reliable than BFS link-discovery.
"""

import requests
from xml.etree import ElementTree
from typing import Optional

from .categorizer import RADIXWEB_BASE, normalize_url, should_skip

_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)
_HEADERS = {"User-Agent": _UA, "Accept-Language": "en-US,en;q=0.9"}


def _fetch(url: str) -> Optional[bytes]:
    try:
        r = requests.get(url, headers=_HEADERS, timeout=15)
        r.raise_for_status()
        return r.content
    except Exception as e:
        print(f"  [sitemap] Cannot fetch {url}: {e}")
        return None


def _parse_xml(content: bytes) -> tuple[list[str], list[str]]:
    """Return (page_urls, child_sitemap_urls) from a sitemap document."""
    try:
        root = ElementTree.fromstring(content)
    except Exception as e:
        print(f"  [sitemap] XML parse error: {e}")
        return [], []

    tag = root.tag.split("}")[-1] if "}" in root.tag else root.tag
    pages, subs = [], []

    for child in root:
        child_tag = child.tag.split("}")[-1]

        if child_tag in ("url", "sitemap"):
            for sub in child:
                sub_tag = sub.tag.split("}")[-1]
                if sub_tag == "loc" and sub.text:
                    url = sub.text.strip()
                    if child_tag == "sitemap":
                        subs.append(url)
                    else:
                        pages.append(url)

    return pages, subs


def fetch_all_sitemap_urls(base_url: str = RADIXWEB_BASE) -> list[str]:
    """
    Returns a deduplicated, filtered list of every scrapable page URL
    found across the site's sitemap chain (handles sitemap indexes).
    """
    # Check robots.txt for Sitemap: entries
    sitemap_seeds: list[str] = []
    try:
        robots = requests.get(
            base_url.rstrip("/") + "/robots.txt",
            headers=_HEADERS,
            timeout=10,
        ).text
        for line in robots.splitlines():
            if line.lower().startswith("sitemap:"):
                sitemap_seeds.append(line.split(":", 1)[1].strip())
    except Exception:
        pass

    if not sitemap_seeds:
        sitemap_seeds = [base_url.rstrip("/") + "/sitemap.xml"]

    visited_sitemaps: set[str] = set()
    queue = list(sitemap_seeds)
    all_page_urls: list[str] = []

    while queue:
        sm_url = queue.pop(0)
        if sm_url in visited_sitemaps:
            continue
        visited_sitemaps.add(sm_url)

        content = _fetch(sm_url)
        if not content:
            continue

        pages, subs = _parse_xml(content)
        all_page_urls.extend(pages)
        queue.extend(s for s in subs if s not in visited_sitemaps)

        print(f"  [sitemap] {sm_url}  →  {len(pages)} pages, {len(subs)} sub-sitemaps")

    # Deduplicate and filter
    seen: set[str] = set()
    result: list[str] = []
    for url in all_page_urls:
        norm = normalize_url(url)
        if norm and norm not in seen and not should_skip(norm):
            seen.add(norm)
            result.append(norm)

    print(f"  [sitemap] Total unique scrapable URLs: {len(result)}")
    return result
