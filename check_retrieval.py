import sys
sys.path.insert(0, ".")
from pro_implementation.answer import fetch_context

question = "What innovation does Radixweb do?"
chunks = fetch_context(question, [])

print(f"Total chunks retrieved: {len(chunks)}\n")
for i, chunk in enumerate(chunks):
    print(f"--- Chunk {i+1} ---")
    print(f"Type: {chunk.metadata.get('type')}")
    print(f"Source: {chunk.metadata.get('source', '').split('/')[-1]}")
    print(f"Content: {chunk.page_content[:150]}")
    print()
