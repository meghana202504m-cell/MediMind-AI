from rag.image_reader import extract_text_from_scanned_pdf
from rag.text_cleaner import clean_ocr_text
from rag.report_parser import structure_report


pdf_path = "data/reports/blood_report.pdf"


print("Running OCR...")

ocr_text = extract_text_from_scanned_pdf(
    pdf_path
)


cleaned_text = clean_ocr_text(
    ocr_text
)


structured_text = structure_report(
    cleaned_text
)


print("\n==============================")
print("STRUCTURED REPORT")
print("==============================\n")

print(structured_text)