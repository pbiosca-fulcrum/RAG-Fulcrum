import os
import uuid
import datetime
import json
import sqlite3
from flask import Blueprint, render_template, request, redirect, url_for, flash, send_from_directory, session
from chunk_and_embed import chunk_and_embed_file, generate_document_title
from database import collection, chroma_client, embedding_function

docs_bp = Blueprint('docs', __name__)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
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
    with open(METADATA_FILE, "r") as f:
        data = json.load(f)
    updated_data = [d for d in data if not (d.get("doc_id") == doc_id)]
    with open(METADATA_FILE, "w") as f:
        json.dump(updated_data, f, indent=2)

def process_document(file_path, doc_id, extra_metadata):
    """
    Previously run in a separate thread, but now done inline
    so we can flash a message when it's truly finished.
    """
    chunk_and_embed_file(file_path, doc_id, extra_metadata=extra_metadata)
    extra_metadata["doc_id"] = doc_id
    update_metadata(extra_metadata)

@docs_bp.route("/upload_page", methods=["GET", "POST"])
def upload_page():
    if "user" not in session:
        return redirect(url_for("auth.login"))
    if request.method == "POST":
        file = request.files.get("document")
        if not file:
            flash("No file uploaded.", "error")
            return redirect(url_for("main.knowledge"))

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
        ext = os.path.splitext(file.filename)[1].lower()
        new_filename = sanitized_title + ext
        new_file_path = os.path.join(folder, new_filename)
        os.rename(temp_file_path, new_file_path)

        doc_id = str(uuid.uuid4())
        uploader = session.get("user", "unknown")
        upload_time = now.isoformat()
        upload_display = now.strftime("%H:%M")
        extra_metadata = {
            "title": title,
            "uploader": uploader,
            "upload_time": upload_time,
            "upload_display": upload_display,
            "folder": relative_folder,
            "filename": new_filename,
            "ext": ext
        }

        try:
            # Process synchronously so we know it's fully done
            process_document(new_file_path, doc_id, extra_metadata)
            flash(f"Document '{title}' has finished uploading and embedding!", "success")
        except Exception as e:
            flash(f"Error processing document: {str(e)}", "error")

        # Move the user directly to the Documents tab in Knowledge
        return redirect(url_for("main.knowledge"))
    return render_template("upload.html")

@docs_bp.route("/document/delete/<doc_id>", methods=["POST"])
def document_delete(doc_id):
    if "user" not in session:
        return redirect(url_for("auth.login"))
    try:
        results = collection.get(where={"doc_id": doc_id})
        if results and "ids" in results:
            to_delete = results["ids"]
            collection.delete(ids=to_delete)
        remove_metadata(doc_id)
        flash("Document deleted successfully.", "success")
        return redirect(url_for("main.knowledge"))
    except Exception as e:
        flash("Failed to delete document: " + str(e), "error")
        return redirect(url_for("main.knowledge"))

@docs_bp.route("/uploads/<path:filename>", methods=["GET"])
def uploaded_file(filename):
    """
    Serve the uploaded file from the uploads folder, ensuring
    that we handle the full subdirectory path.
    """
    absolute_path = os.path.join(os.getcwd(), UPLOAD_FOLDER)
    return send_from_directory(absolute_path, filename)

def get_all_documents():
    with open(METADATA_FILE, "r") as f:
        docs = json.load(f)
    # Sort by full upload timestamp (ISO format) descending
    docs = sorted(docs, key=lambda x: x.get("upload_time", ""), reverse=True)
    for doc in docs:
        ext = doc.get("ext", "")
        # For PDFs and DOCX files, show a link in the UI
        if ext in [".pdf", ".docx"]:
            doc["display"] = "link"
        else:
            doc["display"] = "text"
    return docs
