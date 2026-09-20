import chromadb
from sentence_transformers import SentenceTransformer


_model = None


def get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


# -----------------------------------
# Connect to ChromaDB
# -----------------------------------

client = chromadb.PersistentClient(
    path="./chroma_db"
)


collection = client.get_or_create_collection(
    name="medical_reports"
)


# -----------------------------------
# Retrieve relevant chunks
# -----------------------------------

def retrieve_chunks(query, top_k=3, document_id=None):

    query_embedding = get_model().encode(
        [query]
    ).tolist()

    query_options = {
        "query_embeddings": query_embedding,
        "n_results": top_k,
    }
    if document_id:
        query_options["where"] = {"document_id": document_id}

    results = collection.query(**query_options)

    return results


# -----------------------------------
# Test
# -----------------------------------

if __name__ == "__main__":

    question = input(
        "Ask a question about the medical report: "
    )

    results = retrieve_chunks(
        question,
        top_k=3
    )

    print("\nRetrieved information:\n")

    documents = results["documents"][0]
    distances = results["distances"][0]

    for i, (document, distance) in enumerate(
        zip(documents, distances),
        start=1
    ):

        print(f"Chunk {i}:")
        print(document)

        print(
            f"Similarity distance: {distance:.4f}"
        )

        print("-" * 50)