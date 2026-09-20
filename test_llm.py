import ollama


response = ollama.chat(
    model="gemma3:4b",
    messages=[
        {
            "role": "user",
            "content": "What is fasting blood sugar?"
        }
    ]
)


print("\nLLM Response:\n")
print(response["message"]["content"])