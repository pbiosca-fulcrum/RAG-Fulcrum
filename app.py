import os
import uuid
from flask import Flask, request, render_template, jsonify
from chunk_and_embed import chunk_and_embed_file
from query import generate_answer

app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

@app.route("/upload", methods=["POST"])
def upload():
    file = request.files.get("document")
    if not file:
        return "No file uploaded", 400

    doc_id = str(uuid.uuid4())
    filename = doc_id + "_" + file.filename
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(file_path)

    # Process the file: chunk & embed
    chunk_and_embed_file(file_path, doc_id)

    return f"Uploaded and processed document with ID: {doc_id}"

@app.route("/query", methods=["POST"])
def query():
    data = request.json
    if not data or "question" not in data:
        return jsonify({"error": "No question provided"}), 400

    question = data["question"]
    answer = generate_answer(question)
    return jsonify({"answer": answer})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
