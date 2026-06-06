# RAG Pipelines — Deep Dive

There are two RAG pipelines in this project. Both read from `knowledge-base/` and write to a ChromaDB vector store, but they differ significantly in chunking strategy, retrieval quality, and LLM usage.

---

## Basic Pipeline (`implementation/`)

A straightforward LangChain-based RAG pipeline. Good for quick iteration.

**Vector store location:** `vector_db/`

---

### `implementation/ingest.py`

#### `fetch_documents() → list[Document]`

Uses LangChain's `DirectoryLoader` with `TextLoader` to walk every subfolder of `knowledge-base/`, loading all `*.md` files. Each `Document` gets a `doc_type` metadata field set to the folder name (e.g., `"services"`, `"blog"`).

#### `create_chunks(documents) → list[Document]`

Splits documents with `RecursiveCharacterTextSplitter`:
- `chunk_size = 500` characters
- `chunk_overlap = 200` characters

This is a naive text split — it doesn't understand document structure or semantics. It just breaks text at natural boundaries (paragraphs, sentences, words) within the size limit.

#### `create_embeddings(chunks) → Chroma`

1. If `vector_db/` already exists, deletes the entire collection (`delete_collection()`).
2. Creates a new Chroma collection from the chunks using `OpenAIEmbeddings(model="text-embedding-3-large")`.
3. Persists to `vector_db/`.
4. Prints the vector count and embedding dimension as a sanity check.

---

### `implementation/answer.py`

Loaded at module level (on import), so the vector store and LLM are initialised once and reused for every query.

#### Module-level globals

```python
embeddings = OpenAIEmbeddings(model="text-embedding-3-large")
vectorstore = Chroma(persist_directory=DB_NAME, embedding_function=embeddings)
retriever   = vectorstore.as_retriever()
llm         = ChatOpenAI(temperature=0, model_name="gpt-4.1-nano")
RETRIEVAL_K = 10
```

#### `fetch_context(question) → list[Document]`

Calls `retriever.invoke(question, k=RETRIEVAL_K)`. Returns the 10 most similar chunks from ChromaDB.

#### `combined_question(question, history) → str`

Concatenates all prior user messages from the chat history into a single string and appends the current question. This gives the retrieval step context from the full conversation, not just the last message.

#### `answer_question(question, history) → tuple[str, list[Document]]`

1. Calls `combined_question()` to get the context-enriched query.
2. Calls `fetch_context()` to retrieve the top 10 relevant chunks.
3. Formats a system prompt with the retrieved context injected.
4. Builds the full message list: `[SystemMessage] + history + [HumanMessage]`.
5. Calls `llm.invoke(messages)` and returns `(answer_text, docs)`.

**System prompt template:**
```
You are a knowledgeable, friendly assistant representing the company.
...
Context:
{context}
```

---

## Pro Pipeline (`pro_implementation/`)

An advanced pipeline that uses the OpenAI SDK directly (instead of LangChain), LLM-powered chunking, LiteLLM for model-agnostic LLM calls, and a multi-stage retrieval with re-ranking.

**Vector store location:** `preprocessed_db/`

---

### `pro_implementation/ingest.py`

The key difference from the basic pipeline: **chunks are created by an LLM**, not by a character splitter.

#### `fetch_documents() → list[dict]`

A hand-rolled version of LangChain's `DirectoryLoader`. Returns a list of dicts:
```python
{"type": "services", "source": "/path/to/file.md", "text": "...full file content..."}
```

#### `make_prompt(document) → str`

Builds an LLM prompt that instructs the model to split the document into overlapping chunks. The prompt tells the LLM:
- The document type and source path (for context).
- To estimate how many chunks are appropriate based on document length.
- To aim for ~25% overlap (~50 words) between adjacent chunks.
- That each chunk must have three parts: `headline`, `summary`, and `original_text`.

The `how_many` estimate is `len(text) // AVERAGE_CHUNK_SIZE + 1` where `AVERAGE_CHUNK_SIZE = 100`.

#### `Chunk` and `Chunks` Pydantic models

```python
class Chunk(BaseModel):
    headline: str      # A brief heading optimised for retrieval queries
    summary: str       # A few sentences summarising the chunk's content
    original_text: str # The verbatim text from the document

class Chunks(BaseModel):
    chunks: list[Chunk]
```

These are used with `response_format=Chunks` in the LiteLLM call to get structured JSON output directly from the LLM.

#### `Chunk.as_result(document) → Result`

Converts a `Chunk` into a `Result` (the storage format) by concatenating:
```
{headline}

{summary}

{original_text}
```
This three-part format means that when a chunk is retrieved, it always arrives with its own headline and summary — making it more self-contained and easier for the LLM to use in the answer generation step.

#### `process_document(document) → list[Result]`

Decorated with `@retry(wait=wait_exponential(min=10, max=240))` — if the LLM call fails (rate limit, timeout), it retries with exponential backoff, waiting 10 s, 20 s, 40 s, etc., up to 240 s.

Calls `completion(model=MODEL, messages=..., response_format=Chunks)` and parses the JSON response.

#### `create_chunks(documents) → list[Result]`

Uses `multiprocessing.Pool` with `WORKERS = 3` parallel processes to call `process_document()` concurrently. Each process sends one document to the LLM and waits for the structured response. Progress is shown with `tqdm`.

> If you hit rate limit errors, set `WORKERS = 1` in the file.

#### `create_embeddings(chunks)`

1. Deletes the existing `preprocessed_db/` collection if it exists.
2. Extracts the `page_content` from all chunks into a single list of strings.
3. Calls `openai.embeddings.create(model="text-embedding-3-large", input=texts)` in **one batch call** (more efficient than per-chunk calls).
4. Adds all chunks to ChromaDB with their IDs, embedding vectors, text content, and metadata.
5. Prints the final vector count.

---

### `pro_implementation/answer.py`

A significantly more sophisticated retrieval and answer pipeline than the basic version.

#### Module-level globals

```python
MODEL          = "groq/openai/gpt-oss-120b"   # LiteLLM model string
embedding_model = "text-embedding-3-large"
RETRIEVAL_K    = 20   # initial retrieval count (wide net)
FINAL_K        = 10   # chunks kept after re-ranking
wait           = wait_exponential(multiplier=1, min=10, max=240)

openai     = OpenAI()
chroma     = PersistentClient(path=DB_NAME)
collection = chroma.get_or_create_collection("docs")
```

#### `rewrite_query(question, history) → str`

Calls the LLM with a specialised system prompt to produce a shorter, more precise query for knowledge base retrieval. For example, "what does the company do for fintech clients?" might become "company fintech services offerings".

This matters because user questions are conversational while vector search works best with dense, keyword-rich queries.

Decorated with `@retry(wait=wait)`.

#### `fetch_context_unranked(question) → list[Result]`

1. Embeds `question` using `openai.embeddings.create()`.
2. Calls `collection.query(query_embeddings=..., n_results=RETRIEVAL_K)` to get the top 20 chunks.
3. Returns them as `Result` objects (with `page_content` and `metadata`).

#### `fetch_context(original_question) → list[Result]`

The full dual-retrieval strategy:
1. Calls `rewrite_query(original_question)` to get a refined query.
2. Calls `fetch_context_unranked(original_question)` — retrieves 20 chunks using the **original** question.
3. Calls `fetch_context_unranked(rewritten_question)` — retrieves 20 chunks using the **rewritten** question.
4. Calls `merge_chunks()` to combine both lists, deduplicating by `page_content`.
5. Calls `rerank()` to sort all merged chunks by relevance.
6. Returns only the top `FINAL_K = 10` chunks.

#### `merge_chunks(chunks, reranked) → list[Result]`

Appends any chunk from `reranked` that isn't already in `chunks` (deduplicates by `page_content`). Returns the union.

#### `rerank(question, chunks) → list[Result]`

Sends all merged chunks to the LLM with a re-ranking prompt. The LLM returns a `RankOrder` — a list of integer chunk IDs sorted by relevance to the question. The function reorders the chunks accordingly.

```python
class RankOrder(BaseModel):
    order: list[int]  # e.g. [3, 1, 7, 2, ...] — chunk IDs from most to least relevant
```

This step is expensive (one LLM call per user question) but significantly improves answer quality by promoting the most relevant chunks to the top of the context window.

Decorated with `@retry(wait=wait)`.

#### `make_rag_messages(question, history, chunks) → list[dict]`

Assembles the final message list for the answer LLM:
- System prompt with context injected. Each chunk is formatted as:
  ```
  Extract from {source_path}:
  {chunk.page_content}
  ```
- Full conversation history.
- Current user question.

#### `answer_question(question, history) → tuple[str, list]`

The top-level function called by the chat UI:
1. `fetch_context(question)` — full dual retrieval + rerank pipeline.
2. `make_rag_messages()` — format messages.
3. `completion(model=MODEL, messages=messages)` — generate answer.
4. Returns `(answer_text, chunks)`.

Decorated with `@retry(wait=wait)`.

---

## Retrieval Quality: Basic vs Pro

| Step | Basic | Pro |
|---|---|---|
| Query sent to vector DB | User's message + history concatenated | Original question AND LLM-rewritten query |
| Chunks retrieved | 10 | 20 + 20 merged → up to 40, kept top 10 after rerank |
| Chunk content | Raw text split | Headline + LLM-generated summary + original text |
| Re-ranking | None | LLM re-ranks all merged chunks |
| Metadata in context | None | Source file path shown per chunk |
