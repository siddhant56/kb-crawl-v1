# Key Functions Reference

This document is a quick-reference guide to the most important functions in the codebase — what they do, what they take, and what they return. Grouped by module.

---

## `scraper/sitemap.py`

### `fetch_all_sitemap_urls(base_url) → list[str]`

**What it does:** Recursively walks all sitemaps starting from `robots.txt` and returns a flat, deduplicated, filtered list of every page URL on the site.

**Key behaviour:**
- Handles sitemap indexes (a sitemap that points to other sitemaps).
- Filters every URL through `normalize_url()` and `should_skip()` before including it.
- Prints progress per sitemap file as it processes.

**When to call:** Once, at the start of a crawl — called internally by `run_full_crawl()`.

---

## `scraper/categorizer.py`

### `normalize_url(url, base) → Optional[str]`

**What it does:** Cleans and canonicalises a raw URL string for deduplication.

**Returns:** A clean canonical URL on the company domain, or `None` if the URL is external, malformed, or uses a non-HTTP scheme.

**Example:**
```python
normalize_url("https://www.company.com/services/?utm_source=google#section")
# → "https://company.com/services/"
```

---

### `should_skip(url) → bool`

**What it does:** Returns `True` for URLs that should never be scraped (binary files, CMS admin paths, legal pages, etc.).

**Example:**
```python
should_skip("https://company.com/logo.png")   # → True
should_skip("https://company.com/services/")  # → False
```

---

### `categorize_url(url) → str`

**What it does:** Maps a URL to a knowledge-base category folder name by matching the URL path against ordered regex rules.

**Returns:** One of: `blog`, `hire-developers`, `case-studies`, `industries`, `resources`, `about`, `company`, `services`, or a dynamic fallback (first path segment, or `"general"`).

**Example:**
```python
categorize_url("https://company.com/blog/python-tips")           # → "blog"
categorize_url("https://company.com/hire-python-developers")     # → "hire-developers"
categorize_url("https://company.com/services/cloud")             # → "services"
```

---

### `url_to_filename(url) → str`

**What it does:** Converts a URL to a safe `.md` filename by replacing slashes and stripping special characters.

**Example:**
```python
url_to_filename("https://company.com/services/python-development")
# → "services-python-development.md"
```

---

## `scraper/crawler.py`

### `run_full_crawl(max_pages=10000, workers=3) → None`  *(async)*

**What it does:** The main entry point for the scraper. Launches a concurrent Playwright crawl of the company website, saves every page as Markdown to `knowledge-base/`, and updates `scrape_state` with live progress.

**Parameters:**
- `max_pages` — hard ceiling on total pages visited (safety net; site has ~1,961 URLs).
- `workers` — number of concurrent browser pages. More = faster, but more memory and more likely to get rate-limited.

**Raises:** `RuntimeError` if a crawl is already in progress. Updates `scrape_state.status` to `"failed"` and re-raises any other exception.

**Important:** This is an `async` function. Call it with `await` or `asyncio.run()`.

---

### `_load_page(page, url, attempt=0) → Optional[str]`  *(async, internal)*

**What it does:** Navigates a Playwright `Page` object to `url` and returns the fully-rendered HTML string. Returns `None` on HTTP errors, non-HTML responses, or unrecoverable network errors.

**Key detail:** Scrolls to the bottom of the page before returning HTML — this triggers lazy-loaded React/Vue content that only renders when in the viewport.

---

### `_discover_links(page) → list[str]`  *(async, internal)*

**What it does:** Runs a JavaScript snippet in the browser to collect all `<a href>` values from the fully-rendered DOM. Returns only internal company domain links, filtered and normalised.

**Why it matters:** Discovers pages that aren't in the sitemap (e.g., links only reachable through JavaScript-rendered dropdown menus).

---

## `scraper/extractor.py`

### `extract_content(html, url) → dict`

**What it does:** Takes raw HTML from a fully-rendered page and strips all navigation, ads, scripts, cookie banners, and other boilerplate. Returns the main content area as a dict.

**Returns:**
```python
{
    "title": "Python Development Services",
    "description": "Meta description text...",
    "html": "<main>...cleaned HTML...</main>",
    "url": "https://company.com/services/python-development"
}
```

**Content selection priority:** `<main>` → `<article>` → `id="main"` → `id="content"` → `class="main-content"` → `<body>`.

---

## `scraper/converter.py`

### `to_markdown(extracted) → str`

**What it does:** Converts the dict from `extract_content()` into a formatted Markdown document ready for storage. Returns `""` if the body is shorter than 100 characters (stub page gate).

**Returns format:**
```markdown
# Page Title

> Meta description

**Source:** https://...

---

...body content...
```

---

## `implementation/answer.py`

### `answer_question(question, history=[]) → tuple[str, list[Document]]`

**What it does:** The top-level RAG function for the basic pipeline. Takes a question + chat history and returns an LLM-generated answer plus the retrieved context documents.

**Parameters:**
- `question` — the user's current question.
- `history` — list of `{"role": "user"|"assistant", "content": "..."}` dicts from prior turns.

**Returns:** `(answer_string, list_of_Document_objects)`

**Internally calls:** `combined_question()` → `fetch_context()` → `llm.invoke()`.

---

### `combined_question(question, history) → str`

**What it does:** Concatenates all prior user messages with the current question into a single string for retrieval. Ensures the vector search considers conversation context, not just the last message.

**Example:**
```python
history = [
    {"role": "user", "content": "Tell me about the company"},
    {"role": "assistant", "content": "The company is a..."}
]
question = "What about their Python services?"
# Returns: "Tell me about the company\nWhat about their Python services?"
```

---

## `pro_implementation/ingest.py`

### `fetch_documents() → list[dict]`

**What it does:** Walks `knowledge-base/` and reads every `.md` file. Returns a list of dicts with `type`, `source`, and `text` keys. This is a hand-rolled version of LangChain's `DirectoryLoader`.

---

### `process_document(document) → list[Result]`

**What it does:** Sends one document to the LLM and gets back structured chunks (each with a `headline`, `summary`, and `original_text`). This is the core of the LLM-powered chunking strategy.

**Decorated with `@retry`** — automatically retries with exponential backoff on API errors.

**LLM model:** `openai/gpt-4.1-nano` (via LiteLLM). Uses `response_format=Chunks` to get JSON output directly.

---

### `create_chunks(documents) → list[Result]`

**What it does:** Calls `process_document()` for every document in parallel using `multiprocessing.Pool` with `WORKERS=3`. Shows a `tqdm` progress bar.

**Note:** Uses `pool.imap_unordered()` — results come back in completion order (whichever document the LLM finishes first), not input order. This doesn't matter because order isn't significant for the vector store.

---

### `create_embeddings(chunks)`

**What it does:** Deletes the existing vector database (if any), batches all chunk texts into a single OpenAI embeddings API call, then stores all chunks in ChromaDB.

**Key detail:** All embeddings are fetched in **one API call** (`openai.embeddings.create(input=all_texts)`). This is much more efficient than calling the API once per chunk.

---

## `pro_implementation/answer.py`

### `answer_question(question, history=[]) → tuple[str, list]`  *(decorated with @retry)*

**What it does:** The top-level function for the pro pipeline. Runs the full retrieval pipeline (query rewrite → dual retrieval → merge → re-rank) then generates the answer.

**Returns:** `(answer_string, list_of_Result_objects)`

---

### `rewrite_query(question, history=[]) → str`  *(decorated with @retry)*

**What it does:** Asks the LLM to produce a short, dense query optimised for vector search — converting a conversational user question into a knowledge-base search query.

**Why it matters:** User questions are often vague, conversational, or context-dependent ("what about their pricing?"). The rewritten query is more likely to surface the right chunks from the vector DB.

---

### `fetch_context(original_question) → list[Result]`

**What it does:** The full retrieval pipeline:
1. `rewrite_query()` → short search query.
2. `fetch_context_unranked(original_question)` → 20 chunks.
3. `fetch_context_unranked(rewritten_question)` → 20 more chunks.
4. `merge_chunks()` → up to ~40 unique chunks.
5. `rerank()` → LLM sorts by relevance.
6. Returns top `FINAL_K = 10`.

---

### `rerank(question, chunks) → list[Result]`  *(decorated with @retry)*

**What it does:** Sends all merged chunks to the LLM in a single call. The LLM returns a `RankOrder` — a list of integer chunk IDs ordered from most to least relevant. The function returns the chunks in that order.

**Why it matters:** Vector similarity alone doesn't always surface the best chunks — a chunk can be lexically close to the query but not actually answer it. LLM re-ranking adds a semantic understanding layer on top of embedding similarity.

**Model used:** `groq/openai/gpt-oss-120b` via LiteLLM. Uses `response_format=RankOrder` for structured output.

---

## `api.py`

### `perform_ingestion() → bool`

**What it does:** Thread-safe wrapper for the pro ingestion pipeline. Acquires `ingest_lock`, runs `fetch_documents` → `create_chunks` → `create_embeddings`, then releases the lock.

**Returns:** `True` on success, `False` if already running or on any error.

**Called by:** `POST /api/ingest`, `POST /api/pipeline/run`, and the hourly scheduler.

---

## `app.py`

### `build_app() → gr.Blocks`

**What it does:** Constructs and returns the Gradio `Blocks` UI. The UI has:
- Left column: `gr.Chatbot` (conversation history) + `gr.Textbox` (input).
- Right column: `gr.Markdown` (retrieved context display).

**Event flow:**
1. `message.submit` fires `put_message_in_chatbot()` — appends the user message to history, clears the input box.
2. `.then` fires `chat()` — calls `answer_question()`, appends the assistant reply, updates the context panel.

### `chat(history) → tuple[list, str]`

**What it does:** Extracts the last user message from history, calls `answer_question()`, appends the assistant response to history, and formats the context documents as HTML for the right panel.

**Returns:** `(updated_history, formatted_context_html)`
