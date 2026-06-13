"""
auth_module/sanitizer.py
------------------------
Sensitive-data scrubber for user-uploaded documents.

Detects and redacts the following categories before content is embedded
into the knowledge base:

  1. API keys & tokens  — provider-specific prefixes and generic high-entropy secrets
  2. Credentials        — passwords, private keys, connection strings
  3. Pricing & costs    — monetary amounts, rate cards, billing lines
  4. PII               — email addresses, phone numbers, national ID patterns
  5. Client data        — explicit "Client: …" / "Customer: …" labelled lines

Each match is replaced with a [REDACTED:<category>] placeholder so the
surrounding context is preserved for chunking without leaking secrets.

Usage
-----
    from auth_module.sanitizer import sanitize, SanitizationReport

    clean_text, report = sanitize(raw_markdown)
    if report.total > 0:
        print(f"Redacted {report.total} sensitive items")
"""

import re
from dataclasses import dataclass, field
from typing import List, Tuple

# ---------------------------------------------------------------------------
# Patterns
# Each tuple: (category_label, compiled_regex)
# Ordering matters — more specific patterns first.
# ---------------------------------------------------------------------------

_PATTERNS: List[Tuple[str, re.Pattern]] = [
    # ── 1. Provider-specific API keys ──────────────────────────────────────
    # OpenAI
    ("API_KEY", re.compile(r"\bsk-(?:proj-|ant-)?[A-Za-z0-9_\-]{20,}", re.IGNORECASE)),
    # AWS access key IDs
    ("API_KEY", re.compile(r"\b(?:AKIA|AIPA|AROA|ASCA|ASIA)[A-Z0-9]{16}\b")),
    # AWS secret access keys (40-char base64)
    ("API_KEY", re.compile(r"(?i)aws[_\-\s]?secret[_\-\s]?(?:access[_\-\s]?)?key\s*[:=]\s*[A-Za-z0-9/+]{40}")),
    # Google API keys
    ("API_KEY", re.compile(r"\bAIza[0-9A-Za-z_\-]{35}\b")),
    # GitHub tokens
    ("API_KEY", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b")),
    # Stripe secret keys
    ("API_KEY", re.compile(r"\bsk_(?:live|test)_[A-Za-z0-9]{24,}\b")),
    # Sendgrid
    ("API_KEY", re.compile(r"\bSG\.[A-Za-z0-9_\-]{22,}\.[A-Za-z0-9_\-]{43,}\b")),
    # Twilio
    ("API_KEY", re.compile(r"\bAC[a-f0-9]{32}\b")),
    # Generic bearer tokens in headers/docs
    ("TOKEN", re.compile(r"(?i)(?:Bearer|Authorization)\s*[:=]\s*[A-Za-z0-9\-_.~+/]{20,}")),
    # JWT tokens (three base64url segments)
    ("TOKEN", re.compile(r"eyJ[A-Za-z0-9_\-]+\.eyJ[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+")),

    # ── 2. Key=value / labeled secrets ────────────────────────────────────
    ("SECRET", re.compile(
        r"(?i)(?:api[_\-]?key|api[_\-]?token|secret[_\-]?key|private[_\-]?key|"
        r"access[_\-]?token|auth[_\-]?token|client[_\-]?secret|app[_\-]?secret|"
        r"webhook[_\-]?secret|signing[_\-]?key|encryption[_\-]?key)\s*[:=]\s*\S{8,}"
    )),
    ("PASSWORD", re.compile(
        r"(?i)(?:password|passwd|pwd|passphrase)\s*[:=]\s*\S{4,}"
    )),
    # Connection strings / DSNs
    ("CREDENTIAL", re.compile(
        r"(?i)(?:mysql|postgresql|postgres|mongodb|redis|amqp|mongodb\+srv)"
        r"://[^:\s]+:[^@\s]+@[^\s]+"
    )),
    # PEM private keys
    ("PRIVATE_KEY", re.compile(
        r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----.*?-----END (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----",
        re.DOTALL,
    )),
    # High-entropy hex secrets with labeled context (avoids false positives on hashes/UUIDs)
    ("SECRET", re.compile(
        r"(?i)(?:hmac|digest|checksum|signing[_\-]?key|encryption[_\-]?key|hash)\s*[:=]\s*[0-9a-fA-F]{32,64}\b"
    )),

    # ── 3. Pricing & financial data ────────────────────────────────────────
    # Labeled pricing lines (require explicit context to avoid matching "$1" in general text)
    ("PRICING", re.compile(
        r"(?i)(?:price|pricing|cost|rate|fee|charge|tariff|subscription|plan\s+(?:cost|price))"
        r"\s*[:=]\s*.{1,80}",
    )),
    # Currency amounts only when followed by a per-unit suffix ($/mo, $/user, etc.)
    ("PRICING", re.compile(
        r"(?:USD|EUR|GBP|INR|CAD|AUD|JPY)?\s*"
        r"(?:\$|€|£|¥|₹)\s*\d[\d,]*(?:\.\d{1,2})?\s*"
        r"/\s*(?:mo(?:nth)?|yr|year|user|seat|req(?:uest)?|call|day)"
    )),
    # Discount / promo codes
    ("PRICING", re.compile(r"(?i)(?:promo|discount|coupon)\s*(?:code)?\s*[:=]\s*\S+")),

    # ── 4. PII ─────────────────────────────────────────────────────────────
    # Email addresses
    ("PII_EMAIL", re.compile(r"\b[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}\b")),
    # Phone numbers — international and common national formats
    ("PII_PHONE", re.compile(
        r"(?<!\d)"
        r"(?:\+?1[-.\s]?)?"                    # optional US country code
        r"(?:\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}"  # (NXX) NXX-XXXX
        r"|\+\d{1,3}[-.\s]\d{1,4}[-.\s]\d{2,4}[-.\s]\d{2,9})"  # intl
        r"(?!\d)"
    )),
    # US Social Security numbers
    ("PII_SSN", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
    # Credit card numbers (Luhn not verified, pattern-only)
    ("PII_CARD", re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b")),

    # ── 5. Client / customer identifiers ───────────────────────────────────
    # Explicit labelled lines: "Client: Acme Corp", "Customer ID: 12345"
    ("CLIENT_INFO", re.compile(
        r"(?im)^(?:client|customer|account\s*holder|contact)\s*(?:name|id|company)?\s*[:=]\s*.+$"
    )),
    # Contract/invoice numbers
    ("CLIENT_INFO", re.compile(
        r"(?i)(?:contract|invoice|po|purchase\s*order)\s*(?:#|no\.?|number)?\s*[:=]?\s*[A-Z0-9\-]{4,}"
    )),
]


# ---------------------------------------------------------------------------
# Report dataclass
# ---------------------------------------------------------------------------

@dataclass
class SanitizationReport:
    redactions: List[dict] = field(default_factory=list)  # [{category, original_snippet, position}]

    @property
    def total(self) -> int:
        return len(self.redactions)

    @property
    def by_category(self) -> dict:
        counts: dict = {}
        for r in self.redactions:
            counts[r["category"]] = counts.get(r["category"], 0) + 1
        return counts

    def __str__(self) -> str:
        if not self.redactions:
            return "No sensitive data found."
        lines = [f"Redacted {self.total} items:"]
        for cat, count in sorted(self.by_category.items()):
            lines.append(f"  {cat}: {count}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def sanitize(text: str) -> Tuple[str, SanitizationReport]:
    """Scan `text` for sensitive patterns and replace each match with a
    [REDACTED:<CATEGORY>] placeholder.

    Returns
    -------
    clean_text : str
        The sanitized version of the input.
    report : SanitizationReport
        Summary of what was redacted.
    """
    report = SanitizationReport()
    result = text

    for category, pattern in _PATTERNS:
        def _replace(m: re.Match, _cat: str = category) -> str:
            snippet = m.group(0)
            # Truncate long snippets in the report
            display = snippet[:40] + "…" if len(snippet) > 40 else snippet
            report.redactions.append({
                "category": _cat,
                "original_snippet": display,
                "position": m.start(),
            })
            return f"[REDACTED:{_cat}]"

        result = pattern.sub(_replace, result)

    return result, report


def is_clean(text: str) -> bool:
    """Quick check — True if no sensitive patterns found (no redaction needed)."""
    _, report = sanitize(text)
    return report.total == 0
