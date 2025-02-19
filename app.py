import os
import uuid
import datetime
import json
import sqlite3
import threading
import markdown
import pandas as pd

from markupsafe import Markup
from flask import (
    Flask, request, render_template, jsonify,
    send_from_directory, redirect, url_for, session, flash
)
from werkzeug.security import generate_password_hash, check_password_hash
from chunk_and_embed import chunk_and_embed_file, generate_document_title, embed_text
from query import generate_answer
from database import collection, chroma_client, embedding_function

# New imports for full text extraction in sources route
from unstructured.partition.pdf import partition_pdf
from unstructured.partition.docx import partition_docx
from unstructured.partition.text import partition_text
from unstructured.partition.xlsx import partition_xlsx

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "this-should-be-changed")  # Use a secure key in production
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# --- User Database Setup (SQLite) ---
USERS_DB = "users.db"

def init_db():
    with sqlite3.connect(USERS_DB) as conn:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        conn.commit()

def get_user(username):
    with sqlite3.connect(USERS_DB) as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, username, password FROM users WHERE username = ?", (username,))
        row = cur.fetchone()
        if row:
            return {"id": row[0], "username": row[1], "password": row[2]}
    return None

def register_user(username, password):
    hashed = generate_password_hash(password)
    with sqlite3.connect(USERS_DB) as conn:
        cur = conn.cursor()
        cur.execute("INSERT INTO users (username, password, created_at) VALUES (?, ?, ?)",
                    (username, hashed, datetime.datetime.utcnow().isoformat()))
        conn.commit()

init_db()

# --- Helper for Document Metadata ---
METADATA_FILE = os.path.join(UPLOAD_FOLDER, "metadata.json")
if not os.path.exists(METADATA_FILE):
    with open(METADATA_FILE, "w") as f:
        json.dump([], f)

def update_metadata(record):
    with open(METADATA_FILE, "r") as f:
        data = json.load(f)
    data.append(record)
    with open(METADATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

def remove_metadata(doc_id):
    """Remove a document record from metadata.json by doc_id."""
    with open(METADATA_FILE, "r") as f:
        data = json.load(f)
    updated_data = [d for d in data if not (d.get("doc_id") == doc_id)]
    with open(METADATA_FILE, "w") as f:
        json.dump(updated_data, f, indent=2)

# --- Background processing for document uploads ---
def process_document(new_file_path, doc_id, extra_metadata):
    try:
        chunk_and_embed_file(new_file_path, doc_id, extra_metadata=extra_metadata)
        extra_metadata["doc_id"] = doc_id  # store doc_id so we can remove it later if needed
        update_metadata(extra_metadata)
        # Log which text snippets have been processed (for debugging)
        print(f"[{datetime.datetime.utcnow().isoformat()}] Document '{extra_metadata['title']}' processed. Metadata: {extra_metadata}")
    except Exception as e:
        print(f"[{datetime.datetime.utcnow().isoformat()}] Error processing document '{extra_metadata.get('title', 'Unknown')}': {e}")

# --- New Route: Restart Chroma ---
@app.route("/restart_chroma", methods=["POST"])
def restart_chroma():
    try:
        collection.delete()  # Delete existing collection
        # Re-create the collection with the same embedding function
        new_collection = chroma_client.get_or_create_collection(name="rag_chunks", embedding_function=embedding_function)
        flash("Chroma collection has been restarted.", "success")
        return redirect(url_for("knowledge"))
    except Exception as e:
        flash("Failed to restart Chroma collection: " + str(e), "error")
        return redirect(url_for("knowledge"))

# --- Document Delete ---
@app.route("/document/delete/<doc_id>", methods=["POST"])
def document_delete(doc_id):
    if "user" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    # Remove from vector store
    try:
        # Find all chunks that match doc_id
        results = collection.get(where={"doc_id": doc_id})
        if results and "ids" in results:
            to_delete = results["ids"]
            collection.delete(ids=to_delete)
        # Remove from metadata
        remove_metadata(doc_id)
        flash("Document deleted successfully.", "success")
        return redirect(url_for("knowledge"))
    except Exception as e:
        flash("Failed to delete document: " + str(e), "error")
        return redirect(url_for("knowledge"))

# --- User Authentication Routes ---
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username").strip()
        password = request.form.get("password").strip()
        if get_user(username):
            flash("Username already taken.", "error")
            return render_template("register.html")
        try:
            register_user(username, password)
            flash("Registration successful. Please log in.", "success")
            return redirect(url_for("login"))
        except Exception as e:
            flash("Registration failed: " + str(e), "error")
            return render_template("register.html")
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username").strip()
        password = request.form.get("password").strip()
        user = get_user(username)
        if user and check_password_hash(user["password"], password):
            session["user"] = username
            flash("Logged in successfully.", "success")
            return redirect(url_for("index"))
        else:
            flash("Invalid credentials.", "error")
            return render_template("login.html")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop("user", None)
    flash("Logged out.", "info")
    return redirect(url_for("login"))

# --- Main Chat Route ---
@app.route("/", methods=["GET"])
def index():
    if "user" not in session:
        return redirect(url_for("login"))
    return render_template("index.html")

@app.route("/query", methods=["POST"])
def query():
    if "user" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    data = request.json
    if not data or "question" not in data:
        return jsonify({"error": "No question provided"}), 400
    question = data["question"]
    debug = data.get("debug", False)
    if debug:
        answer, debug_context = generate_answer(question, debug=True)
        return jsonify({"answer": answer, "debug_context": debug_context})
    else:
        answer = generate_answer(question, debug=False)
        return jsonify({"answer": answer})

# --- Unified Knowledge Page (Documents + Wiki) ---
@app.route("/knowledge")
def knowledge():
    if "user" not in session:
        return redirect(url_for("login"))
    # Get documents
    with open(METADATA_FILE, "r") as f:
        docs = json.load(f)
    docs = sorted(docs, key=lambda x: x.get("upload_time", ""), reverse=True)
    # Get wiki pages
    pages = get_all_wiki_pages()
    return render_template("knowledge.html", docs=docs, pages=pages)

# --- Document Upload ---
@app.route("/upload_page", methods=["GET", "POST"])
def upload_page():
    if "user" not in session:
        return redirect(url_for("login"))
    if request.method == "POST":
        file = request.files.get("document")
        if not file:
            flash("No file uploaded.", "error")
            return redirect(url_for("knowledge"))

        now = datetime.datetime.utcnow()
        relative_folder = os.path.join(now.strftime("%Y"), now.strftime("%m"))
        folder = os.path.join(UPLOAD_FOLDER, relative_folder)
        os.makedirs(folder, exist_ok=True)

        temp_filename = str(uuid.uuid4()) + "_" + file.filename
        temp_file_path = os.path.join(folder, temp_filename)
        file.save(temp_file_path)

        try:
            title = generate_document_title(temp_file_path)
        except Exception:
            title = file.filename

        import re
        sanitized_title = re.sub(r'[^a-zA-Z0-9_-]', '_', title)
        ext = os.path.splitext(file.filename)[1]
        new_filename = sanitized_title + ext
        new_file_path = os.path.join(folder, new_filename)
        os.rename(temp_file_path, new_file_path)

        doc_id = str(uuid.uuid4())
        uploader = session.get("user", "unknown")
        upload_time = now.strftime("%H:%M")
        extra_metadata = {
            "title": title,
            "uploader": uploader,
            "upload_time": upload_time,
            "folder": relative_folder,
            "filename": new_filename
        }

        flash(f"Your document '{title}' has been uploaded and is being processed. Please wait...", "info")
        threading.Thread(target=process_document, args=(new_file_path, doc_id, extra_metadata)).start()

        return redirect(url_for("knowledge"))
    return render_template("upload.html")

@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

@app.errorhandler(500)
def internal_error(error):
    return render_template("error.html", error=error), 500

# --- Wiki Functionality ---
WIKI_DB = "wiki.db"

def init_wiki_db():
    with sqlite3.connect(WIKI_DB) as conn:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS wiki (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                folder TEXT DEFAULT '',
                updated_at TEXT NOT NULL
            )
        """)
        conn.commit()

init_wiki_db()

def get_all_wiki_pages():
    with sqlite3.connect(WIKI_DB) as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, title, folder, updated_at FROM wiki ORDER BY updated_at DESC")
        rows = cur.fetchall()
        pages = []
        for row in rows:
            pages.append({
                "id": row[0],
                "title": row[1],
                "folder": row[2],
                "updated_at": row[3]
            })
    return pages

def get_wiki_page(page_id):
    with sqlite3.connect(WIKI_DB) as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, title, content, folder, updated_at FROM wiki WHERE id = ?", (page_id,))
        row = cur.fetchone()
        if row:
            return {
                "id": row[0],
                "title": row[1],
                "content": row[2],
                "folder": row[3],
                "updated_at": row[4]
            }
    return None

def save_wiki_page(title, content, folder, page_id=None):
    now = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M")
    with sqlite3.connect(WIKI_DB) as conn:
        cur = conn.cursor()
        if page_id:
            cur.execute("UPDATE wiki SET title = ?, content = ?, folder = ?, updated_at = ? WHERE id = ?",
                        (title, content, folder, now, page_id))
            conn.commit()
            return page_id
        else:
            cur.execute("INSERT INTO wiki (title, content, folder, updated_at) VALUES (?, ?, ?, ?)",
                        (title, content, folder, now))
            conn.commit()
            return cur.lastrowid

def embed_wiki_page(wiki_id, title, content):
    vector = embed_text(content)
    embedding_id = f"wiki-{wiki_id}"
    try:
        collection.delete(ids=[embedding_id])
    except Exception as e:
        print(f"Warning: could not delete existing wiki embedding: {e}")
    metadata = {"type": "wiki", "title": title}
    collection.add(
        documents=[content],
        embeddings=[vector],
        ids=[embedding_id],
        metadatas=[metadata]
    )
    print(f"Wiki page '{title}' (ID: {wiki_id}) embedded successfully.")

@app.route("/wiki/view/<int:page_id>")
def wiki_view(page_id):
    if "user" not in session:
        return redirect(url_for("login"))
    page = get_wiki_page(page_id)
    if not page:
        flash("Wiki page not found.", "error")
        return redirect(url_for("knowledge"))
    page["content_html"] = Markup(markdown.markdown(page["content"]))
    return render_template("wiki_view.html", page=page)

@app.route("/wiki/edit/<int:page_id>")
def wiki_edit(page_id):
    if "user" not in session:
        return redirect(url_for("login"))
    page = get_wiki_page(page_id)
    if not page:
        flash("Wiki page not found.", "error")
        return redirect(url_for("knowledge"))
    return render_template("wiki_edit.html", page=page)

@app.route("/wiki/new")
def wiki_new():
    if "user" not in session:
        return redirect(url_for("login"))
    existing_pages = get_all_wiki_pages()
    existing_folders = set([p["folder"] for p in existing_pages if p["folder"]])
    page = {"id": None, "title": "", "content": "", "folder": ""}
    return render_template("wiki_edit.html", page=page, all_folders=existing_folders)

@app.route("/wiki/save", methods=["POST"])
def wiki_save():
    if "user" not in session:
        return redirect(url_for("login"))
    title = request.form.get("title").strip()
    content = request.form.get("content").strip()
    folder = request.form.get("folder", "").strip()
    page_id = request.form.get("id")
    if not title or not content:
        flash("Title and content cannot be empty.", "error")
        return redirect(url_for("wiki_new") if not page_id else url_for("wiki_edit", page_id=page_id))
    saved_page_id = save_wiki_page(title, content, folder, page_id)
    embed_wiki_page(saved_page_id, title, content)
    flash("Wiki page saved and embedded successfully.", "success")
    return redirect(url_for("wiki_view", page_id=saved_page_id))

@app.route("/wiki/delete/<int:page_id>", methods=["POST"])
def wiki_delete(page_id):
    if "user" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    page = get_wiki_page(page_id)
    if not page:
        flash("Wiki page not found.", "error")
        return redirect(url_for("knowledge"))
    embedding_id = f"wiki-{page_id}"
    try:
        collection.delete(ids=[embedding_id])
    except Exception as e:
        print(f"Warning: could not delete existing wiki embedding: {e}")

    with sqlite3.connect(WIKI_DB) as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM wiki WHERE id = ?", (page_id,))
        conn.commit()

    flash(f"Wiki page '{page['title']}' deleted successfully.", "success")
    return redirect(url_for("knowledge"))

# --- New Helpers for Source Retrieval ---
def get_full_text(file_path):
    ext = os.path.splitext(file_path)[1].lower()
    full_text = ""
    if ext == ".txt":
        with open(file_path, "r", encoding="utf-8") as f:
            full_text = f.read()
    elif ext == ".pdf":
        try:
            elements = partition_pdf(file_path, infer_table_structure=True, strategy="hi_res")
            for el in elements:
                full_text += el.text + "\n"
        except Exception:
            try:
                from PyPDF2 import PdfReader
                reader = PdfReader(file_path)
                for page in reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        full_text += page_text + "\n"
            except Exception:
                full_text = "Could not extract text."
    elif ext == ".docx":
        elements = partition_docx(file_path)
        for el in elements:
            full_text += (el.text if hasattr(el, 'text') else "") + "\n"
    elif ext == ".xlsx":
        elements = partition_xlsx(file_path)
        for el in elements:
            full_text += el.text + "\n"
    elif ext in [".png", ".jpg", ".jpeg"]:
        full_text = "Image file. No text available."
    else:
        full_text = "Unsupported file type."
    return full_text

def get_metadata_by_doc_id(doc_id):
    with open(METADATA_FILE, "r") as f:
        data = json.load(f)
    for record in data:
        if record.get("doc_id") == doc_id:
            return record
    return None

# --- New Route: Source Retrieval ---
@app.route("/sources")
def sources():
    if "user" not in session:
        return redirect(url_for("login"))
    last_sources = session.get("last_sources")
    if not last_sources:
        flash("No source information available.", "info")
        return redirect(url_for("index"))
    sources_list = []
    for source in last_sources:
        if source.get("type") == "document":
            metadata = get_metadata_by_doc_id(source.get("doc_id"))
            if metadata:
                folder = metadata.get("folder")
                filename = metadata.get("filename")
                file_path = os.path.join(UPLOAD_FOLDER, folder, filename)
                full_text = get_full_text(file_path)
                source["full_text"] = full_text
                source["view_link"] = f"/uploads/{folder}/{filename}"
            else:
                source["full_text"] = "Metadata not found."
        elif source.get("type") == "wiki":
            page = get_wiki_page(source.get("wiki_id"))
            if page:
                source["full_text"] = page.get("content")
                source["view_link"] = f"/wiki/view/{source.get('wiki_id')}"
                source["edit_link"] = f"/wiki/edit/{source.get('wiki_id')}"
            else:
                source["full_text"] = "Wiki page not found."
        sources_list.append(source)
    return render_template("sources.html", sources=sources_list)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5782, debug=True)
