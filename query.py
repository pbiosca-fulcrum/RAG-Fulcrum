from openai import OpenAI
from database import collection
from config import OPENAI_API_KEY, CHAT_MODEL, TOP_K
from flask import session  # To store sources and last query
import tiktoken

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

def generate_answer(question: str):
    # Truncate the user question to avoid overly large input
    question = truncate_to_8100_tokens(question)

    if is_disallowed_query(question):
        return "I’m sorry, but I cannot answer that."

    results = collection.query(
        query_texts=[question],
        n_results=TOP_K
    )

    # If no results or empty
    if not results.get("documents") or not results["documents"] or not results["documents"][0]:
        session["last_query"] = question
        session["last_sources"] = []
        session["last_answer"] = "I don't have that information at this time."
        return "I don't have that information at this time."

    docs = results["documents"][0]
    metas = results["metadatas"][0]
    distances = results["distances"][0]

    # Combine them so we can sort by distance (ascending)
    items = []
    for doc_text, meta, dist in zip(docs, metas, distances):
        items.append({"doc_text": doc_text, "meta": meta, "distance": dist})

    # Sort by ascending distance => highest similarity first
    items.sort(key=lambda x: x["distance"])

    context_text = ""
    unique_sources = []

    for item in items:
        doc_text = item["doc_text"]
        meta = item["meta"]
        distance = item["distance"]
        similarity_score = (1.0 - distance) * 100.0
        if similarity_score < 0:
            similarity_score = 0
        if similarity_score > 100:
            similarity_score = 100

        # Identify type
        if meta.get("type") == "wiki":
            wiki_id = meta.get("wiki_id")
            title = meta.get("title", "Unknown")
            source = {
                "type": "wiki",
                "wiki_id": wiki_id,
                "title": title,
                "score": round(similarity_score, 2)
            }
            # Avoid duplicates by wiki_id
            if not any(s.get("wiki_id") == wiki_id for s in unique_sources):
                unique_sources.append(source)
        else:
            doc_id = meta.get("doc_id")
            title = meta.get("title", "Unknown")
            folder = meta.get("folder")
            filename = meta.get("filename")
            link = f"/uploads/{folder}/{filename}" if (folder and filename) else "No file link"
            source = {
                "type": "document",
                "doc_id": doc_id,
                "title": title,
                "folder": folder,
                "filename": filename,
                "link": link,
                "score": round(similarity_score, 2)
            }
            # Avoid duplicates by doc_id
            if not any(s.get("doc_id") == doc_id for s in unique_sources):
                unique_sources.append(source)

        # Append text for final context
        context_text += doc_text + "\n\n"

    # Store the query and the sources in session
    session["last_query"] = question
    session["last_sources"] = unique_sources

    # Truncate context again to be safe
    context_text = truncate_to_8100_tokens(context_text)

    system_prompt = (
        "You are TheFulcrum's Chat, a helpful assistant for Fulcrum Asset Management. "
        "Provide the best possible answer. If you feel like you really do not have sufficient context, respond: "
        "'I don't have that information at this time.'"
        "If you think you have just a bit of information, you can respond with that without going to much in detail and at the end tell them to check the source button."
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

    # Store the last answer in session
    session["last_answer"] = final_answer

    return final_answer
