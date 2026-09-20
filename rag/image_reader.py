import easyocr
import pymupdf
import os
from PIL import Image


# -----------------------------------
# Load EasyOCR only once
# -----------------------------------

_reader = None


def get_reader():

    global _reader

    if _reader is None:

        _reader = easyocr.Reader(
            ['en'],
            gpu=False
        )

    return _reader


# -----------------------------------
# OCR Image
# -----------------------------------

def extract_text_from_image(image_path):

    reader = get_reader()

    results = reader.readtext(
        image_path,
        detail=1,
        paragraph=False
    )

    extracted_lines = []

    for result in results:

        if len(result) >= 3:

            text = result[1]
            confidence = result[2]

            # Keep reasonably confident results
            if confidence >= 0.20:

                extracted_lines.append(
                    text.strip()
                )

    return "\n".join(extracted_lines)


# -----------------------------------
# OCR Scanned PDF
# -----------------------------------

def extract_text_from_scanned_pdf(pdf_path):

    document = pymupdf.open(pdf_path)

    full_text = ""

    temp_folder = "data/temp_images"

    os.makedirs(
        temp_folder,
        exist_ok=True
    )


    for page_number in range(
        len(document)
    ):

        page = document.load_page(
            page_number
        )


        # -----------------------------------
        # Render PDF at high resolution
        # -----------------------------------

        matrix = pymupdf.Matrix(
            3,
            3
        )

        pix = page.get_pixmap(
            matrix=matrix,
            alpha=False
        )


        original_path = os.path.join(
            temp_folder,
            f"original_page_{page_number + 1}.png"
        )

        pix.save(
            original_path
        )


        # -----------------------------------
        # Open image
        # -----------------------------------

        image = Image.open(
            original_path
        )


        # -----------------------------------
        # IMPORTANT:
        # Rotate 90 degrees CLOCKWISE
        # -----------------------------------

        rotated_image = image.rotate(
            90,
            expand=True
        )


        rotated_path = os.path.join(
            temp_folder,
            f"rotated_page_{page_number + 1}.png"
        )


        rotated_image.save(
            rotated_path
        )


        # -----------------------------------
        # OCR
        # -----------------------------------

        page_text = extract_text_from_image(
            rotated_path
        )


        if page_text.strip():

            full_text += (
                f"\n--- Page {page_number + 1} ---\n"
            )

            full_text += page_text


    document.close()

    return full_text.strip()