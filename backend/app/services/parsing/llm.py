"""Claude LLM/vision fallback for invoices rules can't handle (scanned PDFs, odd layouts).

Sends the PDF straight to Claude (which can read text PDFs and scanned/image PDFs) and asks for the
structured invoice JSON. Only used when ANTHROPIC_API_KEY is configured; otherwise the orchestrator
skips it. Default model is Sonnet (capable + cost-effective for extraction).
"""
from __future__ import annotations

import base64
import json

from app.config import settings
from app.schemas import ParsedInvoice

LLM_MODEL = "claude-sonnet-4-6"

_PROMPT = """You are extracting data from a contractor invoice PDF for accounts payable.
Return ONLY a JSON object (no prose) with these exact keys:
- vendor_name: the supplier/vendor being paid (string or null)
- invoice_number: string or null
- date_received: the invoice date in YYYY-MM-DD (string or null)
- payment_period: the service/billing period as written (string or null)
- total_invoice_cost: number (no currency symbols) or null
- line_items: array of objects, one PER CONTRACTOR/RESOURCE/EMPLOYEE, each:
    { "contractor_name": string, "hours": number|null, "rate": number|null, "amount": number|null }
Rules:
- Numbers must be plain numbers (e.g. 15936.00, not "1 5,936.00" or "$15,936").
- If the invoice has a single fixed fee with one person, still produce one line item.
- If a field is genuinely absent, use null. Do not invent values.
"""


def is_available() -> bool:
    return bool(settings.ANTHROPIC_API_KEY)


def parse_with_llm(pdf_path: str) -> ParsedInvoice:
    """Raises if no API key is configured or the SDK call fails."""
    if not is_available():
        raise RuntimeError("ANTHROPIC_API_KEY not set; LLM parsing unavailable.")

    import anthropic  # imported lazily so the app runs without the key/SDK path

    with open(pdf_path, "rb") as f:
        pdf_b64 = base64.standard_b64encode(f.read()).decode("utf-8")

    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    msg = client.messages.create(
        model=LLM_MODEL,
        max_tokens=4096,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "document",
                        "source": {"type": "base64", "media_type": "application/pdf", "data": pdf_b64},
                    },
                    {"type": "text", "text": _PROMPT},
                ],
            }
        ],
    )
    raw = "".join(block.text for block in msg.content if getattr(block, "type", None) == "text")
    data = _extract_json(raw)
    return ParsedInvoice.model_validate(data)


def _extract_json(raw: str) -> dict:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        raw = raw[raw.find("{") :]
    start, end = raw.find("{"), raw.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"LLM did not return JSON: {raw[:200]}")
    return json.loads(raw[start : end + 1])
