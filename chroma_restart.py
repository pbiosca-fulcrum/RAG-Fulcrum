#!/usr/bin/env python

from database import chroma_client, collection, embedding_function

def restart_chroma_db():
    try:
        print("Deleting all items from the existing collection...")
        collection.delete()  # Delete all items in the collection
        print("Existing collection data deleted.")
    except Exception as e:
        print(f"Error deleting collection data: {e}")

    # Recreate (or get) the collection using the embedding function.
    new_collection = chroma_client.get_or_create_collection(name="rag_chunks", embedding_function=embedding_function)
    print("Chroma collection 'rag_chunks' has been restarted successfully.")

if __name__ == "__main__":
    restart_chroma_db()
