# RAG-Fulcrum Chat

**AI Generated - 17-02-2025**

## Overview

RAG-Fulcrum Chat is a Retrieval Augmented Generation (RAG) system designed for Fulcrum Asset Management. It uses vector embeddings of document text and wiki pages to provide contextual answers to user queries. Key features include:

- **User Authentication**: Secure login and registration.
- **Document Upload & Processing**: Upload various document types (PDF, DOCX, TXT, images, etc.). The system extracts and embeds text from these documents automatically.
- **Wiki Pages**: Create, edit, view, and delete collaborative wiki pages. Wiki content supports Markdown formatting and is rendered as HTML.
- **Chat Interface**: Ask questions via an interactive chat interface. The system retrieves context from uploaded documents and wiki pages and, when applicable, displays clickable hyperlinks as source references.
- **Knowledge Base**: A unified interface with tabs to manage Documents, Add Document, Wiki Pages, and New Wiki Page.
- **Deletion with Confirmation**: Both documents and wiki pages can be deleted via dedicated buttons, with double confirmation prompts to prevent accidental deletion.
- **Chroma Vector Store Management**: Option to restart the vector store to refresh embeddings if needed.

## Requirements

- Python 3.10 or higher
- Virtualenv (recommended)
- pip

### Python Packages

The main dependencies include:
- Flask
- MarkupSafe
- markdown
- pandas
- openai
- chromadb
- python-dotenv
- Pillow
- PyPDF2
- unstructured

## Setup Instructions

1. **Clone the Repository:**

   ```bash
   git clone https://github.com/yourusername/RAG-Fulcrum.git
   cd RAG-Fulcrum
   ```

2. **Create and Activate a Virtual Environment:**

   ```bash
   python -m venv venv
   source venv/bin/activate   # On Linux/MacOS
   venv\Scripts\activate      # On Windows
   ```

3. **Install Dependencies:**

   If a `requirements.txt` file is provided, run:

   ```bash
   pip install -r requirements.txt
   ```

   Otherwise, install manually:

   ```bash
   pip install Flask MarkupSafe markdown pandas openai chromadb python-dotenv Pillow PyPDF2 unstructured
   ```

4. **Configure Environment Variables:**

   Create a `.env` file in the root directory and add:

   ```
   FLASK_SECRET_KEY=your_secret_key_here
   OPENAI_API_KEY=your_openai_api_key_here
   ```

5. **Initialize the Databases:**

   The application automatically creates and initializes the SQLite databases (`users.db` and `wiki.db`) on first run.

## Running the Application

To start the application, run:

```bash
python app.py
```

The application will be available at [http://0.0.0.0:5782](http://0.0.0.0:5782).

## Application Structure

- **app.py**: Main Flask application handling routes for authentication, document upload, chat interface, and wiki management.
- **chunk_and_embed.py**: Processes documents—extracting text, chunking, summarizing, and embedding using OpenAI's API.
- **query.py**: Handles user queries by retrieving context from the vector database and interacting with the chat model.
- **database.py**: Configures and manages the Chroma vector database for storing text embeddings.
- **templates/**: Contains HTML templates for login, registration, chat interface, knowledge base (documents & wiki pages), and more.
- **static/**: Contains static assets such as CSS and images.

## How It Works

### Document Upload & Processing
- **Upload**: Users upload documents via the "Add Document" tab.
- **Processing**: Documents are processed in the background. The system extracts text, divides it into chunks, summarizes if necessary, and embeds it into the vector store.
- **Deletion**: Documents can be deleted via a "Delete" button with confirmation. Deletion removes both the embedded chunks from the vector store and the document's metadata.

### Wiki Pages
- **Creation & Editing**: Users can create and edit wiki pages using Markdown. The content is converted to HTML for display.
- **Existing Categories**: When creating a new wiki page, existing folder names (categories) are displayed as clickable buttons to auto-fill the folder field.
- **Deletion**: Wiki pages can be deleted with confirmation; the associated embeddings are also removed.

### Chat Interface
- **Query Processing**: Users ask questions through the chat interface. The system retrieves relevant document/wiki snippets from the vector store to form context.
- **Clickable References**: If references are used in the response, clickable Markdown links are provided that take you directly to the source document.
- **Debug Mode**: A debug toggle shows additional context information in the console for troubleshooting.

### Knowledge Base
- **Unified Interface**: The Knowledge Base combines both uploaded documents and wiki pages into a tabbed interface.
- **Tabs**: 
  - **Documents**
  - **Add Document**
  - **Wiki Pages**
  - **New Wiki Page**
- **Encouraging Growth**: A message at the top invites users to add more documents and wiki pages, stating that the chat improves with every new piece of knowledge added.

### Vector Store Management
- **Restart Chroma**: A route is provided to restart the Chroma vector collection if you need to refresh embeddings.

## Troubleshooting

- **Import Errors**: Make sure all dependencies are installed. If you encounter an error with `Markup`, ensure `MarkupSafe` is installed and up-to-date.
- **Environment Variables**: Verify that your `.env` file is properly configured.
- **Database Initialization**: If you face issues with SQLite databases, delete `users.db` and `wiki.db` and re-run the application.