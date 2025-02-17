import os
import uuid
import datetime
import json
import sqlite3
import threading
from flask import (Flask, request, render_template, jsonify,
                   send_from_directory, redirect, url_for, session, flash)
from werkzeug.security import generate_password_hash, check_password_hash
from chunk_and_embed import chunk_and_embed_file, generate_document_title
from query import generate_answer

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

# --- Background processing ---
def process_document(new_file_path, doc_id, extra_metadata):
    try:
        chunk_and_embed_file(new_file_path, doc_id, extra_metadata=extra_metadata)
        update_metadata(extra_metadata)
        # Log which text snippets have been processed (for debugging)
        print(f"[{datetime.datetime.utcnow().isoformat()}] Document '{extra_metadata['title']}' processed. Metadata: {extra_metadata}")
    except Exception as e:
        print(f"[{datetime.datetime.utcnow().isoformat()}] Error processing document '{extra_metadata.get('title', 'Unknown')}': {e}")

# --- Routes ---
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

@app.route("/", methods=["GET"])
def index():
    if "user" not in session:
        return redirect(url_for("login"))
    return render_template("index.html")

# ... [imports and earlier code remain unchanged] ...

@app.route("/upload_page", methods=["GET", "POST"])
def upload_page():
    if "user" not in session:
        return redirect(url_for("login"))
    if request.method == "POST":
        file = request.files.get("document")
        if not file:
            flash("No file uploaded.", "error")
            return redirect(url_for("upload_page"))

        now = datetime.datetime.utcnow()
        # Create folder structure based on current UTC date: uploads/YYYY/MM
        relative_folder = os.path.join(now.strftime("%Y"), now.strftime("%m"))
        folder = os.path.join(UPLOAD_FOLDER, relative_folder)
        os.makedirs(folder, exist_ok=True)

        temp_filename = str(uuid.uuid4()) + "_" + file.filename
        temp_file_path = os.path.join(folder, temp_filename)
        file.save(temp_file_path)

        try:
            title = generate_document_title(temp_file_path)
        except Exception as e:
            title = file.filename  # fallback

        import re
        sanitized_title = re.sub(r'[^a-zA-Z0-9_-]', '_', title)
        ext = os.path.splitext(file.filename)[1]
        new_filename = sanitized_title + ext
        new_file_path = os.path.join(folder, new_filename)
        os.rename(temp_file_path, new_file_path)

        doc_id = str(uuid.uuid4())
        uploader = session.get("user", "unknown")
        # Only display HH:MM for upload time
        upload_time = now.strftime("%H:%M")
        extra_metadata = {
            "title": title,
            "uploader": uploader,
            "upload_time": upload_time,
            "folder": relative_folder,  # store only the relative path
            "filename": new_filename
        }

        # Spawn a background thread to process the document
        threading.Thread(target=process_document, args=(new_file_path, doc_id, extra_metadata)).start()

        flash(f"Your document '{title}' has been uploaded and is being processed.", "info")
        return redirect(url_for("documents"))
    return render_template("upload.html")



@app.route("/query", methods=["POST"])
def query():
    if "user" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    data = request.json
    if not data or "question" not in data:
        return jsonify({"error": "No question provided"}), 400
    question = data["question"]
    answer = generate_answer(question)
    return jsonify({"answer": answer})

@app.route("/documents", methods=["GET"])
def documents():
    if "user" not in session:
        return redirect(url_for("login"))
    with open(METADATA_FILE, "r") as f:
        docs = json.load(f)
    docs = sorted(docs, key=lambda x: x.get("upload_time", ""), reverse=True)
    return render_template("documents.html", docs=docs)

@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

@app.errorhandler(500)
def internal_error(error):
    return render_template("error.html", error=error), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5782, debug=True)
