"""Guardrail layer. Runs before anything is stored, scored or displayed.

The rule from the brief is precise: if a card number is spoken, the transcript view
redacts it before anyone sees it, and the score still flags the violation. So
redaction returns BOTH the safe text and the list of what it found, because the
finding is what the compliance check consumes.
"""
import re
from dataclasses import dataclass, field

# Placeholder tags already present in the supplied transcript. Left untouched.
PLACEHOLDER_RE = re.compile(r"\[[A-Z_]+\]")

CARD_DIGITS_RE = re.compile(r"(?:\d[ -]?){13,19}")
LONG_DIGITS_RE = re.compile(r"\b\d{9,}\b")

# Spoken digits, e.g. "four one one one one one one one ..."
_DIGIT_WORDS = {
    "zero": "0", "oh": "0", "one": "1", "two": "2", "three": "3", "four": "4",
    "five": "5", "six": "6", "seven": "7", "eight": "8", "nine": "9",
}
SPOKEN_DIGIT_RUN_RE = re.compile(
    r"\b(?:(?:" + "|".join(_DIGIT_WORDS) + r")[\s,-]+){12,}(?:" + "|".join(_DIGIT_WORDS) + r")\b",
    re.IGNORECASE,
)

CARD_CONTEXT_RE = re.compile(
    r"\b(card number|credit card|debit card|cvv|ccv|security code|expiry|exp date)\b",
    re.IGNORECASE,
)


@dataclass
class RedactionReport:
    text: str
    findings: list[dict] = field(default_factory=list)

    @property
    def card_data_found(self) -> bool:
        return any(f["kind"] == "card_number" for f in self.findings)


def _luhn_ok(digits: str) -> bool:
    if not 13 <= len(digits) <= 19:
        return False
    total, parity = 0, len(digits) % 2
    for i, ch in enumerate(digits):
        d = int(ch)
        if i % 2 == parity:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


def redact(text: str) -> RedactionReport:
    """Return display-safe text plus every finding, in priority order."""
    findings: list[dict] = []
    safe = text

    def _swap(pattern: re.Pattern, token: str, kind: str, validator=None) -> None:
        nonlocal safe

        def repl(m: re.Match) -> str:
            value = m.group(0)
            if validator and not validator(value):
                return value
            findings.append({"kind": kind, "matched_length": len(value)})
            return token

        safe = pattern.sub(repl, safe)

    _swap(CARD_DIGITS_RE, "[REDACTED_CARD]", "card_number",
          validator=lambda v: _luhn_ok(re.sub(r"\D", "", v)))
    _swap(SPOKEN_DIGIT_RUN_RE, "[REDACTED_CARD]", "card_number",
          validator=lambda v: _luhn_ok("".join(
              _DIGIT_WORDS[w.lower()] for w in re.findall(r"[A-Za-z]+", v)
              if w.lower() in _DIGIT_WORDS)))
    _swap(LONG_DIGITS_RE, "[REDACTED_NUMBER]", "long_numeric")

    if CARD_CONTEXT_RE.search(text):
        findings.append({"kind": "card_context_mentioned", "matched_length": 0})

    return RedactionReport(text=safe, findings=findings)
