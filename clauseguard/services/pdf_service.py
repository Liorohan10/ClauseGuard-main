import pymupdf


class PDFService:
    """Parse PDF files and plain text into raw text content."""

    def parse(self, file_bytes: bytes, filename: str) -> tuple[str, int]:
        """Parse a file into (text, num_pages). Supports PDF and plain text."""
        if filename.lower().endswith(".pdf"):
            return self._parse_pdf(file_bytes)
        return self._parse_text(file_bytes)

    def _parse_pdf(self, file_bytes: bytes) -> tuple[str, int]:
        doc = pymupdf.open(stream=file_bytes, filetype="pdf")
        pages = []
        for page in doc:
            text = page.get_text()
            if text.strip():
                pages.append(text)
        doc.close()
        full_text = "\n\n".join(pages)
        return full_text, len(pages) if pages else 1

    def _parse_text(self, file_bytes: bytes) -> tuple[str, int]:
        text = file_bytes.decode("utf-8", errors="replace")
        return text, 1
