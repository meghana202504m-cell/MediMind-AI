from rag.image_reader import extract_text_from_scanned_pdf
from rag.chunker import chunk_text


pdf_path = "E:/projects/MediMind-AI/data/reports/blood_report.pdf"


# Step 1: Extract text
text = extract_text_from_scanned_pdf(pdf_path)

print("\n========== EXTRACTED TEXT ==========\n")
print(text)


# Step 2: Chunk extracted text
chunks = chunk_text(text)

print("\n========== CHUNKS ==========\n")

for i, chunk in enumerate(chunks, 1):

    print(f"\n--- Chunk {i} ---")
    print(chunk)