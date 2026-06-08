# RAG Pipeline: Create → Retrieve → Answer Flow

## Overview

The PRO pipeline runs in two phases. **Ingestion** (offline) builds two parallel search indexes from the knowledge base. **Query** (online, per user message) runs five sequential stages — query rewriting, four-signal retrieval, RRF fusion, cross-encoder reranking, and LLM generation — to produce a grounded answer.

---

## Phase 1 — Ingestion

Entry point: `pro_implementation/ingest.py`  
Triggered by: `POST /api/ingest`, `POST /api/pipeline/run`, or the hourly APScheduler job.

### Step 1 — Load documents (`fetch_documents`)

Every subfolder in `knowledge-base/` is treated as a **doc type** (e.g. `about`, `leadership`, `blog`, `services`). Every `.md` file inside is loaded and tagged:

```python
{"type": "leadership", "source": "knowledge-base/leadership/cto.md", "text": "..."}
```

The folder name becomes the type tag. This tag is stored on every chunk and drives authoritative filtering during retrieval.

---

### Step 2 — Chunking (`chunk_document` → `create_chunks`)

Each document is split in two passes:

**Pass 1 — Markdown header split** (`MarkdownHeaderTextSplitter`)  
Splits on `#` `##` `###` `####`. Each section becomes an independent unit with its heading path in metadata, e.g. `{"h1": "Our Team", "h2": "Engineering"}`.

**Pass 2 — Character split** (`RecursiveCharacterTextSplitter`)  
Each header section is further split into chunks of **600 chars** with **150 char overlap**. Chunks under 40 chars are discarded.

**Breadcrumb injection**  
Before storing, the heading path is prepended to each chunk body so every chunk is self-contained:

```
Our Team > Engineering

Siddhant leads the backend platform team...
```

If a document has no headers at all, the pipeline falls back to pure character splitting.

---

### Step 3 — Build two indexes (`create_embeddings`)

**Index A — ChromaDB vector store** (`preprocessed_db/`)

- All chunk texts are sent to OpenAI `text-embedding-3-small` in batches of 500
- Each 1536-dim vector is stored with the chunk text and `{source, type}` metadata
- The collection is fully deleted and rebuilt on every ingestion run
- ChromaDB receives data in batches of 5000 (hard limit is 5461 per call)

**Index B — TF-IDF matrix** (`bm25_index.pkl`)

- Fits `TfidfVectorizer(ngram_range=(1,2), min_df=1, sublinear_tf=True)`
- `ngram_range=(1,2)` captures both single words and two-word phrases (catches product names like "Node.js development")
- `sublinear_tf=True` applies log-normalization to term frequency, mimicking BM25's term saturation — high-frequency terms stop gaining proportionally more weight
- The fitted vectorizer, sparse matrix, raw texts, and metadatas are pickled to disk
- `reload_bm25()` is called immediately after writing to refresh the in-memory globals in the running process

---

## Phase 2 — Query (per user message)

Entry point: `answer_question(question, history)` in `pro_implementation/answer.py`

### Step 1 — Query rewriting (`rewrite_query`)

The raw user question and conversation history are sent to `gpt-4.1-nano`:

> "Respond ONLY with a short, precise search query optimized to retrieve the most relevant content."

**Why**: User questions are conversational and context-dependent (`"what about their pricing?"`). The rewritten query is a standalone retrieval-optimized string (`"Radixweb software development pricing packages"`). This runs in parallel with the first vector search to avoid adding latency.

---

### Step 2 — Four parallel retrieval calls (`fetch_context`)

Retrieval runs in two waves to minimise wall-clock time.

**Wave 1** (2 threads in parallel):
| Signal | Input | Output |
|--------|-------|--------|
| `vec1` | `fetch_vector_results(original_question)` | top 15 by cosine similarity |
| rewrite | `rewrite_query(question, history)` | rewritten query string |

**Wave 2** (3 threads in parallel, using the rewritten query from Wave 1):
| Signal | Input | Output |
|--------|-------|--------|
| `vec2` | `fetch_vector_results(rewritten_query)` | top 15 by cosine similarity |
| `lex1` | `fetch_tfidf_results(original_question)` | top 15 by TF-IDF cosine similarity |
| `lex2` | `fetch_tfidf_results(rewritten_query)` | top 15 by TF-IDF cosine similarity |

Each signal returns at most **RETRIEVAL_K = 15** results → up to **60 raw candidates** enter the merge step.

**Why four signals?**  
Semantic (vec) retrieval is good at meaning, weak on exact terms. TF-IDF (lex) is the opposite. Running both on both query forms compensates for each method's blind spots and improves recall before the expensive reranking step.

---

### Step 3 — Reciprocal Rank Fusion with authority boost (`rrf_merge`)

All four ranked lists are merged into a single score. For each chunk, across every list it appears in:

```
score += 1 / (RRF_K + rank + 1)     # RRF_K = 60
```

`RRF_K = 60` is the standard constant. It flattens the score curve — the difference between rank 1 (`1/61 ≈ 0.0164`) and rank 10 (`1/71 ≈ 0.0141`) is small, so no single list dominates. A chunk appearing in multiple lists accumulates scores from each.

**Authority boost**: Chunks from `about` or `leadership` type documents have their per-list contribution **doubled** before accumulation. A leadership page ranked #5 in two lists will outscore a blog page ranked #1 in two lists.

The list is sorted descending by total RRF score.

---

### Step 4 — Source diversity cap

Iterates the RRF-sorted list and enforces two rules:

1. **Exact dedup** — skip if the chunk text was already collected
2. **Per-source cap** — at most **2 chunks per source file**

Stops once **RETRIEVAL_K = 15** candidates are collected.

**Why**: Without this, a highly relevant document with many chunks would fill most of the candidate slots with near-duplicate content from the same page, starving other relevant sources.

---

### Step 5 — Cross-encoder reranking with authoritative floor (`cross_encode_rerank`)

The 15 candidates are reranked by `cross-encoder/ms-marco-MiniLM-L-6-v2`, running locally on MPS (Apple Silicon) or CPU.

**What the cross-encoder does**: Unlike the embedding model, which scores query and chunk independently, the cross-encoder takes the `(question, chunk)` pair as a single input and outputs a relevance score. Significantly more accurate but too slow to run on thousands of candidates — that is why it only sees the top 15.

**Authoritative floor filter**:
1. Find the highest raw cross-encoder score among all `about`/`leadership` chunks
2. Drop any non-authoritative chunk that scores **below** that best authoritative score

If a leadership chunk scores 3.2, any blog chunk below 3.2 is removed entirely — even if RRF ranked it highly. This prevents outdated blog posts from surviving into the final context when a canonical source already covers the topic.

The remaining chunks are sorted by raw cross-encoder score, descending. The top **FINAL_K = 10** are returned.

---

### Step 6 — Context assembly (`make_rag_messages`)

Each of the 10 chunks is labeled based on its doc type:

```
Extract from [AUTHORITATIVE — leadership] knowledge-base/leadership/cto.md:
<chunk text>

Extract from [BLOG — may contain outdated info] knowledge-base/blog/team-2022.md:
<chunk text>
```

The labels are passed to the LLM so it knows which sources to trust when they conflict.

**Conversation history is intentionally excluded from the messages.** History was already used in query rewriting (Step 1) so follow-up questions resolve correctly. Previous LLM answers never enter the factual context window — only the live KB extracts do.

---

### Step 7 — LLM answer generation

`gpt-4.1-nano` receives:

| Role | Content |
|------|---------|
| `system` | `SYSTEM_PROMPT` with the 10 labeled KB extracts injected |
| `user` | Original raw question |

The system prompt instructs the model:
- KB extracts are absolute ground truth and override anything in conversation history
- `[AUTHORITATIVE]` sources beat `[BLOG]` sources when they contradict
- Answer only from the KB; say "I don't know" if the answer is not covered

The response text is returned alongside the 10 chunks so the UI can display the retrieved context panel.

---

## Full Data Flow

```
User question + history
        │
        ▼
┌──────────────────────────────────────────────────────┐
│  Wave 1 (parallel)                                   │
│  rewrite_query(q, history)  ─────────► rewritten_q  │
│  fetch_vector_results(q)    ─────────► vec1 [≤15]   │
└──────────────────────────────────────────────────────┘
        │
        ▼
┌──────────────────────────────────────────────────────┐
│  Wave 2 (parallel)                                   │
│  fetch_vector_results(rewritten_q)  ──► vec2 [≤15]  │
│  fetch_tfidf_results(q)             ──► lex1 [≤15]  │
│  fetch_tfidf_results(rewritten_q)   ──► lex2 [≤15]  │
└──────────────────────────────────────────────────────┘
        │
        ▼  up to 60 raw candidates
┌──────────────────────────────────────────────────────┐
│  RRF merge                                           │
│  score = Σ  1 / (60 + rank + 1)                     │
│  authority boost: ×2 for about / leadership types    │
└──────────────────────────────────────────────────────┘
        │
        ▼  deduplicated, max 2 per source file → 15 candidates
┌──────────────────────────────────────────────────────┐
│  Cross-encoder rerank  (ms-marco-MiniLM-L-6-v2)     │
│  Score all 15 (question, chunk) pairs                │
│  Drop non-auth chunks below best auth score          │
│  Sort by cross-encoder score descending              │
└──────────────────────────────────────────────────────┘
        │
        ▼  top 10
┌──────────────────────────────────────────────────────┐
│  Assemble messages                                   │
│  Label each chunk [AUTHORITATIVE] or [BLOG/other]   │
│  system: SYSTEM_PROMPT + 10 labeled extracts         │
│  user:   original question                           │
└──────────────────────────────────────────────────────┘
        │
        ▼
   gpt-4.1-nano  ──►  answer text  +  10 source chunks
```

---

## Key Constants

| Constant | Value | Purpose |
|----------|-------|---------|
| `RETRIEVAL_K` | 15 | Candidates returned per retrieval signal; also the post-diversity-cap target |
| `FINAL_K` | 10 | Chunks passed to the LLM after reranking |
| `RRF_K` | 60 | Rank fusion dampening constant (standard value) |
| `chunk_size` | 600 chars | Max characters per chunk before overlap |
| `chunk_overlap` | 150 chars | Overlap between adjacent chunks to preserve context at boundaries |
| `MAX_PER_SOURCE` | 2 | Max chunks allowed from a single source file |
| `embedding_model` | `text-embedding-3-small` | OpenAI model used for vector indexing and query embedding |
| `MODEL` | `openai/gpt-4.1-nano` | LLM used for query rewriting and answer generation |

---

## Authoritative Types

Documents in the `about/` and `leadership/` knowledge-base folders are classified as authoritative (`AUTHORITATIVE_TYPES = {"about", "leadership"}`). They receive a **2× RRF score boost** and set a **minimum cross-encoder score floor** that non-authoritative chunks must exceed to survive into the final context.
