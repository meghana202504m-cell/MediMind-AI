from rag.image_reader import extract_text_from_scanned_pdf


pdf_path = "data/reports/blood_report.pdf"


print("Starting OCR...")
print("Please wait...")


text = extract_text_from_scanned_pdf(pdf_path)


print("\n==============================")
print("OCR RESULT")
print("==============================\n")

print(text)


print("\n==============================")
print("TEXT LENGTH:", len(text))
print("==============================")