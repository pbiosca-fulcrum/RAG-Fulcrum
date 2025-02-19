# TheFulcrum's Chat

TheFulcrum's Chat is an interactive retrieval-augmented assistant built for Fulcrum Asset Management. It leverages Flask, OpenAI's GPT models, and a persistent Chroma database to provide answers based on uploaded documents and wiki pages. The system supports document uploads in various formats (PDF, DOCX, TXT, PNG, etc.), wiki page management with markdown support, and interactive chat with context-aware responses.

## Features

- **User Authentication:** Secure registration and login with hashed passwords.
- **Document Upload & Processing:** Upload documents that are automatically chunked, embedded, and stored in a Chroma database for efficient retrieval.
- **Wiki Management:** Create, edit, and delete wiki pages with markdown support. Each wiki entry displays its last update and the user who last edited it.
- **Interactive Chat:** Ask questions and receive context-rich answers by retrieving relevant document chunks and wiki content.
- **Source Display & Filtering:** View the sources used to construct each answer, with similarity scores and filtering options.
- **Chroma Database Integration:** Persistent storage of document embeddings using OpenAI's embedding functions.

## Installation

### Prerequisites

- Python 3.8 or later
- pip

### Setup Instructions

1. **Clone the Repository:**

   ```bash
   git clone <repository-url>
   cd <repository-directory>
   ```

2. **Create and Activate a Virtual Environment:**

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Environment Variables:**

   Create a `.env` file in the project root with the following content:

   ```dotenv
   FLASK_SECRET_KEY=your-secret-key
   OPENAI_API_KEY=your-openai-api-key
   ```

## Running the Application

To start the application, run:

```bash
python run.py
```

By default, the app will be available at `http://0.0.0.0:5782`.

## Project Structure

```
├── app/
│   ├── __init__.py           # Application factory and blueprint registration
│   ├── auth.py               # User authentication routes
│   ├── database_setup.py     # Database initialization for users and wiki pages
│   ├── docs.py               # Document upload and processing routes
│   ├── main.py               # Main application routes including chat and knowledge base
│   ├── sources.py            # Display and filtering of source documents
│   └── wiki.py               # Wiki page management routes
├── static/
│   ├── style.css             # Application styles
│   ├── logo.png              # Main logo
│   └── mini-log.png          # Favicon/mini logo
├── templates/
│   ├── base.html             # Base HTML template
│   ├── index.html            # Chat interface
│   ├── documents.html        # Document management page
│   ├── error.html            # Error display page
│   ├── flash_messages.html   # Flash messages partial
│   ├── knowledge.html        # Unified knowledge base (documents + wiki)
│   ├── login.html            # Login page
│   ├── register.html         # Registration page
│   ├── sources.html          # Source documents display
│   ├── upload.html           # Document upload page
│   ├── wiki_edit.html        # Wiki page creation/editing page
│   ├── wiki_list.html        # Wiki pages listing page
│   └── wiki_view.html        # Wiki page viewing page
├── chunk_and_embed.py        # Document chunking and embedding functions
├── chroma_restart.py         # Utility to restart the Chroma database
├── config.py                 # Application configuration
├── database.py               # Chroma database setup and embedding function configuration
├── query.py                  # Query processing and answer generation
├── run.py                    # Application runner
└── README.md                 # This README file
```