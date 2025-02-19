import os
import json
import re
from flask import Blueprint, render_template, session, redirect, url_for, flash
from app.wiki import get_wiki_page
import markdown  # For wiki content
from markupsafe import Markup

sources_bp = Blueprint('sources', __name__)

UPLOAD_FOLDER = "uploads"

def strip_html_tags(html_text: str) -> str:
    return re.sub(r"<[^>]+>", "", html_text)

@sources_bp.route("/sources")
def sources():
    if "user" not in session:
        return redirect(url_for("auth.login"))

    last_sources = session.get("last_sources")
    last_query = session.get("last_query")
    if not last_sources:
        flash("No source information available.", "info")
        return redirect(url_for("main.index"))

    sources_list = []
    for source in last_sources:
        # For documents, we now only show a link, no full text
        if source.get("type") == "document":
            # Keep exactly as is, no "full_text"
            source["full_text"] = None

        # For wiki, show only the first 500 characters (plain text, no HTML tags).
        elif source.get("type") == "wiki":
            page = get_wiki_page(source.get("wiki_id"))
            if page:
                html_content = markdown.markdown(page.get("content", ""))
                plain_text = strip_html_tags(html_content)
                preview = plain_text[:500]
                if len(plain_text) > 500:
                    preview += "..."
                source["full_text"] = preview
                source["view_link"] = f"/wiki/view/{source.get('wiki_id')}"
                source["edit_link"] = f"/wiki/edit/{source.get('wiki_id')}"
            else:
                source["full_text"] = "Wiki page not found."
        sources_list.append(source)

    return render_template("sources.html", sources=sources_list, last_query=last_query)
