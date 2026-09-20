import hashlib
import re

import chromadb


# -----------------------------------
# Connect to ChromaDB
# -----------------------------------

client = chromadb.PersistentClient(
    path="./chroma_db"
)


# -----------------------------------
# Get or create collection
# -----------------------------------

collection = client.get_or_create_collection(
    name="medical_reports"
)


def document_id_from_file(file_path):
    """Return a stable document ID derived from the file contents."""
    digest = hashlib.sha256()

    with open(file_path, "rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(block)

    return digest.hexdigest()


def delete_document(document_id):
    """Delete only the chunks belonging to one document."""
    collection.delete(
        where={"document_id": document_id}
    )


def _page_from_chunk(chunk):
    match = re.search(r"^--- Page (\d+) ---", chunk)
    return int(match.group(1)) if match else None


# -----------------------------------
# Store chunks and embeddings
# -----------------------------------

def store_chunks(
    chunks,
    embeddings,
    document_id=None,
    filename="unknown",
    file_path=None
):

    if not chunks:
        raise ValueError("No chunks provided.")

    if len(chunks) != len(embeddings):
        raise ValueError(
            "Number of chunks and embeddings must match."
        )

    if document_id is None:
        if file_path is None:
            raise ValueError(
                "A document_id or file_path is required."
            )
        document_id = document_id_from_file(file_path)

    delete_document(document_id)

    ids = [
        f"{document_id}_chunk_{i}"
        for i in range(len(chunks))
    ]

    metadatas = []
    for i, chunk in enumerate(chunks):
        metadata = {
            "document_id": document_id,
            "filename": filename,
            "chunk_index": i
        }

        page = _page_from_chunk(chunk)
        if page is not None:
            metadata["page"] = page

        metadatas.append(metadata)

    collection.add(
        ids=ids,
        documents=chunks,
        embeddings=embeddings.tolist()
        if hasattr(embeddings, "tolist")
        else embeddings,
        metadatas=metadatas
    )

    return collection.count()