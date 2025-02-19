from openai import OpenAI
from database import collection
from config import OPENAI_API_KEY, CHAT_MODEL, TOP_K
from flask import session  # To store sources
import tiktoken  # Added for tokenization

client = OpenAI(api_key=OPENAI_API_KEY)

DISALLOWED_KEYWORDS = ["salary", "salaries", "wage", "wages", "private HR"]

encoder = tiktoken.get_encoding("cl100k_base")

def truncate_to_8100_tokens(text: str) -> str:
    tokens = encoder.encode(text)
    if len(tokens) > 8100:
        tokens = tokens[:8100]
    return encoder.decode(tokens)

def is_disallowed_query(query: str) -> bool:
    query_lc = query.lower()
    for kw in DISALLOWED_KEYWORDS:
        if kw in query_lc:
            return True
    return False

def generate_answer(question: str, debug: bool = False):
    # Truncate the user question to prevent overly large input
    question = truncate_to_8100_tokens(question)

    if is_disallowed_query(question):
        if debug:
            return ("I’m sorry, but I cannot answer that.", "")
        else:
            return "I’m sorry, but I cannot answer that."

    results = collection.query(
        query_texts=[question],
        n_results=TOP_K
    )

    # If no results found or empty
    if not results["documents"] or not results["documents"][0]:
        no_context_answer = (
            "I don't have that information at this time."
        )
        return (no_context_answer, "") if debug else no_context_answer

    docs = results["documents"][0]
    metadatas = results["metadatas"][0]
    context_text = ""
    unique_sources = []

    for i, (doc_text, meta) in enumerate(zip(docs, metadatas)):
        if meta.get("type") == "wiki":
            wiki_id = meta.get("wiki_id")
            title = meta.get("title", "Unknown")
            source = {"type": "wiki", "wiki_id": wiki_id, "title": title}
            link = f"/wiki/view/{wiki_id}"
        else:
            doc_id = meta.get("doc_id")
            title = meta.get("title", "Unknown")
            folder = meta.get("folder")
            filename = meta.get("filename")
            link = f"/uploads/{folder}/{filename}" if folder and filename else "No file link"
            source = {"type": "document", "doc_id": doc_id, "title": title, "folder": folder, "filename": filename, "link": link}

        # Avoid duplicates
        if meta.get("type") == "wiki":
            if not any(s.get("wiki_id") == source.get("wiki_id") for s in unique_sources):
                unique_sources.append(source)
        else:
            if not any(s.get("doc_id") == source.get("doc_id") for s in unique_sources):
                unique_sources.append(source)

        context_text += f"{doc_text}\n\n"

    # Truncate the context to 8100 tokens as well
    context_text = truncate_to_8100_tokens(context_text)

    # Revised system prompt to remove mention of "snippets"
    system_prompt = (
        "You are TheFulcrum's Chat, a helpful assistant for Fulcrum Asset Management. "
        "Provide the best possible answer. "
        "If you do not have sufficient context, respond: "
        "'I don't have that information at this time.'"
    )

    user_prompt = f"Question: {question}\n\nContext:\n{context_text}\n\nAnswer:"

    response = client.chat.completions.create(
        model=CHAT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.0
    )
    final_answer = response.choices[0].message.content.strip()

    # Store sources for the "Source" button
    session['last_sources'] = unique_sources

    if debug:
        return final_answer, context_text
    else:
        return final_answer
