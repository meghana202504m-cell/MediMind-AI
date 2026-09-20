from unittest.mock import patch

from fastapi.testclient import TestClient

from app import CHAT_MEMORY, app
from rag.llm import generate_answer


client = TestClient(app)


def setup_function():
    CHAT_MEMORY.clear()


def test_prompt_contains_supported_language_instruction():
    captured = {}

    def fake_generate(prompt):
        captured["prompt"] = prompt
        return "respuesta"

    with patch("rag.llm._generate", side_effect=fake_generate):
        answer = generate_answer(
            "HbA1c: 7%",
            "What does my HbA1c mean?",
            question_type="MIXED",
            language="kn",
        )

    assert answer == "respuesta"
    assert "Respond entirely in Kannada" in captured["prompt"]
    assert "HbA1c: 7%" in captured["prompt"]
    assert "What does my HbA1c mean?" in captured["prompt"]


def test_general_questions_pass_english_kannada_and_hindi_to_llm():
    for language in ("en", "kn", "hi"):
        with patch("app.route_question", return_value="GENERAL"), patch(
            "app.generate_answer", return_value=f"{language} answer"
        ) as mocked_generate:
            response = client.post(
                "/chat",
                json={"question": "What is HbA1c?", "language": language},
            )

        assert response.status_code == 200
        assert response.json()["answer"] == f"{language} answer"
        assert mocked_generate.call_args.kwargs["language"] == language


def test_report_question_passes_language_and_context_to_llm():
    with patch("app.route_question", return_value="REPORT"), patch(
        "app.retrieve_chunks",
        return_value={"documents": [["HbA1c: 7%"]], "metadatas": [[]]},
    ), patch("app.build_context", return_value="HbA1c: 7%"), patch(
        "app.generate_answer", return_value="ಕನ್ನಡ ಉತ್ತರ"
    ) as mocked_generate:
        response = client.post(
            "/chat",
            json={
                "question": "What does my HbA1c mean?",
                "document_id": "report-1",
                "language": "kn",
            },
        )

    assert response.status_code == 200
    assert response.json()["answer"] == "ಕನ್ನಡ ಉತ್ತರ"
    assert mocked_generate.call_args.kwargs["language"] == "kn"
    assert mocked_generate.call_args.kwargs["conversation_context"] == ""


def test_follow_up_reuses_selected_language_and_conversation_context():
    with patch("app.route_question", return_value="GENERAL"), patch(
        "app.generate_answer", side_effect=["पहला उत्तर", "दूसरा उत्तर"]
    ) as mocked_generate:
        first = client.post(
            "/chat",
            json={"question": "What is HbA1c?", "language": "hi"},
        )
        second = client.post(
            "/chat",
            json={"question": "Is that serious?"},
        )

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["answer"] == "दूसरा उत्तर"
    assert mocked_generate.call_args_list[1].kwargs["language"] == "hi"
    assert "What is HbA1c?" in mocked_generate.call_args_list[1].kwargs["conversation_context"]
    assert "पहला उत्तर" in mocked_generate.call_args_list[1].kwargs["conversation_context"]


def test_unsupported_language_code_is_rejected_by_chat_contract():
    response = client.post(
        "/chat",
        json={"question": "What is HbA1c?", "language": "xx"},
    )

    assert response.status_code == 422


def test_report_prompt_prioritizes_report_reference_range():
    captured = {}

    def fake_generate(prompt):
        captured["prompt"] = prompt
        return "The value is within the report range."

    with patch("rag.llm._generate", side_effect=fake_generate):
        generate_answer(
            "Fasting Blood Sugar: 103 mg/dL\nReference Range: 70-110 mg/dL",
            "Is my fasting blood sugar high?",
            language="en",
        )

    normalized_prompt = " ".join(captured["prompt"].split())
    assert "use that range as the authority" in normalized_prompt
    assert "Do not substitute a generic range" in normalized_prompt
    assert "Do not call a result high, low, abnormal, or elevated" in normalized_prompt


def test_mixed_kannada_output_is_regenerated_once():
    with patch(
        "rag.llm._generate",
        side_effect=["ನಿಮ್ಮ value रक्त 103 mg/dL ಆಗಿದೆ.", "ನಿಮ್ಮ ಮೌಲ್ಯ 103 mg/dL ಆಗಿದೆ."],
    ) as mocked_generate:
        answer = generate_answer(
            "Fasting Blood Sugar: 103 mg/dL",
            "Explain my report.",
            language="kn",
        )

    assert answer == "ನಿಮ್ಮ ಮೌಲ್ಯ 103 mg/dL ಆಗಿದೆ."
    assert mocked_generate.call_count == 2
    assert "Rewrite the answer once using only the selected language script" in mocked_generate.call_args_list[1].args[0]
