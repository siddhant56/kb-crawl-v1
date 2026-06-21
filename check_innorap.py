from chromadb import PersistentClient

chroma = PersistentClient(path="preprocessed_db")
col = chroma.get_or_create_collection("docs")

# Get a sample to see metadata format
sample = col.get(limit=5, include=["metadatas"])
print("Sample metadata format:")
for m in sample["metadatas"]:
    print(m)

print(f"\nTotal documents in collection: {col.count()}")

# Try searching by text content instead
results = col.get(where_document={"$contains": "InnoRap"}, include=["documents", "metadatas"])
print(f"\nChunks containing 'InnoRap': {len(results['ids'])}")
for i, (doc, meta) in enumerate(zip(results["documents"][:3], results["metadatas"][:3])):
    print(f"\n--- Chunk {i+1} ---")
    print(f"Metadata: {meta}")
    print(f"Content: {doc[:300]}")
