import os
import uuid
from typing import List
import datetime
from openai import OpenAI
from unstructured.partition.pdf import partition_pdf
from unstructured.partition.docx import partition_docx
from unstructured.partition.text import partition_text
from unstructured.partition.xlsx import partition_xlsx
import base64
from PIL import Image
import io
import tiktoken  # For tokenization

from database import collection
from config import OPENAI_API_KEY, EMBEDDINGS_MODEL, CHAT_MODEL

client = OpenAI(api_key=OPENAI_API_KEY)

encoder = tiktoken.get_encoding("cl100k_base")

def truncate_to_8100_tokens(text: str) -> str:
    tokens = encoder.encode(text)
    if len(tokens) > 8100:
        tokens = tokens[:8100]
    return encoder.decode(tokens)

def extract_image_base64(file_path: str) -> str:
    """Extracts image as reduced-resolution base64 to avoid huge tokens."""
    try:
        img = Image.open(file_path)
        img.thumbnail((400, 400))
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=50)
        return base64.b64encode(buffer.getvalue()).decode('utf-8')
    except Exception as e:
        with open(file_path, "rb") as f:
            data = f.read()
        return base64.b64encode(data).decode('utf-8')

def summarize_chunk(content: str, chunk_type="text") -> str:
    if chunk_type == "text":
        prompt = f"Summarize the following text:\n{content}"
    elif chunk_type == "table":
        prompt = f"Summarize the following table:\n{content}"
    elif chunk_type == "image":
        prompt = (
            "You are an assistant that can interpret images from textual descriptions.\n"
            "Below is the base64 content of an image from a user document. Summarize or "
            "describe what it contains in a concise manner:\n" + content
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
    embedding_response = client.embeddings.create(
        input=text,
        model=EMBEDDINGS_MODEL
    )
    vector = embedding_response.data[0].embedding
    return vector

def generate_document_title(file_path: str) -> str:
    ext = os.path.splitext(file_path)[1].lower()
    content = ""
    if ext == ".txt":
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read(500)
    elif ext == ".pdf":
        try:
            elements = partition_pdf(
                file_path,
                infer_table_structure=True,
                strategy="hi_res",
                max_characters=20000,
                combine_text_under_n_chars=10000,
                new_after_n_chars=16000
            )
            for el in elements:
                if el.text.strip():
                    content += el.text + " "
                if len(content) > 500:
                    break
        except Exception as e:
            # Fallback to PyPDF2
            try:
                from PyPDF2 import PdfReader
                reader = PdfReader(file_path)
                extracted_text = ""
                for page in reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        extracted_text += page_text + " "
                content = extracted_text[:500]
            except Exception:
                content = "Document"
    elif ext == ".docx":
        elements = partition_docx(file_path)
        for el in elements:
            if hasattr(el, 'category') and el.category == "Image":
                image_data = extract_image_base64(file_path)
                summary = summarize_chunk(image_data, chunk_type="image")
                content += " " + summary
            else:
                content += " " + el.text
            if len(content) > 500:
                break

    if not content:
        content = "Document"

    prompt = f"Generate a concise and appropriate title for the following document content:\n{content}\nTitle:"
    response = client.chat.completions.create(
        model=CHAT_MODEL,
        messages=[
            {"role": "system", "content": "You are a creative assistant."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.5
    )
    title = response.choices[0].message.content.strip()
    return title

def chunk_and_embed_file(file_path: str, doc_id: str, extra_metadata=None):
    file_ext = os.path.splitext(file_path)[1].lower()
    docs_to_embed = []

    if file_ext == ".pdf":
        try:
            elements = partition_pdf(
                file_path,
                infer_table_structure=True,
                strategy="hi_res",
                max_characters=20000,
                combine_text_under_n_chars=10000,
                new_after_n_chars=16000
            )
        except Exception as e:
            # Log fallback usage
            print(f"[{datetime.datetime.utcnow().isoformat()}] FALLBACK triggered for PDF: unstructured partition failed with error: {e}")
            try:
                from PyPDF2 import PdfReader
                reader = PdfReader(file_path)
                extracted_text = ""
                for page in reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        extracted_text += page_text + " "
                class DummyElement:
                    category = "Text"
                    text = extracted_text
                elements = [DummyElement()]
            except Exception as e2:
                raise Exception("Error processing PDF using both methods: " + str(e) + " | " + str(e2))

        for el in elements:
            if el.category == "Table":
                summary = summarize_chunk(el.text, chunk_type="table")
                docs_to_embed.append(summary)
            elif el.category == "Image":
                image_data = extract_image_base64(file_path)
                summary = summarize_chunk(image_data, chunk_type="image")
                docs_to_embed.append(summary)
            else:
                docs_to_embed.append(el.text)

    elif file_ext == ".docx":
        elements = partition_docx(file_path)
        combined_text = ""
        for el in elements:
            if hasattr(el, 'category') and el.category == "Image":
                image_data = extract_image_base64(file_path)
                summary = summarize_chunk(image_data, chunk_type="image")
                combined_text += "\n" + summary
            else:
                combined_text += "\n" + el.text
        docs_to_embed.append(combined_text)

    elif file_ext == ".xlsx":
        elements = partition_xlsx(file_path)
        for el in elements:
            if el.category == "Table":
                summary = summarize_chunk(el.text, chunk_type="table")
                docs_to_embed.append(summary)
            else:
                docs_to_embed.append(el.text)

    elif file_ext == ".txt":
        elements = partition_text(file_path)
        for el in elements:
            docs_to_embed.append(el.text)

    elif file_ext in [".png", ".jpg", ".jpeg"]:
        b64_str = extract_image_base64(file_path)
        summary = summarize_chunk(b64_str, chunk_type="image")
        docs_to_embed.append(summary)

    if extra_metadata is None:
        extra_metadata = {}

    print(f"Extracted text for document {file_path}:")
    for i, chunk in enumerate(docs_to_embed):
        preview = chunk[:200] + ("..." if len(chunk) > 200 else "")
        print(f"Chunk {i+1}: {preview}")

    # Embed each chunk, truncating to 8100 tokens if needed
    for content in docs_to_embed:
        if not content.strip():
            continue
        content = truncate_to_8100_tokens(content)

        vector = embed_text(content)
        chunk_id = str(uuid.uuid4())
        metadata = {"doc_id": doc_id, "chunk_id": chunk_id}
        metadata.update(extra_metadata)
        collection.add(
            documents=[content],
            embeddings=[vector],
            ids=[chunk_id],
            metadatas=[metadata]
        )
