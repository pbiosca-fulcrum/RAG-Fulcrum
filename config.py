import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
# Models
EMBEDDINGS_MODEL = "text-embedding-3-large"
CHAT_MODEL = "gpt-4o"
TOP_K = 5  # how many chunks to retrieve