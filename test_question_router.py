from unittest.mock import patch

from rag.question_router import route_question
from backend.services import answer_question


ROUTING_CASES = {
    "What is my fasting blood sugar?": "REPORT",
    "What is my post prandial blood sugar?": "REPORT",
    "What does HbA1c mean?": "GENERAL",
    "What is creatinine?": "GENERAL",
    "My creatinine value is high. What does creatinine mean?": "MIXED",
    "What does my fasting blood sugar result mean?": "MIXED",
    "Summarize my report.": "REPORT",
    "What is cholesterol?": "GENERAL",
    "Which values in my report are outside their stated reference ranges?": "REPORT",
}


def main():
    for question, expected_type in ROUTING_CASES.items():
        actual_type = route_question(question)
        assert actual_type == expected_type, (question, actual_type, expected_type)

    with patch("backend.services.collection.count", return_value=0):
        no_report = answer_question("What is my fasting blood sugar?")

    assert no_report["question_type"] == "REPORT"
    assert "upload" in no_report["answer"].lower()
    assert no_report["sources"] == []
    print("QUESTION_ROUTER_CHECK: PASS")
    print("NO_REPORT_CHECK: PASS")


if __name__ == "__main__":
    main()
