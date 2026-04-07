from __future__ import annotations

import io
from typing import List, Tuple


def _decode_text(data: bytes) -> str:
    try:
        return data.decode("utf-8", errors="ignore")
    except Exception:
        return data.decode("latin-1", errors="ignore")


def extract_text_from_upload(filename: str, data: bytes) -> Tuple[str, List[str]]:
    """
    Extract plain text from uploaded file bytes.

    Supported:
      - .txt/.md/.csv/.tsv: best-effort decode
      - .pdf: text extraction via `pypdf` if installed (otherwise returns "" + warning)

    Returns: (text, warnings)
    """
    warnings: List[str] = []
    name = (filename or "").lower()

    if name.endswith((".txt", ".md", ".csv", ".tsv")):
        return _decode_text(data), warnings

    if name.endswith(".pdf"):
        try:
            import pypdf  # type: ignore
        except Exception:
            warnings.append(
                "PDF extraction requires `pypdf` (install in backend env to enable)."
            )
            return "", warnings

        try:
            reader = pypdf.PdfReader(io.BytesIO(data))
            text = "\n\n".join((p.extract_text() or "") for p in reader.pages)
            if not (text or "").strip():
                warnings.append("PDF extracted no text (scanned image PDF or unsupported).")
            return text, warnings
        except Exception as e:
            warnings.append(f"PDF extraction failed: {e}")
            return "", warnings

    # Fallback: best-effort decode (may be garbage for binary docs)
    warnings.append(
        "Unsupported file type; attempted best-effort text decode (may be incomplete)."
    )
    return _decode_text(data), warnings

