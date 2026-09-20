from rag.image_reader import extract_text_from_scanned_pdf
from rag.text_cleaner import clean_ocr_text
from rag.report_parser import structure_report
from rag.chunker import chunk_text


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

chunks = chunk_text(
    structured_text
)


print("\n==============================")
print("CHUNKS")
print("==============================\n")


for i, chunk in enumerate(chunks):

    print(f"CHUNK {i + 1}")
    print("------------------------------")
    print(chunk)
    print()