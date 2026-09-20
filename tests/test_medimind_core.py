from pathlib import Path

from fastapi.testclient import TestClient

from app import app

client = TestClient(app)


def _report_bytes() -> bytes:
    report_path = Path(__file__).resolve().parent.parent / 'data' / 'reports' / 'blood_report.pdf'
    return report_path.read_bytes()


def test_health_endpoint():
    response = client.get('/health')
    assert response.status_code == 200
    payload = response.json()
    assert payload['status'] in {'healthy', 'ok'}


def test_general_medical_question_and_duplicate_upload():
    general = client.post('/chat', json={'question': 'What is HbA1c?'})
    assert general.status_code == 200
    assert 'HbA1c' in general.json()['answer'] or 'A1c' in general.json()['answer']

    pdf_bytes = _report_bytes()
    file_payload = ('blood_report.pdf', pdf_bytes, 'application/pdf')
    first = client.post('/upload', files={'file': file_payload})
    assert first.status_code == 200
    report_id = first.json()['document_id']

    second = client.post('/upload', files={'file': file_payload})
    assert second.status_code == 200
    assert second.json()['document_id'] == report_id

    chat = client.post('/chat', json={'question': 'What is my HbA1c?', 'document_id': report_id})
    assert chat.status_code == 200


def test_history_endpoints_exist():
    response = client.get('/reports')
    assert response.status_code == 200
    payload = response.json()
    assert 'reports' in payload

    patient_response = client.get('/patients/test-patient/reports')
    assert patient_response.status_code == 200
