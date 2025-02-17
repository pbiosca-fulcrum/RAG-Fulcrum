import os
import uuid
from typing import List
from openai import OpenAI
from unstructured.partition.pdf import partition_pdf
from unstructured.partition.docx import partition_docx
from unstructured.partition.text import partition_text
from unstructured.partition.xlsx import partition_xlsx
import docx2txt
import pandas as pd
from PIL import Image
import base64
import io

from database import collection
from config import OPENAI_API_KEY, EMBEDDINGS_MODEL, CHAT_MODEL

# Instantiate the new OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

def extract_image_base64(file_path: str) -> str:
    with open(file_path, "rb") as f:
        data = f.read()
    b64_str = base64.b64encode(data).decode('utf-8')
    return b64_str

def summarize_chunk(content: str, chunk_type="text") -> str:
    """
    Uses the new OpenAI client to get a summary for non-text chunks.
    """
    if chunk_type == "text":
        prompt = f"Summarize the following text:\n{content}"
    elif chunk_type == "table":
        prompt = f"Summarize the following table:\n{content}"
    elif chunk_type == "image":
        prompt = (
            "You are an assistant that can interpret images from textual descriptions.\n"
            "This is the base64 content of an image from a user document. Summarize or "
            "describe what it contains in detail:\n"
            f"{content}"
        )
    else:
        prompt = f"Summarize:\n{content}"

    response = client.chat.completions.create(
        model=CHAT_MODEL,
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.0
    )
    return response.choices[0].message.content.strip()

def embed_text(text: str) -> List[float]:
    """
    Converts text into an embedding vector using the new OpenAI client.
    """
    embedding_response = client.embeddings.create(
        input=text,
        model=EMBEDDINGS_MODEL
    )
    vector = embedding_response["data"][0]["embedding"]
    return vector

def chunk_and_embed_file(file_path: str, doc_id: str):
    """
    1) Extract text/tables/images from file
    2) Summarize them if needed
    3) Embed & store in Chroma
    """
    file_ext = os.path.splitext(file_path)[1].lower()
    docs_to_embed = []

    if file_ext == ".pdf":
        elements = partition_pdf(file_path, infer_table_structure=True)
        for el in elements:
            if el.category == "Table":
                summary = summarize_chunk(el.text, chunk_type="table")
                docs_to_embed.append(summary)
            elif el.category == "Image":
                # You can add image handling here if desired.
                pass
            else:
                docs_to_embed.append(el.text)
    elif file_ext == ".docx":
        elements = partition_docx(file_path)
        for el in elements:
            docs_to_embed.append(el.text)
    elif file_ext == ".xlsx":
        elements = partition_xlsx(file_path)
        for el in elements:
            if el.category == "Table":
                summary = summarize_chunk(el.text, chunk_type="table")
                docs_to_embed.append(summary)
            else:
                docs_to_embed.append(el.text)
    elif file_ext in [".txt"]:
        elements = partition_text(file_path)
        for el in elements:
            docs_to_embed.append(el.text)
    elif file_ext in [".png", ".jpg", ".jpeg"]:
        b64_str = extract_image_base64(file_path)
        summary = summarize_chunk(b64_str, chunk_type="image")
        docs_to_embed.append(summary)

    # Embed each chunk and add to the Chroma collection.
    for content in docs_to_embed:
        if not content.strip():
            continue
        vector = embed_text(content)
        chunk_id = str(uuid.uuid4())
        metadata = {"doc_id": doc_id, "chunk_id": chunk_id}
        collection.add(
            documents=[content],
            embeddings=[vector],
            ids=[chunk_id],
            metadatas=[metadata]
        )
