"""Spoken language -> machine-comparable values.

Everything in this module is deterministic. No model is involved, because
"forty two dollars and ninety" -> 42.90 is arithmetic, not judgement. The brief
grades critical checks on never false-passing; arithmetic is how you get there.
"""
import re

UNITS = {
    "zero": 0, "oh": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11,
    "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16,
    "seventeen": 17, "eighteen": 18, "nineteen": 19,
}
TENS = {
    "twenty": 20, "thirty": 30, "forty": 40, "fourty": 40, "fifty": 50,
    "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90,
}
SCALES = {"hundred": 100, "thousand": 1000}
NUMBER_WORDS = set(UNITS) | set(TENS) | set(SCALES) | {"and", "point", "a"}

# Common ASR manglings of "Mbps" seen in the supplied call.
SPEED_UNIT_RE = r"(?:mbps|mbbs|mbp|mb\s*p\s*s|megabits?|mb)"

_TOKEN_RE = re.compile(r"[a-z]+|\d+(?:\.\d+)?")


def tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


def words_to_number(tokens: list[str]) -> float | None:
    """Parse a run of number words/digits. Supports 'eight point five'."""
    if not tokens:
        return None

    whole, current, seen = 0, 0, False
    i = 0
    while i < len(tokens):
        t = tokens[i]
        if re.fullmatch(r"\d+(?:\.\d+)?", t):
            current += float(t)
            seen = True
        elif t in UNITS:
            current += UNITS[t]
            seen = True
        elif t in TENS:
            current += TENS[t]
            seen = True
        elif t == "hundred":
            current = (current or 1) * 100
            seen = True
        elif t == "thousand":
            whole += (current or 1) * 1000
            current = 0
            seen = True
        elif t == "point":
            frac_tokens = tokens[i + 1:]
            digits = ""
            for ft in frac_tokens:
                if re.fullmatch(r"\d+", ft):
                    digits += ft
                elif ft in UNITS and UNITS[ft] < 10:
                    digits += str(UNITS[ft])
                else:
                    break
            if digits:
                return (whole + current) + float(f"0.{digits}")
            break
        elif t in ("and", "a"):
            pass
        else:
            break
        i += 1

    return float(whole + current) if seen else None


_SPLITTABLE = sorted(
    (w for w in (set(UNITS) | set(TENS) | set(SCALES)) if len(w) >= 3),
    key=len, reverse=True,
)


def _deglue(token: str) -> list[str]:
    """Split a run-together token that begins with a number word.

    The source contains "forty two dollars and ninetyMhmm" - the cents are welded to
    the next speaker's interjection. Without this, the amount silently parses as
    $42.00 instead of $42.90, which is exactly the kind of quiet wrong answer a
    critical check must never produce.
    """
    if token in NUMBER_WORDS or re.fullmatch(r"\d+(?:\.\d+)?", token):
        return [token]
    for word in _SPLITTABLE:
        if token.startswith(word) and len(token) - len(word) >= 2:
            return [word, *_deglue(token[len(word):])]
    return [token]


def tokens_with_pos(text: str) -> list[tuple[str, int]]:
    out: list[tuple[str, int]] = []
    for m in _TOKEN_RE.finditer(text.lower()):
        for piece in _deglue(m.group(0)):
            out.append((piece, m.start()))
    return out


def _is_number_token(tok: str) -> bool:
    return (tok in UNITS or tok in TENS or tok in SCALES
            or bool(re.fullmatch(r"\d+(?:\.\d+)?", tok)))


def _walk_back(tokens: list[tuple[str, int]], i: int) -> tuple[float | None, int]:
    """Collect the number-word run ending just before index i.

    Walking backwards from the unit word is what makes 'Sixty five dollars for how
    many MBPS' parse as 65 dollars and not as 5, and 'eight point five Mbps' as 8.5.
    """
    j = i - 1
    while j >= 0 and (_is_number_token(tokens[j][0])
                      or tokens[j][0] in ("and", "point", "a")):
        j -= 1
    run = [t for t, _ in tokens[j + 1:i]]
    while run and run[0] in ("and", "a"):
        run.pop(0)
    while run and run[-1] in ("and", "a", "point"):
        run.pop()
    if not run:
        return None, i
    return words_to_number(run), (i - len(run))


def _walk_forward(tokens: list[tuple[str, int]], i: int) -> float | None:
    """Parse the number run starting at index i, used for the cents after 'and'."""
    j = i
    while j < len(tokens) and (_is_number_token(tokens[j][0]) or tokens[j][0] == "point"):
        j += 1
    return words_to_number([t for t, _ in tokens[i:j]]) if j > i else None


def find_money(text: str) -> list[tuple[float, int]]:
    """Return [(amount, char_position)] for every money mention.

    Handles '$42.90', 'forty two dollars and ninety' (= 42.90),
    'three hundred seventeen dollars', 'two hundred seventy five dollars'.
    """
    out: list[tuple[float, int]] = []
    lowered = text.lower()

    for m in re.finditer(r"\$\s*(\d+(?:\.\d{1,2})?)", lowered):
        out.append((float(m.group(1)), m.start()))

    tokens = tokens_with_pos(text)
    for i, (tok, _pos) in enumerate(tokens):
        if tok not in ("dollar", "dollars"):
            continue
        dollars, run_start = _walk_back(tokens, i)
        if dollars is None:
            continue
        amount = dollars
        if i + 2 < len(tokens) and tokens[i + 1][0] == "and":
            cents = _walk_forward(tokens, i + 2)
            if cents is not None and 0 < cents < 100:
                # "forty two dollars and ninety" -> 42.90, never 42 + 90
                amount = round(dollars + cents / 100.0, 2)
        out.append((round(amount, 2), tokens[run_start][1]))

    deduped: list[tuple[float, int]] = []
    for amount, pos in sorted(out, key=lambda x: x[1]):
        if deduped and abs(deduped[-1][1] - pos) < 4 and deduped[-1][0] == amount:
            continue
        deduped.append((amount, pos))
    return deduped


SPEED_UNITS = {"mbps", "mbbs", "mbp", "megabit", "megabits", "mb"}


def find_speeds(text: str) -> list[tuple[float, int]]:
    """Return [(mbps, char_position)] tolerating 'MBBS', 'MBPS', 'Mbps'."""
    tokens = tokens_with_pos(text)
    out: list[tuple[float, int]] = []
    for i, (tok, _pos) in enumerate(tokens):
        if tok not in SPEED_UNITS:
            continue
        value, run_start = _walk_back(tokens, i)
        if value is not None and 0 < value <= 10000:
            out.append((value, tokens[run_start][1]))
    return out


def find_months(text: str) -> list[tuple[int, int]]:
    tokens = tokens_with_pos(text)
    out: list[tuple[int, int]] = []
    for i, (tok, _pos) in enumerate(tokens):
        if tok not in ("month", "months"):
            continue
        value, run_start = _walk_back(tokens, i)
        if value is not None and 0 < value <= 60:
            out.append((int(value), tokens[run_start][1]))
    return out


DAY_FILLERS = {"business", "working", "calendar"}


def find_day_range(text: str) -> tuple[int, int, int] | None:
    """'within three to five business days' -> (3, 5, position)."""
    tokens = tokens_with_pos(text)
    for i, (tok, _pos) in enumerate(tokens):
        if tok not in ("day", "days"):
            continue
        j = i
        while j - 1 >= 0 and tokens[j - 1][0] in DAY_FILLERS:
            j -= 1
        hi, hi_start = _walk_back(tokens, j)
        if hi is None or hi_start - 1 < 0 or tokens[hi_start - 1][0] != "to":
            continue
        lo, lo_start = _walk_back(tokens, hi_start - 1)
        if lo is None:
            continue
        return int(lo), int(hi), tokens[lo_start][1]
    return None


def squash(text: str) -> str:
    """Strip everything but letters and digits.

    The source contains run-together words ('quality assuranceand, training').
    Comparing on the squashed form makes glued words a non-issue for script matching.
    """
    return re.sub(r"[^a-z0-9]", "", text.lower())
