from rag.image_reader import extract_text_from_scanned_pdf
from rag.text_cleaner import clean_ocr_text


pdf_path = "data/reports/blood_report.pdf"


print("Running OCR...")

ocr_text = extract_text_from_scanned_pdf(
    pdf_path
)


print("\n==============================")
print("RAW OCR TEXT")
print("==============================")

print(ocr_text)


cleaned_text = clean_ocr_text(
    ocr_text
)


print("\n==============================")
print("CLEANED TEXT")
print("==============================")

print(cleaned_text)