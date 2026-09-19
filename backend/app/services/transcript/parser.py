"""Raw transcript -> segments.

Why this is not a one-liner: in the supplied call the diarization is broken. The
customer's replies are folded into the agent's turns, e.g.

    Speaker 2  "...do you want a different address?Same address? Same address. Yeah."

Both sides are inside one "Speaker 2" block. So the parser does three things:

  1. splits raw speaker blocks into sentence-sized segments (evidence granularity)
  2. assigns a speaker AND a speaker_confidence, never a bare speaker
  3. marks the transcript `diarization_reliable=False` so no check may decide a
     critical outcome on speaker attribution alone

That last point is the guardrail. A naive parser would confidently attribute a
customer's "Same address" to the agent and manufacture a false critical.
"""
import re
from dataclasses import dataclass

from app.core.enums import Speaker

SPEAKER_LINE_RE = re.compile(r"^\s*Speaker\s+(\d+)\s*[:\t ]\s*(.*)$", re.IGNORECASE)

# Sentence boundary: after .?! followed by whitespace, or glued directly to a capital
# ("assurance.Yeah.K." is one raw run in the source).
SENTENCE_SPLIT_RE = re.compile(r"(?<=[.?!])\s+|(?<=[.?!])(?=[A-Z\[])")

AFFIRMATIONS = {
    "yeah", "yep", "yes", "ok", "okay", "k", "mhmm", "mmhmm", "right", "sure",
    "correct", "no", "alright", "uh huh", "cheers", "thanks", "thank you",
}

AGENT_MARKERS = (
    "this call will be recorded",
    "can you please verify",
    "just let me know if",
    "i need to mute the recording",
)


@dataclass
class ParsedSegment:
    turn_index: int
    speaker: str
    speaker_confidence: float
    text: str


def _normalise_for_match(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", text.lower())


def _split_sentences(block: str) -> list[str]:
    parts = [p.strip() for p in SENTENCE_SPLIT_RE.split(block) if p and p.strip()]
    return parts or ([block.strip()] if block.strip() else [])


def _read_turns(raw: str) -> list[tuple[str, str]]:
    """Collect (speaker_label, block_text), joining continuation lines."""
    turns: list[tuple[str, list[str]]] = []
    for line in raw.splitlines():
        if not line.strip():
            continue
        m = SPEAKER_LINE_RE.match(line)
        if m:
            turns.append((f"Speaker {m.group(1)}", [m.group(2).strip()]))
        elif turns:
            turns[-1][1].append(line.strip())
    return [(label, " ".join(chunks).strip()) for label, chunks in turns if " ".join(chunks).strip()]


def infer_agent_label(turns: list[tuple[str, str]]) -> str:
    """Whoever reads the recording disclaimer is the agent. Never hardcoded."""
    scores: dict[str, int] = {}
    for label, text in turns:
        haystack = _normalise_for_match(text)
        hits = sum(1 for marker in AGENT_MARKERS if _normalise_for_match(marker) in haystack)
        scores[label] = scores.get(label, 0) + hits
    if not scores or max(scores.values()) == 0:
        return "Speaker 2"
    return max(scores, key=scores.get)


def parse(raw: str) -> tuple[list[ParsedSegment], bool]:
    """Return (segments, diarization_reliable)."""
    turns = _read_turns(raw)
    agent_label = infer_agent_label(turns)

    segments: list[ParsedSegment] = []
    multi_sentence_turns = 0

    for turn_index, (label, block) in enumerate(turns):
        sentences = _split_sentences(block)
        if len(sentences) > 4:
            multi_sentence_turns += 1
        base_speaker = Speaker.AGENT if label == agent_label else Speaker.CUSTOMER

        for i, sentence in enumerate(sentences):
            bare = re.sub(r"[^a-z ]", "", sentence.lower()).strip()
            if i == 0:
                confidence = 0.90
            elif bare in AFFIRMATIONS or len(bare) <= 3:
                # Short interjections inside a long block are the classic crosstalk
                # artefact. Attribution here is a coin flip; say so.
                confidence = 0.35
            elif len(sentences) > 4:
                confidence = 0.55
            else:
                confidence = 0.75

            segments.append(
                ParsedSegment(
                    turn_index=turn_index,
                    speaker=base_speaker if confidence >= 0.5 else Speaker.UNKNOWN,
                    speaker_confidence=confidence,
                    text=sentence.strip(),
                )
            )

    # If a meaningful share of turns are long run-together blocks, diarization is
    # not trustworthy and downstream checks must be told.
    reliable = bool(turns) and (multi_sentence_turns / len(turns)) < 0.10
    return segments, reliable
