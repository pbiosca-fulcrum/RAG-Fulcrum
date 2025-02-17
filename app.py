import os
import uuid
import datetime
from flask import Flask, request, render_template, jsonify, send_from_directory, redirect, url_for, session, flash
from chunk_and_embed import chunk_and_embed_file, generate_document_title
from query import generate_answer

app = Flask(__name__)
app.secret_key = "your-secret-key"  # Change to a secure random key in production
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Simple user store (for demo purposes)
USERS = {
    "admin": "password",  # demo credentials
}

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if username in USERS and USERS[username] == password:
            session["user"] = username
            flash("Logged in successfully.", "success")
            return redirect(url_for("index"))
        else:
            flash("Invalid credentials", "error")
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

@app.route("/upload", methods=["POST"])
def upload():
    if "user" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    file = request.files.get("document")
    if not file:
        return jsonify({"error": "No file uploaded"}), 400

    # Save file temporarily
    temp_filename = str(uuid.uuid4()) + "_" + file.filename
    temp_file_path = os.path.join(UPLOAD_FOLDER, temp_filename)
    file.save(temp_file_path)

    # Generate an AI title for the document
    try:
        title = generate_document_title(temp_file_path)
    except Exception as e:
        title = file.filename  # fallback
    # Sanitize title and build new filename
    import re
    sanitized_title = re.sub(r'[^a-zA-Z0-9_-]', '_', title)
    ext = os.path.splitext(file.filename)[1]
    new_filename = sanitized_title + ext
    new_file_path = os.path.join(UPLOAD_FOLDER, new_filename)
    os.rename(temp_file_path, new_file_path)

    # Gather metadata: uploader and upload time
    doc_id = str(uuid.uuid4())
    uploader = session.get("user", "unknown")
    upload_time = datetime.datetime.utcnow().isoformat()
    extra_metadata = {"title": title, "uploader": uploader, "upload_time": upload_time}

    try:
        chunk_and_embed_file(new_file_path, doc_id, extra_metadata=extra_metadata)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    return jsonify({"message": f"Uploaded and processed document titled '{title}'"}), 200

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
    files = os.listdir(UPLOAD_FOLDER)
    files = [f for f in files if os.path.isfile(os.path.join(UPLOAD_FOLDER, f))]
    return render_template("documents.html", files=files)

@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

@app.errorhandler(500)
def internal_error(error):
    return render_template("error.html", error=error), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5782, debug=True)
