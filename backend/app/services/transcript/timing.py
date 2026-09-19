"""Timestamp derivation.

Two sources, never blended:

  * `apply_asr_timings` - real timings from the transcription/synthesis provider.
    Every segment gets the start of its first spoken character and the end of its
    last, so a timestamp shown next to a check result is a real position in the
    recording.
  * `estimate_timings` - a words-per-second guess, used only when no timed payload
    exists. Segments produced this way are stamped `timing_source="estimated"` so
    nobody mistakes an estimate for a measurement.

Tokens may be characters or words. Character tokens are exact. Word tokens are
interpolated across their own duration, which matters because the parser splits
run-together speech ("assurance.Yeah.K.") into segments that the provider reports
as a single token.
"""
from collections.abc import Sequence

from app.core.config import settings
from app.core.enums import TimingSource

INTER_TURN_GAP_MS = 350

# How far ahead to hunt for the next segment if the token stream desynchronises.
RESYNC_WINDOW = 400
RESYNC_PROBE = 12


class TimingAlignmentError(Exception):
    """The timed payload does not describe this transcript."""


def estimate_timings(texts: list[str], start_offset_ms: int = 0) -> list[tuple[int, int]]:
    wps = max(settings.estimated_words_per_second, 0.5)
    spans: list[tuple[int, int]] = []
    cursor = start_offset_ms
    for text in texts:
        words = max(len(text.split()), 1)
        duration = int((words / wps) * 1000)
        spans.append((cursor, cursor + duration))
        cursor += duration + INTER_TURN_GAP_MS
    return spans


def _char_stream(tokens: Sequence[dict]) -> tuple[str, list[int], list[int]]:
    """Flatten tokens into one whitespace-free character timeline."""
    chars: list[str] = []
    starts: list[int] = []
    ends: list[int] = []

    for token in tokens:
        text = str(token.get("text", ""))
        keep = [c for c in text if not c.isspace()]
        if not keep:
            continue
        start = int(token["start_ms"])
        end = max(int(token["end_ms"]), start)
        step = (end - start) / len(keep)
        for i, char in enumerate(keep):
            chars.append(char.lower())
            starts.append(round(start + i * step))
            ends.append(round(start + (i + 1) * step) if len(keep) > 1 else end)

    return "".join(chars), starts, ends


def chars_to_tokens(chars: str, starts_ms: list[int], ends_ms: list[int]) -> list[dict]:
    """Manifest arrays -> the token shape `apply_asr_timings` consumes."""
    if not (len(chars) == len(starts_ms) == len(ends_ms)):
        raise TimingAlignmentError("Character timing arrays disagree in length.")
    return [
        {"text": char, "start_ms": start, "end_ms": end}
        for char, start, end in zip(chars, starts_ms, ends_ms, strict=True)
    ]


def apply_asr_timings(tokens: Sequence[dict], texts: list[str]) -> list[tuple[int, int]]:
    """Give every segment the real span of the audio that produced it.

    `tokens` is [{"text", "start_ms", "end_ms"}]. Matching ignores whitespace and
    case; everything else must line up, because a segment stamped with someone
    else's timestamp is worse than no timestamp at all.
    """
    stream, starts, ends = _char_stream(tokens)
    if not stream:
        raise TimingAlignmentError("Timed payload contains no characters.")

    spans: list[tuple[int, int]] = []
    cursor = 0

    for index, text in enumerate(texts):
        needle = "".join(c.lower() for c in text if not c.isspace())
        if not needle:
            fallback = spans[-1][1] if spans else 0
            spans.append((fallback, fallback))
            continue

        if stream[cursor: cursor + len(needle)] != needle:
            cursor = _resync(stream, needle, cursor, index)

        end_index = cursor + len(needle) - 1
        if end_index >= len(starts):
            raise TimingAlignmentError(
                f"Timed payload ran out at segment {index}: {text[:60]!r}"
            )
        spans.append((starts[cursor], max(ends[end_index], starts[cursor])))
        cursor = end_index + 1

    return _monotonic(spans)


def _resync(stream: str, needle: str, cursor: int, index: int) -> int:
    probe = needle[:RESYNC_PROBE]
    found = stream.find(probe, cursor, cursor + RESYNC_WINDOW + len(needle))
    if found == -1:
        raise TimingAlignmentError(
            f"Segment {index} is not in the timed payload: {needle[:60]!r}. "
            "The audio and the transcript are out of sync - regenerate the audio "
            "from this transcript rather than stamping approximate times."
        )
    return found


def _monotonic(spans: list[tuple[int, int]]) -> list[tuple[int, int]]:
    cleaned: list[tuple[int, int]] = []
    previous_end = 0
    for start, end in spans:
        start = max(start, 0)
        end = max(end, start)
        if start < previous_end:
            start = previous_end
            end = max(end, start)
        cleaned.append((start, end))
        previous_end = end
    return cleaned


DEFAULT_TIMING_SOURCE = TimingSource.ESTIMATED
