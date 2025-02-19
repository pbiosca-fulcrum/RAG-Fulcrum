import os
import json
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, session
from database import collection, chroma_client, embedding_function
from query import generate_answer
from app.docs import get_all_documents
from app.wiki import get_all_wiki_pages

main_bp = Blueprint('main', __name__)

@main_bp.route("/")
def index():
    if "user" not in session:
        return redirect(url_for("auth.login"))
    return render_template("index.html")

@main_bp.route("/query", methods=["POST"])
def query():
    if "user" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    data = request.json
    if not data or "question" not in data:
        return jsonify({"error": "No question provided"}), 400

    question = data["question"]
    answer = generate_answer(question)
    return jsonify({"answer": answer})

@main_bp.route("/restart_chroma", methods=["POST"])
def restart_chroma():
    try:
        collection.delete()
        new_collection = chroma_client.get_or_create_collection(name="rag_chunks", embedding_function=embedding_function)
        flash("Chroma collection has been restarted.", "success")
        return redirect(url_for("main.knowledge"))
    except Exception as e:
        flash("Failed to restart Chroma collection: " + str(e), "error")
        return redirect(url_for("main.knowledge"))

@main_bp.route("/knowledge")
def knowledge():
    if "user" not in session:
        return redirect(url_for("auth.login"))
    docs = get_all_documents()
    pages = get_all_wiki_pages()
    return render_template("knowledge.html", docs=docs, pages=pages)
    
@main_bp.errorhandler(500)
def internal_error(error):
    return render_template("error.html", error=error), 500
