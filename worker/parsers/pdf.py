import fitz  # pymupdf

def parse_pdf(filepath: str, filename: str) -> list[dict]:
    """PDFをページ・見出し単位でチャンク化"""
    doc = fitz.open(filepath)
    chunks = []

    for page_num, page in enumerate(doc, start=1):
        blocks = page.get_text("dict")["blocks"]
        current_section = ""
        current_text = []

        for block in blocks:
            if block["type"] != 0:  # テキストブロックのみ
                continue
            for line in block["lines"]:
                line_text = "".join(s["text"] for s in line["spans"]).strip()
                if not line_text:
                    continue
                # フォントサイズが大きい行を見出しとみなす
                font_size = line["spans"][0]["size"] if line["spans"] else 0
                if font_size >= 14:
                    if current_text:
                        chunks.append(_make_chunk(filename, page_num, current_section, current_text))
                        current_text = []
                    current_section = line_text
                else:
                    current_text.append(line_text)

        if current_text:
            chunks.append(_make_chunk(filename, page_num, current_section, current_text))

    doc.close()
    return chunks

def _make_chunk(filename, page, section, lines):
    return {
        "filename": filename,
        "page": page,
        "section": section,
        "text": "\n".join(lines),
    }
