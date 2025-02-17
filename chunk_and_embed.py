import os
import uuid
from typing import List, Tuple
from openai import OpenAI
import openai
from unstructured.partition.pdf import partition_pdf
from unstructured.partition.docx import partition_docx
from unstructured.partition.text import partition_text
from unstructured.partition.xlsx import partition_xlsx
# You can import more partitioners from unstructured, or use alternative libraries
import docx2txt
import pandas as pd
from PIL import Image
import base64
import io

from database import collection
from config import OPENAI_API_KEY, EMBEDDINGS_MODEL, CHAT_MODEL

# Make sure to set the OpenAI key for usage in your code
openai.api_key = OPENAI_API_KEY

# A small function to read images, convert to base64, etc.
def extract_image_base64(file_path: str) -> str:
    with open(file_path, "rb") as f:
        data = f.read()
    b64_str = base64.b64encode(data).decode('utf-8')
    return b64_str

# Summaries for any chunk that’s not directly textual
def summarize_chunk(content: str, chunk_type="text") -> str:
    """
    Simple function that uses a ChatCompletion to summarize content
    chunk_type can be "text", "table", or "image"
    """
    # Adjust your prompt. You might also do specialized
    # prompts for images vs tables.
    prompt = ""
    if chunk_type == "text":
        prompt = f"Summarize the following text:\n{content}"
    elif chunk_type == "table":
        prompt = f"Summarize the following table:\n{content}"
    elif chunk_type == "image":
        # We can embed base64 or we can just say "we have an image about..."
        # to produce a textual summary.
        prompt = (
            "You are an assistant that can interpret images from textual descriptions.\n"
            "This is the base64 content of an image from a user document. Summarize or "
            "describe what it contains in detail:\n"
            f"{content}"
        )
    else:
        prompt = f"Summarize:\n{content}"

    # Use gpt-4o or gpt-4o-mini, as you like. We'll keep it simple here.
    response = openai.ChatCompletion.create(
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
    Convert text to an embedding vector using text-embedding-3-large
    """
    # For the new client library usage:
    # from openai import OpenAI
    # client = OpenAI()
    # return ...
    embedding_response = openai.Embedding.create(
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
    # For storing chunk data: chunk_id -> text or summary
    docs_to_embed = []

    if file_ext == ".pdf":
        elements = partition_pdf(file_path, infer_table_structure=True)
        # Each element is either text, table, or a composite that might hold images, etc.
        for el in elements:
            # If it's a table, we can get HTML or text representation from unstructured
            if el.category == "Table":
                summary = summarize_chunk(el.text, chunk_type="table")
                docs_to_embed.append(summary)
            elif el.category == "Image":
                # In unstructured, 'Image' might have base64 already or
                # you might need to read from the PDF in a different approach
                # For simplicity, let's do a textual summary with "image" placeholder
                # If you do have base64 in `el.metadata`, then pass it to summarize_chunk
                pass
            else:
                # Text block
                # If it's short enough, we can keep it as is
                docs_to_embed.append(el.text)

    elif file_ext == ".docx":
        # Use partition_docx or docx2txt
        elements = partition_docx(file_path)
        for el in elements:
            docs_to_embed.append(el.text)
    elif file_ext == ".xlsx":
        # partition_xlsx returns a list of elements, including tables
        elements = partition_xlsx(file_path)
        for el in elements:
            if el.category == "Table":
                # Summarize
                summary = summarize_chunk(el.text, chunk_type="table")
                docs_to_embed.append(summary)
            else:
                docs_to_embed.append(el.text)

    elif file_ext in [".txt"]:
        elements = partition_text(file_path)
        for el in elements:
            docs_to_embed.append(el.text)

    elif file_ext in [".png", ".jpg", ".jpeg"]:
        # Summarize the image
        b64_str = extract_image_base64(file_path)
        summary = summarize_chunk(b64_str, chunk_type="image")
        docs_to_embed.append(summary)

    # Now chunk docs_to_embed if needed (e.g. splitting large text).
    # For brevity, assume each item in docs_to_embed is small enough.
    # Then embed and store in Chroma.
    for content in docs_to_embed:
        if not content.strip():
            continue
        vector = embed_text(content)
        chunk_id = str(uuid.uuid4())
        metadata = {"doc_id": doc_id, "chunk_id": chunk_id}
        # Add to Chroma
        collection.add(
            documents=[content],
            embeddings=[vector],
            ids=[chunk_id],
            metadatas=[metadata]
        )

