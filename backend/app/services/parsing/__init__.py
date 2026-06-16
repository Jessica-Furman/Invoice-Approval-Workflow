"""Hybrid invoice parsing (M3): pdfplumber rules first, optional Claude LLM/vision fallback."""
from app.services.parsing.parser import ParseOutcome, parse_invoice

__all__ = ["ParseOutcome", "parse_invoice"]
