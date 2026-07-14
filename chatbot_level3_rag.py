import os
import uuid
from pathlib import Path

import chromadb
from dotenv import load_dotenv
from google import genai
from google.genai import types
from pypdf import PdfReader


# -----------------------------
# Setup
# -----------------------------

load_dotenv()

api_key = os.getenv("GOOGLE_API_KEY")

if not api_key:
    raise ValueError("GOOGLE_API_KEY not found. Check your .env file.")

client = genai.Client(api_key=api_key)

CHAT_MODEL = "gemini-3.1-flash-lite"
EMBEDDING_MODEL = "gemini-embedding-001"

CHROMA_DB_DIR = "chroma_db"
COLLECTION_NAME = "basic_rag_collection"

chroma_client = chromadb.PersistentClient(path=CHROMA_DB_DIR)

collection = chroma_client.get_or_create_collection(
    name=COLLECTION_NAME
)


# -----------------------------
# Read uploaded file
# -----------------------------

def read_file(file_path: str) -> str:
    """
    Reads .txt, .md, or .pdf files and returns text.
    """

    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    if path.suffix.lower() in [".txt", ".md"]:
        return path.read_text(encoding="utf-8")

    if path.suffix.lower() == ".pdf":
        reader = PdfReader(str(path))
        text = ""

        for page_number, page in enumerate(reader.pages, start=1):
            page_text = page.extract_text() or ""
            text += f"\n\n--- Page {page_number} ---\n"
            text += page_text

        return text

    raise ValueError("Only .txt, .md, and .pdf files are supported.")


# -----------------------------
# Chunking
# -----------------------------

def chunk_text(text: str, chunk_size: int = 800, overlap: int = 150) -> list[str]:
    """
    Splits large text into smaller overlapping chunks.
    """

    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]

        if chunk.strip():
            chunks.append(chunk.strip())

        start = end - overlap

    return chunks


# -----------------------------
# Embeddings
# -----------------------------

def create_embedding(text: str) -> list[float]:
    """
    Converts text into an embedding vector using Gemini.
    """

    response = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=text
    )

    return response.embeddings[0].values


# -----------------------------
# Index file into vector DB
# -----------------------------

def index_file(file_path: str) -> str:
    """
    Reads a file, chunks it, creates embeddings, and stores them in Chroma.
    """

    path = Path(file_path)
    text = read_file(file_path)

    if not text.strip():
        return "The file has no readable text."

    chunks = chunk_text(text)

    for chunk_index, chunk in enumerate(chunks):
        chunk_id = f"{path.name}_{chunk_index}_{uuid.uuid4().hex[:8]}"
        embedding = create_embedding(chunk)

        collection.upsert(
            ids=[chunk_id],
            documents=[chunk],
            embeddings=[embedding],
            metadatas=[{
                "file_name": path.name,
                "chunk_index": chunk_index
            }]
        )

    return f"Indexed {len(chunks)} chunks from {path.name}."


# -----------------------------
# Search relevant chunks
# -----------------------------

def search_documents(question: str, top_k: int = 3) -> list[dict]:
    """
    Searches the vector database and returns the most relevant chunks.
    """

    if collection.count() == 0:
        return []

    question_embedding = create_embedding(question)

    results = collection.query(
        query_embeddings=[question_embedding],
        n_results=min(top_k, collection.count())
    )

    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    retrieved_chunks = []

    for doc, metadata, distance in zip(documents, metadatas, distances):
        retrieved_chunks.append({
            "text": doc,
            "file_name": metadata.get("file_name", "unknown"),
            "chunk_index": metadata.get("chunk_index", "unknown"),
            "distance": distance
        })

    return retrieved_chunks


# -----------------------------
# Generate RAG answer
# -----------------------------

def answer_with_rag(question: str) -> str:
    """
    Retrieves relevant chunks and asks Gemini to answer using only those chunks.
    """

    chunks = search_documents(question, top_k=3)

    if collection.count() == 0:
        return "No documents have been indexed yet. Type 'upload' first."

    if not chunks:
        return "I could not find relevant information in the uploaded file."

    context_parts = []

    for index, chunk in enumerate(chunks, start=1):
        context_parts.append(
            f"""
Source {index}
File: {chunk["file_name"]}
Chunk: {chunk["chunk_index"]}

{chunk["text"]}
"""
        )

    context = "\n\n".join(context_parts)

    prompt = f"""
You are a RAG chatbot.

Answer the user's question using only the context below.

Rules:
- Use only the provided context.
- Do not make up information.
- If the answer is not in the context, say: "I could not find this in the uploaded file."
- Mention the source file name in the answer.

Context:
{context}

User question:
{question}

Answer:
"""

    response = client.models.generate_content(
        model=CHAT_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.2,
            max_output_tokens=600
        )
    )

    return response.text


# -----------------------------
# Main chatbot
# -----------------------------

def main():
    print("Basic RAG Chatbot")
    print("Commands:")
    print("  upload  → add/index a file")
    print("  exit    → quit")
    print()

    while True:
        user_input = input("You: ").strip()

        if not user_input:
            continue

        if user_input.lower() in ["exit", "quit", "bye"]:
            print("Bot: Goodbye.")
            break

        if user_input.lower() == "upload":
            file_path = input("Enter file path: ").strip()

            try:
                result = index_file(file_path)
                print("Bot:", result)
                print()
            except Exception as e:
                print("Bot: File upload/indexing error:", e)
                print()

            continue

        try:
            answer = answer_with_rag(user_input)
            print("\nBot:", answer)
            print()

        except Exception as e:
            print("\nBot: Error:", e)
            print()


if __name__ == "__main__":
    main()