import pickle
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv
from chromadb import PersistentClient
from tqdm import tqdm
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
from sklearn.feature_extraction.text import TfidfVectorizer


load_dotenv(override=True)

DB_NAME = str(Path(__file__).parent.parent / "preprocessed_db")
BM25_PATH = Path(__file__).parent.parent / "bm25_index.pkl"
collection_name = "docs"
# text-embedding-3-small is 5x cheaper than large with competitive quality
embedding_model = "text-embedding-3-small"
KNOWLEDGE_BASE_PATH = Path(__file__).parent.parent / "knowledge-base"

openai = OpenAI()

HEADERS_TO_SPLIT = [("#", "h1"), ("##", "h2"), ("###", "h3"), ("####", "h4")]
md_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=HEADERS_TO_SPLIT)
char_splitter = RecursiveCharacterTextSplitter(chunk_size=600, chunk_overlap=150)


def fetch_documents():
    documents = []
    for folder in KNOWLEDGE_BASE_PATH.iterdir():
        if not folder.is_dir():
            continue
        doc_type = folder.name
        for file in folder.rglob("*.md"):
            with open(file, "r", encoding="utf-8") as f:
                documents.append({"type": doc_type, "source": file.as_posix(), "text": f.read()})
    print(f"Loaded {len(documents)} documents")
    return documents


def chunk_document(document):
    try:
        header_splits = md_splitter.split_text(document["text"])
    except Exception:
        header_splits = []

    chunks = []
    for split in header_splits:
        # Prepend breadcrumb so each chunk carries its section context
        breadcrumb = " > ".join(v for v in split.metadata.values() if v)
        for text in char_splitter.split_text(split.page_content):
            text = text.strip()
            if len(text) < 40:
                continue
            full_text = f"{breadcrumb}\n\n{text}" if breadcrumb else text
            chunks.append({
                "page_content": full_text,
                "metadata": {"source": document["source"], "type": document["type"]},
            })

    # Fallback for docs with no headers
    if not chunks:
        for text in char_splitter.split_text(document["text"]):
            text = text.strip()
            if len(text) >= 40:
                chunks.append({
                    "page_content": text,
                    "metadata": {"source": document["source"], "type": document["type"]},
                })
    return chunks


def create_chunks(documents):
    all_chunks = []
    for doc in tqdm(documents, desc="Chunking"):
        all_chunks.extend(chunk_document(doc))
    print(f"Created {len(all_chunks)} chunks")
    return all_chunks


def embed_in_batches(texts, batch_size=500):
    """OpenAI allows up to 2048 inputs per call; 500 is safe and fast."""
    all_vectors = []
    for i in tqdm(range(0, len(texts), batch_size), desc="Embedding"):
        batch = texts[i : i + batch_size]
        response = openai.embeddings.create(model=embedding_model, input=batch)
        all_vectors.extend(e.embedding for e in response.data)
    return all_vectors


def create_embeddings(chunks):
    chroma = PersistentClient(path=DB_NAME)
    if collection_name in [c.name for c in chroma.list_collections()]:
        chroma.delete_collection(collection_name)

    texts = [c["page_content"] for c in chunks]
    metas = [c["metadata"] for c in chunks]
    ids = [str(i) for i in range(len(chunks))]

    vectors = embed_in_batches(texts)
    collection = chroma.get_or_create_collection(collection_name)

    # ChromaDB hard limit is 5461 per add call
    chroma_batch = 5000
    for i in tqdm(range(0, len(chunks), chroma_batch), desc="Storing"):
        collection.add(
            ids=ids[i : i + chroma_batch],
            embeddings=vectors[i : i + chroma_batch],
            documents=texts[i : i + chroma_batch],
            metadatas=metas[i : i + chroma_batch],
        )
    print(f"Vectorstore created with {collection.count()} documents")

    # Build TF-IDF lexical index for hybrid retrieval (BM25-style exact-term matching)
    # sublinear_tf approximates BM25 term saturation; bigrams catch product names
    vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=1, sublinear_tf=True)
    matrix = vectorizer.fit_transform(texts)
    with open(BM25_PATH, "wb") as f:
        pickle.dump({"vectorizer": vectorizer, "matrix": matrix, "texts": texts, "metadatas": metas}, f)
    print(f"TF-IDF index saved ({BM25_PATH.name})")


if __name__ == "__main__":
    documents = fetch_documents()
    chunks = create_chunks(documents)
    create_embeddings(chunks)
    print("Ingestion complete")
