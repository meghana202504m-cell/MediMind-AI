import re


def clean_ocr_text(text):
    """
    Clean OCR output before chunking.
    """

    # Remove excessive spaces
    text = re.sub(
        r"[ \t]+",
        " ",
        text
    )

    # Remove excessive blank lines
    text = re.sub(
        r"\n{2,}",
        "\n",
        text
    )

    # Fix common OCR mistakes
    replacements = {
        "mgldl": "mg/dL",
        "mg/dl": "mg/dL",
        "AGESEX": "AGE/SEX",
        "REFeRREd": "REFERRED",
        "REGILAB": "REG LAB",
        "DIAGNOSTIC CENTR": "DIAGNOSTIC CENTRE"
    }

    for old, new in replacements.items():

        text = text.replace(
            old,
            new
        )

    return text.strip()