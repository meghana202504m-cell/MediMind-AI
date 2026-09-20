import json
import re
import sqlite3
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_DIR = BASE_DIR / 'database'
DB_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DB_DIR / 'medimind.db'


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_connection()
    try:
        conn.execute(
            '''
            CREATE TABLE IF NOT EXISTS patients (
                patient_id TEXT PRIMARY KEY,
                patient_name TEXT,
                age INTEGER,
                sex TEXT,
                doctor TEXT,
                created_at TEXT NOT NULL
            )
            '''
        )
        conn.execute(
            '''
            CREATE TABLE IF NOT EXISTS reports (
                report_id TEXT PRIMARY KEY,
                patient_id TEXT,
                file_hash TEXT,
                source_filename TEXT,
                upload_date TEXT NOT NULL,
                report_date TEXT,
                patient_name TEXT,
                age INTEGER,
                sex TEXT,
                doctor TEXT,
                original_metadata TEXT,
                raw_text TEXT,
                FOREIGN KEY(patient_id) REFERENCES patients(patient_id)
            )
            '''
        )
        conn.execute(
            '''
            CREATE TABLE IF NOT EXISTS biomarker_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                report_id TEXT,
                patient_id TEXT,
                biomarker_name TEXT,
                value REAL,
                unit TEXT,
                reference_low REAL,
                reference_high REAL,
                status TEXT,
                report_date TEXT,
                source_text TEXT,
                FOREIGN KEY(report_id) REFERENCES reports(report_id)
            )
            '''
        )
        conn.execute(
            '''
            CREATE INDEX IF NOT EXISTS idx_reports_patient ON reports(patient_id)
            '''
        )
        conn.execute(
            '''
            CREATE INDEX IF NOT EXISTS idx_reports_date ON reports(report_date)
            '''
        )
        conn.execute(
            '''
            CREATE INDEX IF NOT EXISTS idx_biomarkers_name ON biomarker_results(biomarker_name)
            '''
        )
        conn.commit()
    finally:
        conn.close()


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def file_hash_bytes(data: bytes) -> str:
    return sha256(data).hexdigest()


def patient_id_from_meta(patient_name: str | None, age: int | None, sex: str | None) -> str:
    base = ' '.join(filter(None, [patient_name or 'unknown', str(age or ''), sex or '']))
    return sha256(base.strip().encode('utf-8')).hexdigest()[:20]


def _safe_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_range_from_text(text: str):
    match = re.search(r'(?:\b(?:ref(?:erence)?(?: range)?|range)\b.*?[:=]?\s*)?(\d+(?:\.\d+)?)\s*(?:-|to|–|–|\s*–\s*)\s*(\d+(?:\.\d+)?)', text, flags=re.I)
    if match:
        low = _safe_float(match.group(1))
        high = _safe_float(match.group(2))
        if low is not None and high is not None:
            return low, high
    return None, None


def _status_for_value(value, low, high):
    if value is None:
        return 'unknown'
    if low is not None and high is not None:
        if value < low:
            return 'low'
        if value > high:
            return 'high'
        return 'normal'
    return 'unknown'


def _extract_biomarker_value(name, text):
    patterns = [
        r'(?i)\b' + re.escape(name) + r'\b[^\n]{0,30}[:=]\s*(\d+(?:\.\d+)?)\s*(mg/dL|g/dL|mmol/L|%|IU/L|ng/mL|pg/mL|mmol|U/L|mIU/L|pg/dL|fL|10\^3/\u03bcL|\u00b5g/dL|mmHg|kg/m\^2)'
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            value = _safe_float(match.group(1))
            unit = match.group(2)
            low, high = _parse_range_from_text(text[max(0, match.start()-80):match.end()+80])
            return {
                'name': name,
                'value': value,
                'unit': unit,
                'reference_low': low,
                'reference_high': high,
                'status': _status_for_value(value, low, high),
            }
    return None


def extract_biomarker_values(text: str, report_date: str | None = None):
    biomarker_names = [
        'Hemoglobin', 'RBC', 'WBC', 'Platelets', 'Fasting Blood Sugar', 'Post Prandial Blood Sugar', 'HbA1c',
        'Total Cholesterol', 'LDL', 'HDL', 'Triglycerides', 'Creatinine', 'Urea', 'SGPT', 'ALT', 'SGOT', 'AST',
        'Vitamin D', 'Vitamin B12', 'TSH', 'T3', 'T4', 'Blood Pressure', 'BMI'
    ]
    extracted = []
    for name in biomarker_names:
        result = _extract_biomarker_value(name, text)
        if result:
            result['report_date'] = report_date or utc_now()
            extracted.append(result)
    return extracted


def get_report_by_file_hash(file_hash: str):
    conn = get_connection()
    try:
        row = conn.execute(
            'SELECT * FROM reports WHERE file_hash = ? ORDER BY upload_date DESC LIMIT 1',
            (file_hash,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def create_or_update_patient(patient_id: str, patient_name: str | None = None, age: int | None = None, sex: str | None = None, doctor: str | None = None):
    conn = get_connection()
    try:
        existing = conn.execute('SELECT * FROM patients WHERE patient_id = ?', (patient_id,)).fetchone()
        if existing:
            conn.execute(
                'UPDATE patients SET patient_name = COALESCE(?, patient_name), age = COALESCE(?, age), sex = COALESCE(?, sex), doctor = COALESCE(?, doctor) WHERE patient_id = ?',
                (patient_name, age, sex, doctor, patient_id),
            )
        else:
            conn.execute(
                'INSERT INTO patients(patient_id, patient_name, age, sex, doctor, created_at) VALUES (?, ?, ?, ?, ?, ?)',
                (patient_id, patient_name, age, sex, doctor, utc_now()),
            )
        conn.commit()
    finally:
        conn.close()


def persist_report(file_bytes: bytes, filename: str, extracted_text: str, patient_context: dict | None = None):
    init_db()
    file_hash = file_hash_bytes(file_bytes)
    existing = get_report_by_file_hash(file_hash)
    if existing:
        return {
            'success': True,
            'document_already_exists': True,
            'report_id': existing['report_id'],
            'patient_id': existing['patient_id'],
            'message': 'A matching report was already stored. Duplicate upload prevented.',
        }

    patient_name = (patient_context or {}).get('patient_name')
    age = (patient_context or {}).get('age')
    sex = (patient_context or {}).get('sex')
    doctor = (patient_context or {}).get('doctor')
    patient_id = (patient_context or {}).get('patient_id') or patient_id_from_meta(patient_name, age, sex)
    create_or_update_patient(patient_id, patient_name, age, sex, doctor)

    report_date = (patient_context or {}).get('report_date') or datetime.now().strftime('%Y-%m-%d')
    report_id = sha256(f'{patient_id}:{file_hash}:{report_date}'.encode('utf-8')).hexdigest()[:24]

    conn = get_connection()
    try:
        conn.execute(
            '''
            INSERT INTO reports(report_id, patient_id, file_hash, source_filename, upload_date, report_date, patient_name, age, sex, doctor, original_metadata, raw_text)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''',
            (
                report_id,
                patient_id,
                file_hash,
                filename,
                utc_now(),
                report_date,
                patient_name,
                age,
                sex,
                doctor,
                json.dumps({
                    'source_filename': filename,
                    'report_date': report_date,
                    'patient_name': patient_name,
                    'age': age,
                    'sex': sex,
                    'doctor': doctor,
                }),
                extracted_text,
            ),
        )

        biomarker_values = extract_biomarker_values(extracted_text, report_date)
        for biomarker in biomarker_values:
            conn.execute(
                '''
                INSERT INTO biomarker_results(report_id, patient_id, biomarker_name, value, unit, reference_low, reference_high, status, report_date, source_text)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''',
                (
                    report_id,
                    patient_id,
                    biomarker['name'],
                    biomarker.get('value'),
                    biomarker.get('unit'),
                    biomarker.get('reference_low'),
                    biomarker.get('reference_high'),
                    biomarker.get('status', 'unknown'),
                    biomarker.get('report_date'),
                    json.dumps(biomarker),
                ),
            )
        conn.commit()
    finally:
        conn.close()

    return {
        'success': True,
        'document_already_exists': False,
        'report_id': report_id,
        'patient_id': patient_id,
        'biomarkers': len(biomarker_values),
        'message': 'Medical report analyzed and stored.',
    }


def list_reports():
    conn = get_connection()
    try:
        rows = conn.execute('SELECT * FROM reports ORDER BY upload_date DESC').fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_report(report_id: str):
    conn = get_connection()
    try:
        row = conn.execute('SELECT * FROM reports WHERE report_id = ?', (report_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_patient_reports(patient_id: str):
    conn = get_connection()
    try:
        rows = conn.execute('SELECT * FROM reports WHERE patient_id = ? ORDER BY report_date DESC, upload_date DESC', (patient_id,)).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_patient_history(patient_id: str):
    reports = get_patient_reports(patient_id)
    biomarkers = []
    conn = get_connection()
    try:
        rows = conn.execute(
            'SELECT * FROM biomarker_results WHERE patient_id = ? ORDER BY report_date DESC',
            (patient_id,),
        ).fetchall()
        biomarkers = [dict(row) for row in rows]
    finally:
        conn.close()
    return {'reports': reports, 'biomarkers': biomarkers}


def get_biomarker_history(patient_id: str, biomarker_name: str):
    conn = get_connection()
    try:
        rows = conn.execute(
            '''
            SELECT * FROM biomarker_results WHERE patient_id = ? AND biomarker_name = ? ORDER BY report_date ASC
            ''',
            (patient_id, biomarker_name),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_recent_biomarker_status(patient_id: str):
    conn = get_connection()
    try:
        rows = conn.execute(
            '''
            SELECT biomarker_name, value, unit, reference_low, reference_high, status, report_date
            FROM biomarker_results
            WHERE patient_id = ?
            ORDER BY report_date DESC, id DESC
            ''',
            (patient_id,),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


init_db()
