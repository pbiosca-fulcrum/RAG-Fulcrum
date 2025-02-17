import os
from chromadb.config import Settings
import chromadb

# This database script sets up a local Chroma instance.
# For production, you might point to a managed vector database or
# embed these in Postgres, Pinecone, Weaviate, etc.

DB_DIR = "chroma_db"  # where Chroma persists data

# Initialize Chroma
chroma_client = chromadb.Client(
    Settings(
        chroma_db_impl="duckdb+parquet",
        persist_directory=DB_DIR
    )
)

# A single collection for all docs in this example
COLLECTION_NAME = "rag_chunks"
collection = chroma_client.get_or_create_collection(name=COLLECTION_NAME)