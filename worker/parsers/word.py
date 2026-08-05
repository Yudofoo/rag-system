from docx import Document

def parse_word(filepath: str, filename: str) -> list[dict]:
    """Wordを見出し単位でチャンク化"""
    doc = Document(filepath)
    chunks = []
    current_section = ""
    current_lines = []

    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            continue
        if para.style.name.startswith("Heading"):
            if current_lines:
                chunks.append(_make_chunk(filename, current_section, current_lines))
                current_lines = []
            current_section = text
        else:
            current_lines.append(text)

    if current_lines:
        chunks.append(_make_chunk(filename, current_section, current_lines))

    return chunks

def _make_chunk(filename, section, lines):
    return {
        "filename": filename,
        "page": None,
        "section": section,
        "text": "\n".join(lines),
    }
