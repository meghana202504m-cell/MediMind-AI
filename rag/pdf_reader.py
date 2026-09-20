from pypdf import PdfReader

def read_pdf(file_path):
    """
    Reads a PDF file and returns all the extracted text.
    """

    reader = PdfReader(file_path)

    text = ""

    for page in reader.pages:
        extracted = page.extract_text()

        if extracted:
            text += extracted + "\n"

    return text