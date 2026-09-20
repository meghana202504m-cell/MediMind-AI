from rag.report_parser import split_report_sections


def chunk_text(text):
    """
    Split report text into document-agnostic sections while preserving all extracted content.
    If no clear section heading is found, keep the text as one chunk.
    """
    sections = split_report_sections(text)
    return sections if sections else ([text.strip()] if text and text.strip() else [])