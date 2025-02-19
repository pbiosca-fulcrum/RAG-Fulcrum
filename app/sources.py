import os
import json
from flask import Blueprint, render_template, session, redirect, url_for, flash
from app.wiki import get_wiki_page
import markdown  # Added to render wiki content as Markdown

sources_bp = Blueprint('sources', __name__)

UPLOAD_FOLDER = "uploads"

def get_full_text(file_path):
    import os
    ext = os.path.splitext(file_path)[1].lower()
    # For PDFs and DOCX files, we now only show a note to use the link.
    if ext in [".pdf", ".docx"]:
        return "This document type is best viewed/downloaded via the provided link."
    elif ext == ".txt":
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    elif ext == ".xlsx":
        return "This is an Excel document. Please use the link to view/download."
    elif ext in [".png", ".jpg", ".jpeg"]:
        return "Image file. No text available."
    else:
        return "Unsupported file type."

@sources_bp.route("/sources")
def sources():
    if "user" not in session:
        return redirect(url_for("auth.login"))
    last_sources = session.get("last_sources")
    if not last_sources:
        flash("No source information available.", "info")
        return redirect(url_for("main.index"))
    sources_list = []
    for source in last_sources:
        if source.get("type") == "document":
            folder = source.get("folder")
            filename = source.get("filename")
            file_path = os.path.join(UPLOAD_FOLDER, folder, filename)
            full_text = get_full_text(file_path)
            source["full_text"] = full_text
            source["view_link"] = f"/uploads/{folder}/{filename}"
        elif source.get("type") == "wiki":
            page = get_wiki_page(source.get("wiki_id"))
            if page:
                # Render wiki content using Markdown
                source["full_text"] = markdown.markdown(page.get("content"))
                source["view_link"] = f"/wiki/view/{source.get('wiki_id')}"
                source["edit_link"] = f"/wiki/edit/{source.get('wiki_id')}"
            else:
                source["full_text"] = "Wiki page not found."
        sources_list.append(source)
    return render_template("sources.html", sources=sources_list)
