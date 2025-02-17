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

def generate_answer(question: str) -> str:
    if is_disallowed_query(question):
        return "I’m sorry, but I cannot answer that."

    results = collection.query(
        query_texts=[question],
        n_results=TOP_K
    )
    retrieved_docs = results["documents"][0]
    context_text = ""
    for i, doc_text in enumerate(retrieved_docs):
        context_text += f"Snippet {i+1}:\n{doc_text}\n\n"

    system_prompt = (
        "You are TheFulcrum's Chat, a helpful assistant for Fulcrum Asset Management. "
        "Answer questions based on the provided document snippets. "
        "If you do not have sufficient context, say: "
        "'I don't have that information. You can ask me about the documents I have access to, such as those related to Fulcrum Asset Management.'"
    )
    if not context_text.strip():
        context_text = "No document context available. You have access to several documents regarding Fulcrum Asset Management."
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
    return final_answer
