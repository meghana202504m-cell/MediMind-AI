from rag.image_reader import extract_text_from_scanned_pdf
from rag.text_cleaner import clean_ocr_text
from rag.report_parser import structure_report
from rag.chunker import chunk_text
from rag.embedder import create_embeddings


pdf_path = "data/reports/blood_report.pdf"


print("Preparing report...")

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


print("\nCreating embeddings...")

embeddings = create_embeddings(
    chunks
)


print("\n==============================")
print("EMBEDDING TEST")
print("==============================")

print("Chunks:", len(chunks))

print("Embeddings:", len(embeddings))

print(
    "Embedding dimensions:",
    len(embeddings[0])
)