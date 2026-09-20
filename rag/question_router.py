import re

import ollama


QUESTION_TYPES = {"REPORT", "GENERAL", "MIXED"}


def _normalize_question(question):
    return re.sub(r"\s+", " ", str(question or "").strip().lower())


def _contains_any(question, phrases):
    return any(phrase in question for phrase in phrases)


def _is_patient_context(question):
    patient_phrases = (
        "my ", "mine", "in my report", "according to my report", "my report",
        "my result", "my value", "my level", "my fasting", "my hemoglobin",
        "my hba1c", "my creatinine", "my cholesterol", "my tsh",
        "this result in my report", "result in my report", "value in my report",
        "summarize my report", "important findings in my report",
        "abnormal results in my report", "outside the reference range",
        "is my ", "explain my ", "what does my ", "what is my ", "what is my result",
        "what does this mean", "what does that mean", "is it normal", "is this normal"
    )
    return _contains_any(question, patient_phrases)


def _is_mixed_interpretation(question):
    explicit_mixed_patterns = (
        "what does my ", "what does this mean", "what does that mean",
        "explain my ", "interpret my ", "what does my result mean",
        "what does my value mean", "what does my level mean",
        "what does this abnormal result mean"
    )
    if _contains_any(question, explicit_mixed_patterns):
        return True

    if "my " in question and (
        "what does" in question or "explain" in question or "interpret" in question
    ) and any(token in question for token in ("mean", "normal", "abnormal", "high", "low", "outside", "inside", "range")):
        return True

    if "my " in question and "normal" in question and ("what does" in question or "is my" in question):
        return True

    return False


def _is_definition_or_general(question):
    general_phrases = (
        "what is ", "what does ", "what are ", "define ", "definition of ",
        "meaning of ", "what is the normal range of ", "what is the range of ",
        "why is a ", "why is ", "what does ", "what is blood pressure",
        "what is cholesterol", "what is creatinine", "what is hemoglobin"
    )
    return _contains_any(question, general_phrases)


def _is_explanation_or_interpretation(question):
    explanation_phrases = (
        "mean", "means", "explain", "interpret", "normal", "abnormal",
        "high", "low", "within range", "outside range", "reference range",
        "what does this mean", "what does that mean", "is it normal", "is this normal"
    )
    return _contains_any(question, explanation_phrases)


def _fallback_question_type(question):
    normalized = _normalize_question(question)

    if _is_mixed_interpretation(normalized):
        return "MIXED"
    if _is_patient_context(normalized):
        if re.search(r"^(what is|what does|what are|is|are)\s+my\b", normalized) and not any(token in normalized for token in ("mean", "explain", "interpret", "normal", "abnormal", "high", "low", "outside", "range")):
            return "REPORT"
        if _is_explanation_or_interpretation(normalized):
            return "REPORT"
        return "REPORT"
    if _is_definition_or_general(normalized):
        return "GENERAL"
    if "my " in normalized:
        return "REPORT"
    return "GENERAL"


def route_question(question, report_context=None):
    """Classify a question as REPORT, GENERAL, or MIXED using local Gemma and safeguards."""
    normalized = _normalize_question(question)

    heuristic_type = _fallback_question_type(normalized)
    if heuristic_type in QUESTION_TYPES:
        return heuristic_type

    prompt = (
        "You classify medical assistant questions. Return exactly one word.\n"
        "REPORT: asks for a patient-specific value from an uploaded report or a report summary.\n"
        "GENERAL: asks for general medical knowledge with no patient-specific report context.\n"
        "MIXED: includes the patient's result and asks for general meaning or interpretation.\n"
        "Examples: 'What is my fasting blood sugar?'=REPORT; "
        "'What does HbA1c mean?'=GENERAL; "
        "'What does my HbA1c result mean?'=MIXED; "
        "'Summarize my report.'=REPORT.\n"
        f"Question: {question}"
    )

    try:
        response = ollama.chat(
            model="gemma3:4b",
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0}
        )
        output = response.get("message", {}).get("content", "").upper()
        match = re.search(r"\b(REPORT|GENERAL|MIXED)\b", output)
        model_type = match.group(1) if match else None
        if model_type in QUESTION_TYPES:
            return model_type
    except Exception:
        pass

    return heuristic_type
