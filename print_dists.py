import chromadb

client = chromadb.PersistentClient(path="./test_chroma_db")
collection = client.get_collection(name="clip_tag_embeddings")
results = collection.get(include=["embeddings", "documents"])
for id, emb in zip(results["ids"], results["embeddings"]):
    print(id, emb[:3])
