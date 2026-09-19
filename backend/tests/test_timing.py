"""Real timings must land on the right words, or they are worse than no timings."""
import pytest

from app.services.transcript import parser
from app.services.transcript.timing import (
    TimingAlignmentError, apply_asr_timings, chars_to_tokens, estimate_timings,
)


def _char_tokens(text: str, ms_per_char: int = 100, start: int = 0) -> list[dict]:
    """One token per character, as the ElevenLabs manifest provides."""
    chars, starts, ends = [], [], []
    cursor = start
    for char in text:
        chars.append(char)
        starts.append(cursor)
        ends.append(cursor + ms_per_char)
        cursor += ms_per_char
    return chars_to_tokens("".join(chars), starts, ends)


def test_segment_spans_come_from_the_payload_not_a_guess():
    tokens = _char_tokens("Hello. Helen speaking.")
    spans = apply_asr_timings(tokens, ["Hello.", "Helen speaking."])
    # "Hello." is characters 0-5, so it starts at 0 and ends after the sixth.
    assert spans[0] == (0, 600)
    # The space is character 6; "Helen speaking." starts at the H that follows it.
    assert spans[1][0] == 700
    assert spans[1][1] == 2200


def test_glued_sentences_split_inside_one_token():
    """The parser splits 'assurance.Yeah.K.' that a provider reports as one word."""
    tokens = [{"text": "assurance.Yeah.K.", "start_ms": 1000, "end_ms": 2700}]
    spans = apply_asr_timings(tokens, ["assurance.", "Yeah.", "K."])
    assert spans[0][0] == 1000
    assert spans[2][1] == 2700
    # Strictly increasing, and inside the token's own window.
    assert spans[0][1] <= spans[1][0] and spans[1][1] <= spans[2][0]


def test_whitespace_and_case_do_not_break_alignment():
    tokens = _char_tokens("Yes.  HI there.")
    spans = apply_asr_timings(tokens, ["Yes.", "Hi   there."])
    assert spans[1][1] > spans[0][1]


def test_spans_never_run_backwards():
    tokens = _char_tokens("One. Two. Three.")
    spans = apply_asr_timings(tokens, ["One.", "Two.", "Three."])
    assert all(a[1] <= b[0] for a, b in zip(spans, spans[1:], strict=False))


def test_a_transcript_the_audio_never_said_is_refused():
    tokens = _char_tokens("Hello there.")
    with pytest.raises(TimingAlignmentError):
        apply_asr_timings(tokens, ["Hello there.", "And your date of birth?"])


def test_real_transcript_maps_onto_its_own_character_stream():
    raw = (
        "Speaker 1: Hello. Helen speaking.\n"
        "Speaker 2: Yes. Hi, Helen.Good day.This call will be recorded for "
        "quality assuranceand, training purposes. K?\n"
    )
    parsed, _ = parser.parse(raw)
    texts = [p.text for p in parsed]

    stream = "".join(texts)
    spans = apply_asr_timings(_char_tokens(stream), texts)

    assert len(spans) == len(texts)
    assert spans[0][0] == 0
    # Every span sits inside the audio, in order.
    assert spans[-1][1] <= len(stream) * 100
    assert all(a[1] <= b[0] for a, b in zip(spans, spans[1:], strict=False))


def test_estimated_timings_remain_available_without_a_payload():
    spans = estimate_timings(["one two three", "four five"])
    assert spans[0][0] == 0
    assert spans[1][0] > spans[0][1]
