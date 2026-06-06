# Scraper Module — Deep Dive

The scraper lives in `scraper/` and turns the entire company website into a local folder of Markdown files. It is driven by **Playwright** (a headless Chromium browser) so JavaScript-rendered content is fully captured.

---

## End-to-End Flow

```
fetch_all_sitemap_urls()          ← scraper/sitemap.py
        │
        ▼ list of ~1,961 URLs
asyncio.Queue  ◄──────────────── dynamically discovered links added here too
        │
        ▼  N concurrent workers
  _worker()                       ← scraper/crawler.py
        │
        ├─ _load_page()           navigate, wait for JS, scroll
        ├─ _discover_links()      extract new internal links from rendered DOM
        ├─ extract_content()      ← scraper/extractor.py  (strip boilerplate)
        ├─ to_markdown()          ← scraper/converter.py  (HTML → Markdown)
        └─ _save()                write to knowledge-base/{category}/{slug}.md
                                  category from categorize_url()  ← scraper/categorizer.py
```

---

## `scraper/sitemap.py` — URL Discovery

**Purpose:** Build a complete seed list of URLs before crawling starts, so nothing is missed.

### `fetch_all_sitemap_urls(base_url) → list[str]`

1. Reads `robots.txt` looking for `Sitemap:` directives. Falls back to `/sitemap.xml` if none found.
2. Recursively parses sitemap index files (a sitemap can point to other sitemaps).
3. Deduplicates and filters every URL through `normalize_url()` and `should_skip()`.
4. Returns a flat list of every scrapable page URL on the site (~1,961 pages).

This is called once at the start of `run_full_crawl()` to seed the asyncio queue.

---

## `scraper/categorizer.py` — URL Routing

**Purpose:** Decide which `knowledge-base/` subfolder a URL belongs to, and generate a safe filename for it.

### `CATEGORY_RULES`

An ordered list of `(regex_pattern, category_name)` tuples. The first matching pattern wins. Key ordering decisions:

- Blog/news patterns come **first** so `/company-news/*` isn't swallowed by the generic company rule.
- "Hire developers" patterns come before the generic `-development` suffix rule.
- Services come **last** as a broad catch-all.

Categories produced: `blog`, `hire-developers`, `case-studies`, `industries`, `resources`, `about`, `company`, `services`.

### `normalize_url(url, base) → Optional[str]`

Cleans a raw URL for deduplication:
- Resolves relative URLs against `base` (the company's base URL).
- Rejects anything that isn't on the company domain (strips `www.` too).
- Strips tracking query params: `utm_source`, `utm_medium`, `gclid`, `fbclid`, etc.
- Strips URL fragments (`#section`).
- Normalises scheme to `https`.

### `should_skip(url) → bool`

Returns `True` for URLs that should never be scraped:
- Binary file extensions: `.pdf`, `.jpg`, `.png`, `.js`, `.css`, etc.
- CMS admin paths: `/wp-admin/`, `/wp-login`.
- XML/JSON files, sitemap files.
- Legal boilerplate: `/privacy-policy`, `/terms-of-use`.

### `categorize_url(url) → str`

Applies `CATEGORY_RULES` in order. Returns the category string. Falls back to the first URL path segment if nothing matches.

### `url_to_filename(url) → str`

Converts a URL to a safe `.md` filename:
- Takes the URL path, replaces `/` with `-`, removes unsafe characters.
- Caps at 180 characters.
- Appends an MD5 hash suffix if the URL has a query string (to avoid collisions).
- Always ends with `.md`.

**Example:** `https://company.com/services/python-development` → `services-python-development.md`

---

## `scraper/state.py` — Shared State

**Purpose:** A single global object that tracks the live progress of the current crawl. Needed because the crawl runs in a background asyncio task while the API must serve status queries synchronously.

### `ScrapeState` dataclass

| Field | Type | Description |
|---|---|---|
| `status` | `str` | `idle` / `running` / `completed` / `failed` |
| `pages_scraped` | `int` | Pages successfully saved to disk |
| `pages_discovered` | `int` | Total URLs seen (queue size + visited) |
| `pages_skipped` | `int` | Pages that returned errors or empty content |
| `current_url` | `Optional[str]` | URL currently being fetched by any worker |
| `categories` | `dict` | `{category: page_count}` breakdown |
| `error` | `Optional[str]` | Error message if status is `failed` |
| `started_at` | `Optional[str]` | ISO 8601 timestamp |
| `completed_at` | `Optional[str]` | ISO 8601 timestamp |

`scrape_lock` is a `threading.Lock` used to ensure only one crawl runs at a time (the FastAPI endpoint checks `scrape_lock.locked()` before starting).

---

## `scraper/crawler.py` — The Crawler

**Purpose:** The main crawler engine. Runs N Playwright pages concurrently via asyncio.

### `run_full_crawl(max_pages, workers)`

The public entry point. Called by `api.py` and `run_crawl.py`.

1. Acquires `scrape_lock` — ensures only one crawl is active.
2. Resets `scrape_state` to a clean slate.
3. Calls `fetch_all_sitemap_urls()` to get all known URLs.
4. Seeds an `asyncio.Queue` with every URL (no slicing — all ~1,961 go in).
5. Launches N `_worker()` coroutines, each with its own Playwright page.
6. Calls `queue.join()` — blocks until every URL in the queue (including ones dynamically added during crawl) has been processed.
7. Sends `None` sentinels to stop workers cleanly.
8. Updates `scrape_state.status` to `completed` or `failed`.

**Key design:** `asyncio.Queue.join()` is used instead of a fixed iteration. Because workers enqueue newly discovered links via `queue.put()`, `join()` automatically waits for those too. This means the crawl is truly exhaustive — it won't finish until both the sitemap URLs and every link discovered dynamically have been visited.

### `_worker(worker_id, context, url_queue, visited, visit_lock, max_pages)`

One worker coroutine. Runs in a loop:
1. `await url_queue.get()` — blocks until a URL is available.
2. Checks `visited` set under `visit_lock` to skip duplicates.
3. Calls `_load_page()`.
4. Calls `_discover_links()` and enqueues any new URLs found.
5. Calls `extract_content()` → `to_markdown()` → `_save()`.
6. Always calls `url_queue.task_done()` even if the page was skipped (required for `queue.join()` to work correctly).

### `_load_page(page, url, attempt) → Optional[str]`

Navigates to a URL and returns the fully-rendered HTML:
1. `page.goto()` with `wait_until="domcontentloaded"`.
2. Waits for `networkidle` (up to 10 s) to let deferred JS finish.
3. Scrolls to the bottom of the page to trigger lazy-loaded React sections.
4. Retries once on failure (`MAX_RETRIES = 1`).
5. Returns `None` for HTTP 4xx/5xx, non-HTML content, or unrecoverable errors.

### `_discover_links(page) → list[str]`

Evaluates JavaScript in the page context to extract every `<a href>` from the fully-rendered DOM (including hidden dropdowns and off-canvas navs). Filters through `normalize_url()` and `should_skip()`.

### Browser Fingerprint Hardening

The browser is launched with flags to avoid bot detection:
- `--disable-blink-features=AutomationControlled` — removes the `navigator.webdriver` flag.
- Custom `User-Agent` mimicking Chrome 131 on macOS.
- `add_init_script(_STEALTH_JS)` — overrides `navigator.webdriver`, `navigator.plugins`, and `navigator.languages` before any page script runs.
- Realistic `Accept-Language` and `Accept` headers.
- Heavy media (`.jpg`, `.gif`, `.mp4`) is aborted via route interception to save bandwidth.

---

## `scraper/extractor.py` — Content Extraction

**Purpose:** Strip navigation, ads, cookie banners, and other boilerplate from raw HTML, leaving only the main article content.

### `extract_content(html, url) → dict`

Returns `{"title": ..., "description": ..., "html": ..., "url": ...}`.

Steps:
1. **Title** — prefers `og:title` meta tag; falls back to `<title>`, stripping the site name suffix (e.g. ` | Company Name`).
2. **Description** — reads `<meta name="description">`.
3. **Technical tag removal** — deletes `<script>`, `<style>`, `<noscript>`, `<iframe>`, `<svg>`, `<canvas>`, `<template>`.
4. **Structural boilerplate removal** — deletes `<header>`, `<footer>`, `<nav>`, `<aside>`.
5. **Class/ID heuristic removal** — removes any element whose `class` or `id` contains keywords like `navbar`, `cookie`, `popup`, `modal`, `sidebar`, `advertisement`, `chat-widget`, etc.
6. **Main content selection** — tries `<main>`, then `<article>`, then `id="main"`, then `id="content"`, then `class="main-content"`, then falls back to `<body>`.

### Important constants

`_BOILERPLATE_KEYWORDS` — the list of class/id substrings that trigger element removal. Adding a word here will strip more aggressively. Examples: `"intercom"`, `"back-to-top"`, `"newsletter"`.

---

## `scraper/converter.py` — Markdown Conversion

**Purpose:** Convert the cleaned HTML fragment from `extractor.py` into a clean Markdown document.

### `to_markdown(extracted) → str`

Uses the `html2text` library with these settings:
- `ignore_links = True` — drops raw URLs from the output (reduces noise in RAG chunks).
- `ignore_images = True` — drops image references.
- `body_width = 0` — no hard line-wrapping (preserves natural paragraph flow).
- `unicode_snob = True` — keeps Unicode characters instead of ASCII approximations.

After conversion, `_clean_markdown()` collapses 3+ consecutive blank lines into 2, strips trailing whitespace, and normalises horizontal rules.

**Minimum content gate:** if the converted Markdown body is shorter than 100 characters, `to_markdown()` returns `""` and the crawler skips the page (`pages_skipped += 1`). This prevents stub pages from polluting the knowledge base.

**Output format:**
```
# Page Title

> Meta description

**Source:** https://company.com/...

---

...main body markdown...
```
