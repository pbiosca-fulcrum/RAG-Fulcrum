import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
EMBEDDINGS_MODEL = "text-embedding-3-large"
CHAT_MODEL = "gpt-4o"
TOP_K = 5  # Number of chunks to retrieve
