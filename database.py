import chromadb
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction
from config import OPENAI_API_KEY, EMBEDDINGS_MODEL

DB_DIR = "chroma_db"  # Directory for Chroma persistence

# Note: use api_key (not openai_api_key)
embedding_function = OpenAIEmbeddingFunction(model_name=EMBEDDINGS_MODEL, api_key=OPENAI_API_KEY)
chroma_client = chromadb.PersistentClient(path=DB_DIR)
COLLECTION_NAME = "rag_chunks"
collection = chroma_client.get_or_create_collection(name=COLLECTION_NAME, embedding_function=embedding_function)
