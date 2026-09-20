from rag.context_builder import build_context
from rag.llm import generate_answer
from rag.retriever import retrieve_chunks


def main():
    question = input("Ask a question about the medical report: ")
    results = retrieve_chunks(question, top_k=3)
    retrieved_chunks = results["documents"][0]
    context = build_context(retrieved_chunks)
    answer = generate_answer(context, question)

    print("\n" + "=" * 60)
    print("MEDIMIND AI ANSWER")
    print("=" * 60)
    print(answer)


if __name__ == "__main__":
    main()