import chromadb

DB_DIR = "chroma_db"  # Directory for Chroma persistence

# Use the new persistent client
chroma_client = chromadb.PersistentClient(path=DB_DIR)
COLLECTION_NAME = "rag_chunks"
collection = chroma_client.get_or_create_collection(name=COLLECTION_NAME)
