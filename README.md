# TheFulcrum's Chat

TheFulcrum's Chat is an interactive retrieval-augmented assistant built for Fulcrum Asset Management. It uses OpenAI's `text-embedding-3-large` model to embed both documents and queries, and stores these embeddings in a Chroma vector database for semantic search.

## Features

- **User Authentication:**  
  Secure login and registration using an SQLite database with hashed passwords.

- **Document Uploads:**  
  Users can upload documents (PDF, DOCX, TXT, XLSX, images). Documents are stored in a folder structure organized by year and month (e.g., `uploads/2025/02`), and metadata (such as AI-generated title, uploader, and upload time in HH:MM) is saved in a JSON file.

- **Embeddings & Semantic Search:**  
  The system uses OpenAI's `text-embedding-3-large` for both indexing and querying documents.  
  When a query is processed, the top relevant chunks are logged (including document title and link) and then the full document is passed to the LLM to generate an answer. If there isn’t sufficient context, the LLM responds with only the most similar sentence.

- **Vector Database (Chroma):**  
  The application uses a persistent Chroma collection that leverages OpenAI’s embeddings for storage and retrieval.  
  A dedicated route is provided to restart (i.e., delete and reinitialize) the Chroma collection if needed.

- **Asynchronous Document Processing:**  
  Document uploads are processed in the background to avoid long wait times during upload.

- **Interactive Chat:**  
  A chat interface that preserves conversation history (stored in localStorage) and allows users to restart the chat.

## Database Content

- **User Database (users.db):**  
  An SQLite database storing user credentials (username, hashed password, and creation timestamp).

- **Document Metadata (metadata.json):**  
  A JSON file in the `uploads` folder containing an array of metadata records. Each record includes:
  - **title:** The AI-generated title of the document.
  - **uploader:** The username of the person who uploaded the document.
  - **upload_time:** The time of upload (formatted as HH:MM).
  - **folder:** The relative folder (e.g., `2025/02`) where the document is stored.
  - **filename:** The sanitized filename of the document.

- **Chroma Collection:**  
  A persistent vector collection that stores the embeddings (generated using `text-embedding-3-large`) for each chunk of a document. The collection also stores metadata for each chunk, allowing for retrieval and filtering based on document title, uploader, etc.

## Setup Instructions

1. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
