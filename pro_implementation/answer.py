import pickle
import numpy as np
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from openai import OpenAI
from dotenv import load_dotenv
from chromadb import PersistentClient
from litellm import completion
from pydantic import BaseModel
from tenacity import retry, wait_exponential
from sentence_transformers import CrossEncoder
from sklearn.metrics.pairwise import cosine_similarity


load_dotenv(override=True)

MODEL = "openai/gpt-4.1-nano"
DB_NAME = str(Path(__file__).parent.parent / "preprocessed_db")
BM25_PATH = Path(__file__).parent.parent / "bm25_index.pkl"

collection_name = "docs"
embedding_model = "text-embedding-3-small"
wait = wait_exponential(multiplier=1, min=10, max=240)

RETRIEVAL_K = 15   # candidates per retrieval method (reduced for faster cross-encoder)
FINAL_K = 10       # chunks passed to the LLM
RRF_K = 60         # standard Reciprocal Rank Fusion constant

openai = OpenAI()
chroma = PersistentClient(path=DB_NAME)
collection = chroma.get_or_create_collection(collection_name)

with open(BM25_PATH, "rb") as f:
    _idx = pickle.load(f)
_tfidf_vectorizer = _idx["vectorizer"]
_tfidf_matrix = _idx["matrix"]
_tfidf_texts = _idx["texts"]
_tfidf_metas = _idx["metadatas"]

# Use MPS on Apple Silicon if available, otherwise CPU
import torch
_device = "mps" if torch.backends.mps.is_available() else "cpu"
_cross_encoder = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2", device=_device)

SYSTEM_PROMPT = """
You are a knowledgeable, friendly assistant representing the company Radixweb.

CRITICAL INSTRUCTION: The Knowledge Base extracts provided below are the absolute ground truth. \
They ALWAYS override anything stated in the conversation history. \
If a previous message in the conversation contradicts the Knowledge Base, \
IGNORE the previous message and rely solely on the Knowledge Base extracts.

Source authority rules — when extracts conflict with each other:
- Extracts labelled [AUTHORITATIVE] are the definitive source for company facts (leadership, team, structure, mission).
- Extracts labelled [BLOG] may contain outdated information about former employees or past events. \
  When an [AUTHORITATIVE] extract contradicts a [BLOG] extract, always trust the [AUTHORITATIVE] one.

Knowledge Base extracts:
{context}

Answer the user's question using only the Knowledge Base above. Be accurate, relevant and complete. \
If you don't know the answer, say so.
"""


class Result(BaseModel):
    page_content: str
    metadata: dict


AUTHORITATIVE_TYPES = {"about", "leadership"}


def rrf_merge(ranked_lists: list[list[Result]]) -> list[Result]:
    scores: dict[str, float] = {}
    items: dict[str, Result] = {}
    for ranked in ranked_lists:
        for rank, item in enumerate(ranked):
            key = item.page_content
            score = 1.0 / (RRF_K + rank + 1)
            # Boost authoritative doc types so they surface above blog posts
            if item.metadata.get("type") in AUTHORITATIVE_TYPES:
                score *= 2.0
            scores[key] = scores.get(key, 0.0) + score
            items[key] = item
    return sorted(items.values(), key=lambda x: scores[x.page_content], reverse=True)


def fetch_vector_results(query_text: str, n: int = RETRIEVAL_K) -> list[Result]:
    query_vec = openai.embeddings.create(model=embedding_model, input=[query_text]).data[0].embedding
    results = collection.query(query_embeddings=[query_vec], n_results=n)
    return [
        Result(page_content=doc, metadata=meta)
        for doc, meta in zip(results["documents"][0], results["metadatas"][0])
    ]


def fetch_tfidf_results(query_text: str, n: int = RETRIEVAL_K) -> list[Result]:
    query_vec = _tfidf_vectorizer.transform([query_text])
    sims = cosine_similarity(query_vec, _tfidf_matrix).flatten()
    top_indices = np.argsort(sims)[::-1][:n]
    return [
        Result(page_content=_tfidf_texts[i], metadata=_tfidf_metas[i])
        for i in top_indices
        if sims[i] > 0
    ]


def cross_encode_rerank(question: str, chunks: list[Result]) -> list[Result]:
    if not chunks:
        return chunks
    pairs = [(question, chunk.page_content) for chunk in chunks]
    raw_scores = _cross_encoder.predict(pairs)

    scored = list(zip(raw_scores, chunks))

    # Find the best raw score among authoritative chunks
    auth_scores = [s for s, c in scored if c.metadata.get("type") in AUTHORITATIVE_TYPES]
    best_auth_score = max(auth_scores) if auth_scores else None

    # Drop non-authoritative chunks that score below the best authoritative chunk.
    # This prevents outdated blog posts from polluting the context when a canonical
    # source already covers the same topic.
    if best_auth_score is not None:
        scored = [(s, c) for s, c in scored
                  if c.metadata.get("type") in AUTHORITATIVE_TYPES or s >= best_auth_score]

    return [c for _, c in sorted(scored, key=lambda x: x[0], reverse=True)]


@retry(wait=wait)
def rewrite_query(question: str, history: list = []) -> str:
    message = f"""You are searching a knowledge base about Radixweb.
Conversation history: {history}
User question: {question}
Respond ONLY with a short, precise search query optimized to retrieve the most relevant content. Nothing else."""
    response = completion(model=MODEL, messages=[{"role": "user", "content": message}])
    return response.choices[0].message.content.strip()


def fetch_context(question: str, history: list = []) -> list[Result]:
    # Fire rewrite + original-query vector search in parallel (both are IO-bound)
    with ThreadPoolExecutor(max_workers=2) as ex:
        fut_rewrite = ex.submit(rewrite_query, question, history)
        fut_vec1 = ex.submit(fetch_vector_results, question)
        rewritten = fut_rewrite.result()
        vec1 = fut_vec1.result()

    # Now fire rewritten vector + both TF-IDF searches in parallel
    with ThreadPoolExecutor(max_workers=3) as ex:
        fut_vec2 = ex.submit(fetch_vector_results, rewritten)
        fut_lex1 = ex.submit(fetch_tfidf_results, question)
        fut_lex2 = ex.submit(fetch_tfidf_results, rewritten)
        vec2 = fut_vec2.result()
        lex1 = fut_lex1.result()
        lex2 = fut_lex2.result()

    merged = rrf_merge([vec1, vec2, lex1, lex2])

    # Cap at 2 chunks per source file so no single doc floods the candidate list
    MAX_PER_SOURCE = 2
    seen_content: set[str] = set()
    source_counts: dict[str, int] = {}
    candidates: list[Result] = []
    for chunk in merged:
        if chunk.page_content in seen_content:
            continue
        src = chunk.metadata.get("source", "")
        if source_counts.get(src, 0) >= MAX_PER_SOURCE:
            continue
        seen_content.add(chunk.page_content)
        source_counts[src] = source_counts.get(src, 0) + 1
        candidates.append(chunk)
        if len(candidates) >= RETRIEVAL_K:
            break

    return cross_encode_rerank(question, candidates)[:FINAL_K]


def _source_label(chunk: Result) -> str:
    doc_type = chunk.metadata.get("type", "unknown")
    path = chunk.metadata.get("source", "")
    if doc_type in AUTHORITATIVE_TYPES:
        return f"[AUTHORITATIVE — {doc_type}] {path}"
    return f"[{doc_type.upper()} — may contain outdated info] {path}"


def make_rag_messages(question: str, chunks: list[Result]) -> list:
    context = "\n\n".join(
        f"Extract from {_source_label(chunk)}:\n{chunk.page_content}" for chunk in chunks
    )
    # History is intentionally excluded — the KB context is the sole source of truth.
    # History is used only for query rewriting so follow-up questions still work.
    return [
        {"role": "system", "content": SYSTEM_PROMPT.format(context=context)},
        {"role": "user", "content": question},
    ]


@retry(wait=wait)
def answer_question(question: str, history: list[dict] = []) -> tuple[str, list]:
    chunks = fetch_context(question, history)
    messages = make_rag_messages(question, chunks)
    response = completion(model=MODEL, messages=messages)
    return response.choices[0].message.content, chunks
