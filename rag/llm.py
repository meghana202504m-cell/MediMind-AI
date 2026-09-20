import re

import ollama

LANGUAGE_NAMES = {"en": "English", "kn": "Kannada", "hi": "Hindi"}


def _language_instruction(language):
    instructions = {
        "en": "Respond entirely in English.",
        "kn": (
            "Respond entirely in Kannada. Use natural, standard Kannada. "
            "Do not mix other languages or scripts unless a medical or scientific "
            "term has no suitable Kannada equivalent."
        ),
        "hi": (
            "Respond entirely in Hindi. Use natural, standard Hindi. "
            "Do not mix Kannada, other Indic scripts, Arabic, Urdu, or other "
            "languages unnecessarily."
        ),
    }
    return (
        f"{instructions.get(language, instructions['en'])} Keep numbers, units, "
        "medical abbreviations, and universally used medical terms such as mg/dL unchanged."
    )


def _contains_mixed_script(answer, language):
    script_ranges = {
        "en": r"[\u0900-\u097F\u0C00-\u0C7F\u0C80-\u0CFF]",
        "kn": r"[\u0900-\u097F\u0C00-\u0C7F]",
        "hi": r"[\u0C00-\u0CFF\u0600-\u06FF]",
    }
    pattern = script_ranges.get(language)
    return bool(pattern and re.search(pattern, answer or ""))


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


def _generate_localized(prompt, language):
    answer = _generate(prompt)
    if not _contains_mixed_script(answer, language):
        return answer

    retry_prompt = (
        f"{prompt}\n\nIMPORTANT: {_language_instruction(language)} "
        "Rewrite the answer once using only the selected language script. "
        "Preserve report values, reference ranges, units, abbreviations, and numbers exactly."
    )
    return _generate(retry_prompt)


def generate_answer(context, question, question_type="REPORT", language="en", conversation_context=""):
    if question_type == "GENERAL":
        return generate_general_answer(question, language, conversation_context)

    if question_type == "MIXED":
        prompt = f"""
You are MediMind AI, an educational medical-report assistant.
{_language_instruction(language)}
Use ONLY the report context for patient-specific facts. Explain general medical
meaning separately. Do not diagnose, prescribe, or give medication instructions.
Do not invent patient values or reference ranges. Use simple language and advise
professional medical consultation when clinical judgment is needed.

Clearly separate report facts from general meaning when both apply. If a requested
report fact is absent, say so in the selected language. When the report provides a
reference range, use that range as the authority and do not substitute a generic range.

Report context:
{context}

User question: {question}

Conversation context:
{conversation_context or "No previous conversation."}

Answer:
"""
        return _generate_localized(prompt, language)

    prompt = f"""
You are MediMind AI, an educational medical-report assistant.
{_language_instruction(language)}

Your task is to answer the user's question using ONLY the
information provided in the medical report context.

IMPORTANT RULES:

1. Give the patient's actual RESULT when the question asks
   for a test value.

2. Do NOT confuse the patient's result with the reference range.

3. If a test is shown with a result and a reference range, use that range as
    the authority for normal, high, or low interpretation. Do not substitute a
    generic range.
4. Do not call a result high, low, abnormal, or elevated when it is within the
    reference range stated in the report.
5. If the requested information is not present in the context, say so in the
    selected language.
6. Give the answer as a complete, natural-language sentence.
7. Never return only a number, value, or short fragment.
8. Include the appropriate unit when it is available in the medical report.
9. Do not diagnose, prescribe, or give medication instructions.
10. Recommend professional medical consultation when clinical judgment is needed.
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

Medical Report Context:
{context}

User Question:
{question}

Conversation context:
{conversation_context or "No previous conversation."}

Answer:
"""

    return _generate_localized(prompt, language)


def generate_general_answer(question, language="en", conversation_context=""):
    prompt = f"""
You are MediMind AI, an educational medical assistant.
{_language_instruction(language)}
Answer the question as general medical education, not as a statement about the
user or an uploaded report. Use simple language. Do not diagnose, prescribe,
or tell the user to start or stop medication. Recommend a qualified healthcare
professional when the question requires personal clinical judgment.

Question: {question}

Conversation context:
{conversation_context or "No previous conversation."}

Answer:
"""
    return _generate_localized(prompt, language)