"""
Document Processing Pipeline
================================
Extracts text content from various document formats:
- PDF (via PyMuPDF)
- HTML (via text extraction)
- LaTeX (basic parsing)
- Patent XML (structured extraction)

This pipeline prepares documents for the Epistemic Filter.
For complex scientific PDFs with formulas, the raw PDF is
sent directly to Claude (which handles it natively).
This module handles preprocessing and text extraction for
cases where pre-processing improves quality or reduces cost.
"""

import re
from pathlib import Path
from typing import Optional


def validate_pdf(file_path: str) -> bool:
    """Check if a file is actually a valid PDF.

    Returns True if file starts with %PDF header.
    Returns False for HTML pages, redirects, or corrupted downloads.
    """
    path = Path(file_path)
    if not path.exists():
        return False
    if path.stat().st_size < 100:
        return False
    try:
        with open(path, 'rb') as f:
            header = f.read(5)
        return header.startswith(b'%PDF')
    except Exception:
        return False


def cleanup_invalid_download(file_path: str) -> None:
    """Remove a downloaded file that turned out not to be a PDF."""
    path = Path(file_path)
    if path.exists():
        path.unlink()



def extract_pdf_text(pdf_path: str, max_pages: int = 50) -> str:
    """Extract text from a PDF using PyMuPDF.

    This is used for:
    - Pre-screening PDFs before sending to Claude (check relevance)
    - Extracting text from PDFs too large for Claude's context
    - Reducing token cost by sending text instead of base64 PDF

    For scientific papers with formulas/tables, prefer sending
    the raw PDF to Claude via epistemic_filter.extract_from_pdf().
    """
    try:
        import fitz  # PyMuPDF
    except ImportError:
        print("  PyMuPDF not installed. Run: pip install PyMuPDF")
        return ""

    try:
        doc = fitz.open(pdf_path)
        pages = min(len(doc), max_pages)
        text_parts = []

        for i in range(pages):
            page = doc[i]
            text = page.get_text("text")
            if text.strip():
                text_parts.append(f"--- Page {i+1} ---\n{text}")

        doc.close()
        return "\n\n".join(text_parts)

    except Exception as e:
        print(f"  PDF text extraction failed: {e}")
        return ""


def extract_pdf_metadata(pdf_path: str) -> dict:
    """Extract metadata from a PDF (title, author, subject, etc.)."""
    try:
        import fitz
        doc = fitz.open(pdf_path)
        meta = doc.metadata or {}
        page_count = len(doc)
        doc.close()
        return {
            "title": meta.get("title", ""),
            "author": meta.get("author", ""),
            "subject": meta.get("subject", ""),
            "creator": meta.get("creator", ""),
            "page_count": page_count,
        }
    except Exception:
        return {}


def check_pdf_relevance(pdf_path: str, keywords: list[str], min_matches: int = 2) -> tuple[bool, int]:
    """Quick relevance check — does the PDF contain enough keywords?

    Extracts text from first 5 pages and checks for keyword presence.
    Returns (is_relevant, match_count).
    """
    text = extract_pdf_text(pdf_path, max_pages=5).lower()
    matches = sum(1 for kw in keywords if kw.lower() in text)
    return matches >= min_matches, matches


def extract_html_text(html: str) -> str:
    """Extract clean text from HTML content."""
    # Remove script and style
    text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
    # Convert some tags to text markers
    text = re.sub(r"<h[1-6][^>]*>", "\n## ", text, flags=re.IGNORECASE)
    text = re.sub(r"</h[1-6]>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<p[^>]*>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<br[^>]*>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<li[^>]*>", "\n- ", text, flags=re.IGNORECASE)
    # Strip remaining tags
    text = re.sub(r"<[^>]+>", "", text)
    # Clean up
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r" {2,}", " ", text)
    # Decode entities
    text = text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    text = text.replace("&quot;", '"').replace("&#39;", "'").replace("&nbsp;", " ")
    return text.strip()


def extract_latex_text(latex_source: str) -> str:
    """Extract readable text from LaTeX source.

    Preserves math environments and section structure.
    Strips LaTeX formatting commands.
    """
    text = latex_source

    # Preserve math environments
    text = re.sub(r"\\begin\{equation\*?\}", "[EQUATION: ", text)
    text = re.sub(r"\\end\{equation\*?\}", "]", text)
    text = re.sub(r"\$\$(.*?)\$\$", r"[MATH: \1]", text, flags=re.DOTALL)
    text = re.sub(r"\$(.*?)\$", r"[MATH: \1]", text)

    # Convert sections to headers
    text = re.sub(r"\\section\{(.*?)\}", r"\n## \1\n", text)
    text = re.sub(r"\\subsection\{(.*?)\}", r"\n### \1\n", text)
    text = re.sub(r"\\subsubsection\{(.*?)\}", r"\n#### \1\n", text)

    # Strip common commands
    text = re.sub(r"\\textbf\{(.*?)\}", r"\1", text)
    text = re.sub(r"\\textit\{(.*?)\}", r"\1", text)
    text = re.sub(r"\\emph\{(.*?)\}", r"\1", text)
    text = re.sub(r"\\cite\{(.*?)\}", r"[ref:\1]", text)
    text = re.sub(r"\\ref\{(.*?)\}", r"[ref:\1]", text)
    text = re.sub(r"\\label\{.*?\}", "", text)

    # Remove preamble
    begin_match = re.search(r"\\begin\{document\}", text)
    if begin_match:
        text = text[begin_match.end():]
    end_match = re.search(r"\\end\{document\}", text)
    if end_match:
        text = text[:end_match.start()]

    # Strip remaining commands
    text = re.sub(r"\\[a-zA-Z]+\{([^}]*)\}", r"\1", text)
    text = re.sub(r"\\[a-zA-Z]+", "", text)
    text = re.sub(r"[{}]", "", text)

    # Clean up
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_patent_claims(patent_text: str) -> list[str]:
    """Extract individual claims from patent text.

    Claims are numbered and typically start after a "Claims" header.
    """
    # Find claims section
    claims_match = re.search(r"(?:Claims|CLAIMS)\s*\n", patent_text, re.IGNORECASE)
    if not claims_match:
        return []

    claims_text = patent_text[claims_match.end():]

    # Split by claim numbers
    claims = re.split(r"\n\s*(\d+)\.\s+", claims_text)

    # Group number + text pairs
    result = []
    for i in range(1, len(claims), 2):
        if i + 1 < len(claims):
            claim_num = claims[i]
            claim_text = claims[i + 1].strip()
            if claim_text and len(claim_text) > 20:
                result.append(f"Claim {claim_num}: {claim_text[:500]}")

    return result[:30]  # Limit to 30 claims


def get_processor_for_file(filepath: str) -> str:
    """Determine the best processing approach for a file.

    Returns: "claude_pdf" | "text_extract" | "html" | "latex" | "unknown"
    """
    path = Path(filepath)
    ext = path.suffix.lower()

    if ext == ".pdf":
        # Check file size — large PDFs should be text-extracted first
        size_mb = path.stat().st_size / (1024 * 1024)
        if size_mb > 20:
            return "text_extract"  # Too large for Claude's context
        return "claude_pdf"  # Send directly to Claude

    elif ext in (".html", ".htm"):
        return "html"
    elif ext in (".tex", ".latex"):
        return "latex"
    elif ext in (".txt", ".md"):
        return "text_extract"
    else:
        return "unknown"
