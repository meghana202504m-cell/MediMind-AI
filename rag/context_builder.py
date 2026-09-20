def build_context(retrieved_chunks):
    context = "--- Medical Report Context ---\n\n"

    for i, chunk in enumerate(retrieved_chunks, start=1):
        context += f"[Section {i}]\n"
        context += chunk
        context += "\n\n"

    context += "--- End Context ---"

    return context