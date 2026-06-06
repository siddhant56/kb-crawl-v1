"""
Concurrent Playwright crawler for radixweb.com.

Architecture:
  - asyncio.Queue seeded with ALL sitemap URLs (no slicing).
  - N workers share the queue; each runs its own Playwright page.
  - asyncio.Queue.join() means the crawl only finishes when every URL
    has been processed — including URLs discovered dynamically during
    the crawl itself.
  - max_pages is a safety ceiling, not a queue filter.
"""

import asyncio
import random
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from playwright.async_api import async_playwright, BrowserContext, Page

from .state import scrape_state, scrape_lock
from .categorizer import (
    RADIXWEB_BASE,
    normalize_url,
    should_skip,
    categorize_url,
    url_to_filename,
)
from .extractor import extract_content
from .converter import to_markdown
from .sitemap import fetch_all_sitemap_urls

KNOWLEDGE_BASE_PATH = Path(__file__).parent.parent / "knowledge-base"

MAX_PAGES = 10_000     # safety ceiling; site has ~1 961 URLs
WORKERS = 3            # concurrent browser pages
DELAY_MIN = 0.8        # seconds of polite delay per worker
DELAY_MAX = 1.8
PAGE_TIMEOUT = 40_000  # ms
NETWORK_IDLE_TIMEOUT = 10_000
MAX_RETRIES = 1

CHROME_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)

# Hide Playwright's webdriver fingerprint before any page script runs
_STEALTH_JS = """
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
Object.defineProperty(navigator, 'plugins',   { get: () => [1, 2, 3] });
Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
window.chrome = { runtime: {} };
"""

# Block heavy media; keep CSS + fonts so browser fingerprint looks normal
_BLOCK_MEDIA = re.compile(
    r"\.(jpe?g|gif|webp|ico|mp4|mp3|webm|avi|mov)(\?.*)?$",
    re.IGNORECASE,
)


async def _route_handler(route, request):
    if _BLOCK_MEDIA.search(request.url):
        await route.abort()
    else:
        await route.continue_()


async def _discover_links(page: Page) -> list[str]:
    """
    Extract every internal link from the rendered DOM — including links
    inside hidden/collapsed elements (dropdown menus, off-canvas navs).
    """
    try:
        hrefs: list[str] = await page.evaluate(
            """() => Array.from(document.querySelectorAll('a[href]'))
                         .map(a => a.href)
                         .filter(h => h && !h.startsWith('javascript:')
                                        && !h.startsWith('mailto:')
                                        && !h.startsWith('tel:'))"""
        )
    except Exception:
        return []

    seen: set[str] = set()
    links: list[str] = []
    for href in hrefs:
        norm = normalize_url(href)
        if norm and norm not in seen and not should_skip(norm):
            seen.add(norm)
            links.append(norm)
    return links


async def _load_page(page: Page, url: str, attempt: int = 0) -> Optional[str]:
    """Navigate to url, wait for JS, return fully-rendered HTML or None."""
    try:
        resp = await page.goto(url, wait_until="domcontentloaded", timeout=PAGE_TIMEOUT)
        if resp is None or resp.status >= 400:
            return None
        if "text/html" not in resp.headers.get("content-type", ""):
            return None

        # Let JS finish
        try:
            await page.wait_for_load_state("networkidle", timeout=NETWORK_IDLE_TIMEOUT)
        except Exception:
            pass  # timeout is acceptable — page is usually ready enough

        # Scroll to trigger lazy-loaded / deferred React sections
        try:
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(0.3)
        except Exception:
            pass

        return await page.content()

    except Exception as exc:
        if attempt < MAX_RETRIES:
            await asyncio.sleep(2.0)
            return await _load_page(page, url, attempt + 1)
        print(f"    [skip] {url}  ({exc})")
        return None


def _save(url: str, markdown: str) -> str:
    """Write Markdown to knowledge-base/{category}/slug.md. Returns category."""
    category = categorize_url(url)
    folder = KNOWLEDGE_BASE_PATH / category
    folder.mkdir(parents=True, exist_ok=True)
    (folder / url_to_filename(url)).write_text(markdown, encoding="utf-8")
    return category


async def _worker(
    worker_id: int,
    context: BrowserContext,
    url_queue: asyncio.Queue,
    visited: set,
    visit_lock: asyncio.Lock,
    max_pages: int,
) -> None:
    """One worker: pulls URLs from the queue, scrapes, enqueues discovered links."""
    page = await context.new_page()
    try:
        while True:
            url = await url_queue.get()      # blocks until an item is available
            if url is None:                  # sentinel — time to stop
                url_queue.task_done()
                break

            try:
                # Skip if already seen or over the page limit
                async with visit_lock:
                    if url in visited or len(visited) >= max_pages:
                        continue
                    visited.add(url)
                    n = len(visited)

                scrape_state.current_url = url
                print(f"  [W{worker_id}][{n}] {url}")

                html = await _load_page(page, url)
                if html is None:
                    scrape_state.pages_skipped += 1
                    continue

                # Discover links from rendered DOM and enqueue new ones.
                # queue.put() increments Queue's unfinished counter so join()
                # correctly waits for these new URLs to be processed too.
                links = await _discover_links(page)
                new_count = 0
                async with visit_lock:
                    for link in links:
                        if link not in visited:
                            await url_queue.put(link)
                            new_count += 1
                if new_count:
                    print(f"    +{new_count} new links discovered")

                # Extract → Markdown → persist
                extracted = extract_content(html, url)
                markdown = to_markdown(extracted)

                if not markdown:
                    scrape_state.pages_skipped += 1
                    continue

                category = _save(url, markdown)
                scrape_state.pages_scraped += 1
                scrape_state.categories[category] = (
                    scrape_state.categories.get(category, 0) + 1
                )
                scrape_state.pages_discovered = url_queue.qsize() + n

                await asyncio.sleep(random.uniform(DELAY_MIN, DELAY_MAX))

            finally:
                url_queue.task_done()   # must always be called — even on skip

    finally:
        await page.close()


async def run_full_crawl(max_pages: int = MAX_PAGES, workers: int = WORKERS) -> None:
    """
    Main entry point. Acquires the global scrape lock, runs the concurrent
    crawl to completion, and releases the lock.

    Completion is defined by asyncio.Queue.join():
        every URL that entered the queue (sitemap + dynamically discovered)
        has been both processed and had task_done() called.
    """
    if not scrape_lock.acquire(blocking=False):
        raise RuntimeError("A scrape is already in progress.")

    try:
        scrape_state.reset()
        scrape_state.status = "running"
        scrape_state.started_at = datetime.now(timezone.utc).isoformat()

        # ── Phase 1: build queue from sitemap — guarantees ALL known URLs ──
        print("=" * 60)
        print("Phase 1: Fetching sitemap…")
        sitemap_urls = fetch_all_sitemap_urls(RADIXWEB_BASE)

        # Prepend homepage in case it's somehow absent
        homepage = normalize_url(RADIXWEB_BASE)
        seed: list[str] = []
        if homepage:
            seed.append(homepage)
        for u in sitemap_urls:
            if u not in seed:
                seed.append(u)

        url_queue: asyncio.Queue = asyncio.Queue()
        for u in seed:                 # NO slicing — every URL goes in
            await url_queue.put(u)

        scrape_state.pages_discovered = len(seed)
        print(f"Phase 2: Crawling {len(seed)} URLs with {workers} workers…")
        print("=" * 60 + "\n")

        # ── Phase 2: concurrent crawl ───────────────────────────────────────
        visited: set[str] = set()
        visit_lock = asyncio.Lock()

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--disable-blink-features=AutomationControlled",
                    "--disable-infobars",
                ],
            )
            ctx: BrowserContext = await browser.new_context(
                user_agent=CHROME_UA,
                viewport={"width": 1280, "height": 800},
                locale="en-US",
                timezone_id="America/New_York",
                java_script_enabled=True,
                extra_http_headers={
                    "Accept-Language": "en-US,en;q=0.9",
                    "Accept": (
                        "text/html,application/xhtml+xml,application/xml;"
                        "q=0.9,image/webp,*/*;q=0.8"
                    ),
                },
            )
            await ctx.add_init_script(_STEALTH_JS)
            await ctx.route("**/*", _route_handler)

            # Start N worker coroutines, each with its own browser page
            worker_tasks = [
                asyncio.create_task(
                    _worker(i + 1, ctx, url_queue, visited, visit_lock, max_pages)
                )
                for i in range(workers)
            ]

            # Block until EVERY queued URL is processed (including newly
            # discovered ones — asyncio.Queue.join() handles this correctly
            # because queue.put() increments the unfinished counter).
            await url_queue.join()

            # Send one sentinel per worker so they exit cleanly
            for _ in range(workers):
                await url_queue.put(None)

            await asyncio.gather(*worker_tasks)
            await browser.close()

        scrape_state.status = "completed"
        scrape_state.current_url = None
        scrape_state.completed_at = datetime.now(timezone.utc).isoformat()
        print(
            f"\n{'='*60}\n"
            f"Crawl complete: {scrape_state.pages_scraped} pages saved "
            f"across {len(scrape_state.categories)} categories.\n"
            f"Skipped: {scrape_state.pages_skipped}\n"
            f"{'='*60}"
        )

    except Exception as exc:
        scrape_state.status = "failed"
        scrape_state.error = str(exc)
        scrape_state.current_url = None
        print(f"Crawl failed: {exc}")
        raise

    finally:
        scrape_lock.release()
