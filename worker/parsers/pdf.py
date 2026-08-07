import fitz  # pymupdf

def parse_pdf(filepath: str, filename: str) -> list[dict]:
    """PDFをページ・見出し単位でチャンク化。表はMarkdown化して個別チャンクにする"""
    doc = fitz.open(filepath)
    chunks = []

    for page_num, page in enumerate(doc, start=1):
        tables = page.find_tables()
        table_bboxes = [fitz.Rect(t.bbox) for t in tables.tables]

        blocks = page.get_text("dict")["blocks"]
        current_section = ""
        current_text = []

        for block in blocks:
            if block["type"] != 0:  # テキストブロックのみ
                continue
            # 表領域と重なるブロックは、表側でMarkdown化するのでここではスキップ（重複防止）
            block_rect = fitz.Rect(block["bbox"])
            if any(block_rect.intersects(tb) for tb in table_bboxes):
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

        for table in tables.tables:
            markdown = _table_to_markdown(table.extract())
            if markdown:
                chunks.append(_make_chunk(filename, page_num, current_section, [markdown]))

    doc.close()
    return chunks

def _table_to_markdown(rows: list[list]) -> str:
    """表の行データ（None含む）をMarkdownテーブル文字列に変換"""
    cleaned = [
        [("" if cell is None else str(cell).strip()) for cell in row]
        for row in rows
        if row
    ]
    if not cleaned:
        return ""

    header, *body = cleaned
    lines = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join("---" for _ in header) + " |",
    ]
    for row in body:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)

def _make_chunk(filename, page, section, lines):
    return {
        "filename": filename,
        "page": page,
        "section": section,
        "text": "\n".join(lines),
    }
