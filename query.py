from openai import OpenAI
from database import collection
from config import OPENAI_API_KEY, CHAT_MODEL, TOP_K

# Instantiate the new OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

DISALLOWED_KEYWORDS = ["salary", "salaries", "wage", "wages", "private HR"]

def is_disallowed_query(query: str) -> bool:
    query_lc = query.lower()
    for kw in DISALLOWED_KEYWORDS:
        if kw in query_lc:
            return True
    return False

def generate_answer(question: str) -> str:
    # 1) Check for disallowed queries
    if is_disallowed_query(question):
        return "I’m sorry, but I cannot answer that."

    # 2) Retrieve top-K relevant chunks from Chroma
    results = collection.query(
        query_texts=[question],
        n_results=TOP_K
    )
    retrieved_docs = results["documents"][0]
    
    # 3) Combine retrieved snippets into context text
    context_text = ""
    for i, doc_text in enumerate(retrieved_docs):
        context_text += f"Snippet {i+1}:\n{doc_text}\n\n"

    # 4) Construct the prompt with system instructions and user question
    system_prompt = (
        "You are a helpful assistant that only uses the provided text snippets. "
        "If you do not see an answer in the context, say 'I don’t know'. "
        "Never reveal any private or sensitive info. "
        "Never mention salaries or private HR."
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
    return final_answer
