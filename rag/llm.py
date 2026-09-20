import ollama


def _generate(prompt):
    response = ollama.chat(
        model="gemma3:4b",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    return response["message"]["content"].strip()


def generate_answer(context, question, question_type="REPORT"):
    if question_type == "GENERAL":
        return generate_general_answer(question)

    if question_type == "MIXED":
        prompt = f"""
You are MediMind AI, an educational medical-report assistant.
Use ONLY the report context for patient-specific facts. Explain general medical
meaning separately. Do not diagnose, prescribe, or give medication instructions.
Do not invent patient values or reference ranges. Use simple language and advise
professional medical consultation when clinical judgment is needed.

Clearly label the two parts as "According to the report" and "General explanation"
when both apply. If a requested report fact is absent, say it is not available.

Report context:
{context}

User question: {question}

Answer:
"""
        return _generate(prompt)

    prompt = f"""
You are MediMind AI, an educational medical-report assistant.

Your task is to answer the user's question using ONLY the
information provided in the medical report context.

IMPORTANT RULES:

1. Give the patient's actual RESULT when the question asks
   for a test value.

2. Do NOT confuse the patient's result with the reference range.

3. If a test is shown in this format:

   TEST NAME
   RESULT
   REFERENCE RANGE

   then the first value after the test name is the patient's
   result, while the following values represent the reference
   range.

4. Do not include reference-range values as the patient's result.

5. Do not invent or assume information that is not present
   in the context.

6. If the requested information is not present in the context,
   say:
   "I could not find this information in the provided medical report."

7. Give the answer as a complete, natural-language sentence.

8. Never return only a number, value, or short fragment.

Examples:

Question: What is the fasting blood sugar?
Correct: The fasting blood sugar is 103 mg/dL.
Incorrect: 103 mg/dL

Question: What is the patient's age?
Correct: The patient is 52 years old.
Incorrect: 52

Question: What is the patient's sex?
Correct: The patient is female.
Incorrect: Female

9. Include the appropriate unit when it is available in the medical report.
10. Do not diagnose, prescribe, or give medication instructions.
11. Recommend professional medical consultation when clinical judgment is needed.

Medical Report Context:
{context}

User Question:
{question}

Answer:
"""

    return _generate(prompt)


def generate_general_answer(question):
    prompt = f"""
You are MediMind AI, an educational medical assistant.
Answer the question as general medical education, not as a statement about the
user or an uploaded report. Use simple language. Do not diagnose, prescribe,
or tell the user to start or stop medication. Recommend a qualified healthcare
professional when the question requires personal clinical judgment.

Question: {question}

Answer:
"""
    return _generate(prompt)