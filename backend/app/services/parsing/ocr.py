"""OCR fallback for scanned (image-only) PDFs using RapidOCR (offline, no LLM, no system binary).

Renders each page to an image with pypdfium2, then runs RapidOCR to recover text. The recovered text
is fed back through the same header/line parsers.
"""
from __future__ import annotations

import functools


def is_available() -> bool:
    try:
        import pypdfium2  # noqa: F401
        import rapidocr_onnxruntime  # noqa: F401
        return True
    except Exception:
        return False


@functools.lru_cache(maxsize=1)
def _engine():
    from rapidocr_onnxruntime import RapidOCR

    return RapidOCR()


def ocr_pdf(pdf_path: str, scale: float = 2.5) -> str:
    """Return text recovered from a scanned PDF, line by line, top-to-bottom per page."""
    import numpy as np
    import pypdfium2 as pdfium

    engine = _engine()
    out: list[str] = []
    pdf = pdfium.PdfDocument(pdf_path)
    try:
        for page in pdf:
            bitmap = page.render(scale=scale)
            image = bitmap.to_pil().convert("RGB")
            result, _ = engine(np.array(image))
            if result:
                # result: list of [box, text, score]; keep document order.
                out.extend(item[1] for item in result)
            page.close()
    finally:
        pdf.close()
    return "\n".join(out)
