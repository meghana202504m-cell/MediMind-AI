from rag.report_parser import structure_report
from rag.chunker import chunk_text


def test_structure_report_preserves_unknown_sections_and_ranges():
    report = """PATIENT NAME: Jane Doe
FASTING BLOOD SUGAR
Result: 95 mg/dL
Reference Range: 70-100 mg/dL
POST PRANDIAL BLOOD SUGAR
Result: 130 mg/dL
Reference Range: 80-140 mg/dL
"""

    structured = structure_report(report)

    assert "FASTING BLOOD SUGAR" in structured
    assert "POST PRANDIAL BLOOD SUGAR" in structured
    assert "Reference Range" in structured
    assert "95 mg/dL" in structured
    assert "130 mg/dL" in structured


def test_chunk_text_is_document_type_independent():
    text = """CLINICAL CHEMISTRY
TOTAL LEUKOCYTE COUNT
Value: 7.2 x10^3/uL
Reference Range: 4.0-11.0 x10^3/uL
URINE ANALYSIS
Colour: Yellow
Appearance: Clear
"""

    chunks = chunk_text(text)

    assert chunks
    joined = "\n\n".join(chunks)
    assert "TOTAL LEUKOCYTE COUNT" in joined
    assert "URINE ANALYSIS" in joined
    assert "Reference Range" in joined
