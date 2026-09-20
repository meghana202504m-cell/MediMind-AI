from rag.image_reader import extract_text_from_scanned_pdf
from rag.text_cleaner import clean_ocr_text
from rag.report_parser import structure_report
from rag.chunker import chunk_text
from rag.embedder import create_embeddings
from rag.vector_store import document_id_from_file, store_chunks
from rag.retriever import retrieve_chunks
from rag.context_builder import build_context
from rag.llm import generate_answer


# -----------------------------------
# Medical report
# -----------------------------------

pdf_path = "data/reports/blood_report.pdf"


# -----------------------------------
# 1. OCR
# -----------------------------------

raw_text = extract_text_from_scanned_pdf(
    pdf_path
)

cleaned_text = clean_ocr_text(
    raw_text
)

structured_text = structure_report(cleaned_text)
chunks = chunk_text(
    structured_text
)

print("==============================")
print("CHUNKS")
print("==============================\n")
for i, chunk in enumerate(chunks, 1):
    print(f"CHUNK {i}")
    print("------------------------------")
    print(chunk)
    print()

all_chunks = "\n".join(chunks)
fasting_present = all(value.lower() in all_chunks.lower() for value in ["FASTING BLOOD SUGAR", "103", "70", "110"])
post_prandial_present = all(value.lower() in all_chunks.lower() for value in ["POST PRANDIAL BLOOD SUGAR", "136", "80", "150"])
patient_info_present = all(value.lower() in structured_text.lower() for value in ["S SUDHAMANI", "52 Yrs / Female", "26060119"])

embeddings = create_embeddings(
    chunks
)

count = store_chunks(
    chunks,
    embeddings,
    document_id=document_id_from_file(pdf_path),
    filename=pdf_path
)

def documents_for(question):
    return retrieve_chunks(question, top_k=3)["documents"][0]

fasting_documents = documents_for("What is the fasting blood sugar?")
post_prandial_documents = documents_for("What is the post prandial blood sugar?")
cholesterol_documents = documents_for("What is the cholesterol level?")

fasting_retrieved = all(value.lower() in "\n".join(fasting_documents).lower() for value in ["FASTING BLOOD SUGAR", "103"])
post_prandial_retrieved = all(value.lower() in "\n".join(post_prandial_documents).lower() for value in ["POST PRANDIAL BLOOD SUGAR", "136"])
cholesterol_absent = "cholesterol" not in "\n".join(cholesterol_documents).lower()

fasting_context = build_context(fasting_documents)
post_prandial_context = build_context(post_prandial_documents)
cholesterol_context = build_context(cholesterol_documents)

fasting_answer = generate_answer(fasting_context, "What is the fasting blood sugar?")
post_prandial_answer = generate_answer(post_prandial_context, "What is the post prandial blood sugar?")
cholesterol_answer = generate_answer(cholesterol_context, "What is the cholesterol level?")

fasting_answer_ok = "103 mg/dL" in fasting_answer and fasting_answer.strip() != "103"
post_prandial_answer_ok = "136 mg/dL" in post_prandial_answer and post_prandial_answer.strip() != "136"
grounding_answer_ok = "could not find" in cholesterol_answer.lower()

print("MEDIMIND AI PIPELINE TEST")
print("=========================\n")
print("1. PDF loading: PASS")
print("2. OCR extraction: PASS" if raw_text.strip() else "2. OCR extraction: FAIL")
print("3. Text cleaning: PASS" if cleaned_text.strip() else "3. Text cleaning: FAIL")
print("4. Generic report parsing: PASS" if structured_text.strip() and patient_info_present else "4. Generic report parsing: FAIL")
print("5. Chunking: PASS" if chunks and fasting_present and post_prandial_present else "5. Chunking: FAIL")
print("6. Fasting blood sugar retrieval: PASS" if fasting_retrieved else "6. Fasting blood sugar retrieval: FAIL")
print("7. Post-prandial blood sugar retrieval: PASS" if post_prandial_retrieved else "7. Post-prandial blood sugar retrieval: FAIL")
print("8. Context construction: PASS" if fasting_context and post_prandial_context else "8. Context construction: FAIL")
print("9. Gemma answer generation: PASS" if fasting_answer_ok and post_prandial_answer_ok else "9. Gemma answer generation: FAIL")
print("10. Grounding/no-hallucination test: PASS" if cholesterol_absent and grounding_answer_ok else "10. Grounding/no-hallucination test: FAIL")
print(f"\nNumber of chunks:\n{len(chunks)}")
print(f"\nFasting blood sugar retrieved:\n{'yes' if fasting_retrieved else 'no'}")
print(f"\nPost-prandial blood sugar retrieved:\n{'yes' if post_prandial_retrieved else 'no'}")
print(f"\nGenerated answer:\n{fasting_answer}\n\n{post_prandial_answer}")
print(f"\nCholesterol grounding answer:\n{cholesterol_answer}")
print("\nIssues found:")
checks = [fasting_present, post_prandial_present, patient_info_present, fasting_retrieved, post_prandial_retrieved, fasting_answer_ok, post_prandial_answer_ok, cholesterol_absent, grounding_answer_ok]
print("None" if all(checks) else "One or more checks failed; see the individual statuses above.")
print(f"\nTotal documents in ChromaDB: {count}")