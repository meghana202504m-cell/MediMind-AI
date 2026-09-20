import re


def _looks_like_measurement(line):
    """Return True when a line looks like a value or observation rather than a section heading."""
    if not line:
        return False

    if ":" in line:
        return True

    if re.search(r"\d", line):
        if re.search(r"(?:mg/dL|mg/dl|g/dL|g/dl|mmol/L|mmol/l|uL|x10\^3|%|IU|mEq|ng/mL|pg/mL)", line, re.IGNORECASE):
            return True
        if re.search(r"\d\s*(?:-|to|–)\s*\d", line):
            return True

    return False


def _looks_like_section_heading(line):
    """Recognize generic report section titles without hard-coding medical test names."""
    if not line or len(line.strip()) < 3:
        return False

    stripped = line.strip()

    if _looks_like_measurement(stripped):
        return False

    if stripped.endswith(":"):
        return False

    if stripped.isupper():
        words = stripped.split()
        return len(words) >= 2

    words = re.findall(r"[A-Za-z]+", stripped)
    if len(words) < 2:
        return False

    if any(ch.isdigit() for ch in stripped):
        return False

    if any(char in stripped for char in ["/", "(", ")", "&", "-"]):
        return True

    return stripped[0].isupper() and " " in stripped


def split_report_sections(text):
    """Split OCR text into sections while preserving any unrecognized content."""
    if not text or not text.strip():
        return []

    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    sections = []
    current_section = []
    current_page_marker = None

    for line in lines:
        page_match = re.match(r"^--- Page (\d+) ---$", line, re.IGNORECASE)
        if page_match:
            if current_section:
                sections.append("\n".join(current_section))
            current_page_marker = line
            current_section = [line]
            continue

        if _looks_like_section_heading(line):
            if current_section and current_section != [current_page_marker]:
                sections.append("\n".join(current_section))
            current_section = [line]
            if current_page_marker:
                current_section.insert(0, current_page_marker)
        else:
            current_section.append(line)

    if current_section:
        sections.append("\n".join(current_section))

    return sections


def structure_report(text):
    """
    Organize OCR text into meaningful report sections without assuming a specific test.
    Preserve all extracted information, including unknown or unrecognized sections.
    """
    sections = split_report_sections(text)
    return "\n\n".join(sections) if sections else ""