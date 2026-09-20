from rag.retriever import retrieve_chunks
from rag.context_builder import build_context


question = "What is the fasting blood sugar?"

results = retrieve_chunks(
    question,
    top_k=3
)


retrieved_chunks = results["documents"][0]


context = build_context(
    retrieved_chunks
)


print(context)