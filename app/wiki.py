import os
import datetime
import sqlite3
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from markupsafe import Markup
import markdown

from chunk_and_embed import embed_text
from database import collection
# We now import the WIKI_DB constant from database_setup
from app.database_setup import WIKI_DB

wiki_bp = Blueprint('wiki', __name__)

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
            cur.execute(
                "UPDATE wiki SET title = ?, content = ?, folder = ?, updated_at = ? WHERE id = ?",
                (title, content, folder, now, page_id)
            )
            conn.commit()
            return page_id
        else:
            cur.execute(
                "INSERT INTO wiki (title, content, folder, updated_at) VALUES (?, ?, ?, ?)",
                (title, content, folder, now)
            )
            conn.commit()
            return cur.lastrowid

def embed_wiki_page(wiki_id, title, content):
    vector = embed_text(content)
    embedding_id = f"wiki-{wiki_id}"
    try:
        collection.delete(ids=[embedding_id])
    except Exception as e:
        print(f"Warning: could not delete existing wiki embedding: {e}")
    # Store the wiki_id in metadata so that later we can reference the correct wiki page.
    metadata = {"type": "wiki", "title": title, "wiki_id": wiki_id}
    collection.add(
        documents=[content],
        embeddings=[vector],
        ids=[embedding_id],
        metadatas=[metadata]
    )
    print(f"Wiki page '{title}' (ID: {wiki_id}) embedded successfully.")

@wiki_bp.route("/wiki/view/<int:page_id>")
def wiki_view(page_id):
    if "user" not in session:
        return redirect(url_for("auth.login"))
    page = get_wiki_page(page_id)
    if not page:
        flash("Wiki page not found.", "error")
        return redirect(url_for("main.knowledge"))
    page["content_html"] = Markup(markdown.markdown(page["content"]))
    return render_template("wiki_view.html", page=page)

@wiki_bp.route("/wiki/edit/<int:page_id>")
def wiki_edit(page_id):
    if "user" not in session:
        return redirect(url_for("auth.login"))
    page = get_wiki_page(page_id)
    if not page:
        flash("Wiki page not found.", "error")
        return redirect(url_for("main.knowledge"))
    return render_template("wiki_edit.html", page=page)

@wiki_bp.route("/wiki/new")
def wiki_new():
    if "user" not in session:
        return redirect(url_for("auth.login"))
    existing_pages = get_all_wiki_pages()
    existing_folders = set([p["folder"] for p in existing_pages if p["folder"]])
    page = {"id": None, "title": "", "content": "", "folder": ""}
    return render_template("wiki_edit.html", page=page, all_folders=existing_folders)

@wiki_bp.route("/wiki/save", methods=["POST"])
def wiki_save():
    if "user" not in session:
        return redirect(url_for("auth.login"))
    title = request.form.get("title").strip()
    content = request.form.get("content").strip()
    folder = request.form.get("folder", "").strip()
    page_id = request.form.get("id")
    if not title or not content:
        flash("Title and content cannot be empty.", "error")
        if page_id:
            return redirect(url_for("wiki.wiki_edit", page_id=page_id))
        else:
            return redirect(url_for("wiki.wiki_new"))
    saved_page_id = save_wiki_page(title, content, folder, page_id)
    embed_wiki_page(saved_page_id, title, content)
    flash("Wiki page saved and embedded successfully.", "success")
    return redirect(url_for("wiki.wiki_view", page_id=saved_page_id))

@wiki_bp.route("/wiki/delete/<int:page_id>", methods=["POST"])
def wiki_delete(page_id):
    if "user" not in session:
        return redirect(url_for("auth.login"))
    page = get_wiki_page(page_id)
    if not page:
        flash("Wiki page not found.", "error")
        return redirect(url_for("main.knowledge"))
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
    return redirect(url_for("main.knowledge"))

def get_all_wiki():
    return get_all_wiki_pages()
