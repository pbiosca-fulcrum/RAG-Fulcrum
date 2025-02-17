from openai import OpenAI
from database import collection
from config import OPENAI_API_KEY, CHAT_MODEL, TOP_K

client = OpenAI(api_key=OPENAI_API_KEY)

DISALLOWED_KEYWORDS = ["salary", "salaries", "wage", "wages", "private HR"]

def is_disallowed_query(query: str) -> bool:
    query_lc = query.lower()
    for kw in DISALLOWED_KEYWORDS:
        if kw in query_lc:
            return True
    return False

def generate_answer(question: str, debug: bool = False):
    if is_disallowed_query(question):
        return "I’m sorry, but I cannot answer that." if not debug else ("I’m sorry, but I cannot answer that.", "")

    results = collection.query(
        query_texts=[question],
        n_results=TOP_K
    )

    # If no results found or empty (safety check)
    if not results["documents"] or not results["documents"][0]:
        no_context_answer = (
            "I don't have that information. You can ask me about the documents I have access to, "
            "such as those related to Fulcrum Asset Management."
        )
        return (no_context_answer, "") if debug else no_context_answer

    docs = results["documents"][0]
    metadatas = results["metadatas"][0]
    context_text = ""
    # Also gather unique sources for potential references
    unique_sources = {}

    for i, (doc_text, meta) in enumerate(zip(docs, metadatas)):
        folder = meta.get("folder")
        filename = meta.get("filename")
        title = meta.get("title", "Unknown")
        # Link if available
        link = ""
        if folder and filename:
            link = f"/uploads/{folder}/{filename}"

        # Gather context
        context_text += f"Snippet {i+1} from '{title}' ({link if link else 'No file link'}):\n{doc_text}\n\n"

        # Collect unique sources by title
        if title not in unique_sources:
            unique_sources[title] = link if link else "#"

    if not context_text.strip():
        context_text = "No document context available."

    system_prompt = (
        "You are TheFulcrum's Chat, a helpful assistant for Fulcrum Asset Management. "
        "Answer questions based on the provided document snippets. "
        "If you do not have sufficient context, say: "
        "'I don't have that information. You can ask me about the documents I have access to, such as those related to Fulcrum Asset Management.'"
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

    # If user specifically asks for sources/references, append them:
    if any(x in question.lower() for x in ["source", "sources", "reference", "references"]):
        if unique_sources:
            final_answer += "\n\n**Sources**:"
            for title, url in unique_sources.items():
                if url != "#":
                    # Hidden under the document title but clickable:
                    final_answer += f"\n- [{title}]({url})"
                else:
                    final_answer += f"\n- {title} (no direct link)"

    if debug:
        # Return the debug context as well
        return final_answer, context_text
    else:
        return final_answer
