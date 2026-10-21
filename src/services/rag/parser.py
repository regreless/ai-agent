from pathlib import Path
from pypdf import PdfReader
from docx import Document


def parse_file(path: str) -> str:
    p = Path(path)
    suffix = p.suffix.lower()
    if suffix in [".txt", ".md", ".csv", ".json"]:
        return p.read_text(encoding="utf-8", errors="ignore")
    if suffix == ".pdf":
        try:
            reader = PdfReader(str(p))
            return "\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception as exc:
            return f"PDF 解析失败：{exc}"

    if suffix in [".docx"]:
        try:
            doc = Document(str(p))
            return "\n".join(paragraph.text for paragraph in doc.paragraphs)
        except Exception as exc:
            return f"DOCX 解析失败：{exc}"
    return p.read_text(encoding="utf-8", errors="ignore")


def split_text(text: str, chunk_size: int = 600, overlap: int = 80) -> list[str]:
    clean = "\n".join(line.strip() for line in text.splitlines() if line.strip())
    if not clean:
        return []
    chunks = []
    start = 0
    while start < len(clean):
        end = min(len(clean), start + chunk_size)
        chunks.append(clean[start:end])
        if end >= len(clean):
            break
        start = max(0, end - overlap)
    return chunks
